"""Normalize one real graph response, exposing incomplete facts explicitly."""

import hashlib
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

from falkordb.node import Node

from rippleproof.models import EvidenceNode, EvidencePath, EvidenceRelationship, strict_iso_date
from rippleproof.queries import OPERATIONAL_LABELS, OPERATIONAL_RELATIONSHIPS
from rippleproof.simulation.models import (
    DataIssue,
    GraphSnapshot,
    MaterialLine,
    OfferFact,
    OrderDemand,
    PartDemand,
    PartFact,
    ShipmentFact,
)


def connected_path(nodes: list[EvidenceNode], edges: list[EvidenceRelationship]) -> EvidencePath:
    text = f"{nodes[0].label} {nodes[0].id}"
    for index, edge in enumerate(edges):
        left, right = nodes[index], nodes[index + 1]
        if (edge.source_id, edge.target_id) == (left.id, right.id):
            text += f" -[{edge.type}]-> "
        elif (edge.source_id, edge.target_id) == (right.id, left.id):
            text += f" <-[{edge.type}]- "
        else:
            raise ValueError("Evidence path endpoints do not connect")
        text += f"{right.label} {right.id}"
    return EvidencePath(nodes=nodes, relationships=edges, human_readable=text)


def normalize(nodes: list[Node], edges: list) -> GraphSnapshot:
    # Memory is deliberately outside the material model and its revision hash.
    # Filter before validation too: malformed memory must not invent material issues.
    # The serialized representation is unchanged for existing operational graphs.
    nodes = [n for n in nodes if OPERATIONAL_LABELS.intersection(n.labels)]
    edges = [e for e in edges if e.relation in OPERATIONAL_RELATIONSHIPS]
    issues = []

    def issue(identity, field, detail="Missing or invalid graph property"):
        issues.append(
            DataIssue(entity_id=str(identity), code=f"INVALID_{field.upper()}", detail=detail)
        )

    def integer(props, field, identity, minimum=0):
        value = props.get(field)
        if type(value) is not int or value < minimum or value > 10**9:
            issue(identity, field)
            return None
        return value

    def calendar(props, field, identity):
        try:
            return strict_iso_date(props.get(field))
        except (ValueError, TypeError):
            issue(identity, field)
            return None

    node_map, native_map = {}, {}
    for node in sorted(nodes, key=lambda n: str(n.properties.get("id", ""))):
        identity = node.properties.get("id")
        if not isinstance(identity, str) or not identity or not node.labels or identity in node_map:
            issue(identity, "node_identity")
            continue
        node_map[identity] = EvidenceNode(
            id=identity, label=node.labels[0], properties=node.properties
        )
        native_map[node.id] = identity
    relation_map = {}
    for edge in sorted(edges, key=lambda e: str(e.properties.get("id", ""))):
        identity = edge.properties.get("id")
        if (
            not isinstance(identity, str)
            or not identity
            or identity in relation_map
            or edge.src_node not in native_map
            or edge.dest_node not in native_map
        ):
            issue(identity, "relationship_identity")
            continue
        properties = dict(edge.properties)
        # Monetary evidence is decimal text too. The legacy Phase 1 API retains
        # its original graph property types.
        if edge.relation == "SUPPLIES" and "unit_cost" in properties:
            properties["unit_cost"] = str(properties["unit_cost"])
        relation_map[identity] = EvidenceRelationship(
            id=identity,
            type=edge.relation,
            source_id=native_map[edge.src_node],
            target_id=native_map[edge.dest_node],
            properties=properties,
        )
    outgoing = defaultdict(list)
    incoming = defaultdict(list)
    for edge in relation_map.values():
        outgoing[edge.source_id].append(edge)
        incoming[edge.target_id].append(edge)

    parts = {}
    for node in node_map.values():
        if node.label == "Supplier" and node.properties.get("status") not in {
            "active",
            "inactive",
            "unavailable",
        }:
            issue(node.id, "supplier_status")
        if node.label == "Order" and node.properties.get("status") not in {"open", "closed"}:
            issue(node.id, "order_status")
        if node.label != "Part":
            continue
        requirements = [r.id for r in outgoing[node.id] if r.type == "REQUIRES_CERT"]
        for ref in requirements:
            if node_map[relation_map[ref].target_id].label != "Certificate":
                issue(node.id, "certificate_requirement")
        if not requirements and node.properties.get("certification_policy") != "none":
            issue(node.id, "certificate_requirements", "No requirements or explicit 'none' policy")
        parts[node.id] = PartFact(
            id=node.id,
            stock_on_hand=integer(node.properties, "stock_on_hand", node.id),
            requirement_edges=sorted(requirements),
        )

    offers = []
    for edge in relation_map.values():
        if edge.type != "SUPPLIES":
            continue
        props = edge.properties
        try:
            price = Decimal(str(props["unit_cost"]))
            if not price.is_finite() or price < 0 or price > Decimal("1e12"):
                raise ValueError("Invalid monetary value")
        except (KeyError, ValueError, InvalidOperation):
            price = None
            issue(edge.id, "unit_cost")
        primary = props.get("is_primary")
        if type(primary) is not bool:
            primary = None
            issue(edge.id, "is_primary")
        if node_map[edge.source_id].label != "Supplier" or node_map[edge.target_id].label != "Part":
            issue(edge.id, "supply_endpoints")
        offers.append(
            OfferFact(
                id=edge.id,
                supplier_id=edge.source_id,
                part_id=edge.target_id,
                unit_cost=price,
                lead_days=integer(props, "lead_days", edge.id),
                daily_capacity=integer(props, "daily_capacity", edge.id),
                is_primary=primary,
            )
        )
    for edge in relation_map.values():
        if edge.type == "HOLDS_CERT":
            calendar(edge.properties, "valid_until", edge.id)

    shipments = []
    scheduled_parts = set()
    global_unknown = any("IDENTITY" in entry.code for entry in issues)
    for node in node_map.values():
        if node.label != "InboundShipment":
            continue
        suppliers = [r for r in incoming[node.id] if r.type == "FULFILLS"]
        part_edges = [r for r in outgoing[node.id] if r.type == "FOR_PART"]
        if (
            len(suppliers) != 1
            or len(part_edges) != 1
            or node_map[suppliers[0].source_id].label != "Supplier"
            or part_edges[0].target_id not in parts
        ):
            issue(node.id, "shipment_endpoints", "Exactly one supplier and part are required")
            global_unknown = True
            continue
        part = part_edges[0].target_id
        scheduled_parts.add(part)
        count_before = len(issues)
        if not any(o.supplier_id == suppliers[0].source_id and o.part_id == part for o in offers):
            issue(node.id, "shipment_offer", "Supplier has no SUPPLIES relationship for this part")
        quantity = integer(node.properties, "quantity", node.id, 1)
        dispatch = calendar(node.properties, "dispatch_date", node.id)
        arrival = calendar(node.properties, "expected_arrival_date", node.id)
        status = node.properties.get("status")
        if status not in {"PLANNED", "DISPATCHED", "CANCELLED"}:
            issue(node.id, "shipment_status")
        if dispatch and arrival and arrival < dispatch:
            issue(node.id, "shipment_interval")
        if len(issues) != count_before:
            parts[part].issues.append("INVALID_SHIPMENT_DATA")
            continue
        shipments.append(
            ShipmentFact(
                id=node.id,
                supplier_id=suppliers[0].source_id,
                part_id=part,
                quantity=quantity,
                dispatch_date=dispatch,
                expected_arrival_date=arrival,
                status=status,
                evidence_refs=[node.id, suppliers[0].id, part_edges[0].id],
            )
        )
    for part in parts.values():
        if (
            part.id not in scheduled_parts
            and node_map[part.id].properties.get("inbound_schedule_complete") is not True
        ):
            issue(part.id, "inbound_schedule", "No inbound schedule or explicit completeness flag")

    orders = []
    for node in node_map.values():
        if node.label != "Order" or node.properties.get("status") != "open":
            continue
        deadline = calendar(node.properties, "deadline", node.id)
        priority = integer(node.properties, "priority", node.id)
        by_part = defaultdict(list)
        lines = [r for r in outgoing[node.id] if r.type == "CONTAINS"]
        if not lines:
            issue(node.id, "order_lines")
        for contains in lines:
            product = node_map[contains.target_id]
            quantity = integer(contains.properties, "quantity", node.id, 1)
            uses = [r for r in outgoing[product.id] if r.type == "USES"]
            if product.label != "Product" or not uses:
                issue(node.id, "bill_of_materials")
            for use in uses:
                units = integer(use.properties, "units_per_product", node.id, 1)
                if use.target_id not in parts:
                    issue(node.id, "part_reference")
                    continue
                if quantity is not None and units is not None:
                    by_part[use.target_id].append(
                        MaterialLine(
                            product_id=product.id,
                            product_quantity=quantity,
                            units_per_product=units,
                            quantity=quantity * units,
                            evidence=connected_path(
                                [node, product, node_map[use.target_id]], [contains, use]
                            ),
                        )
                    )
        orders.append(
            OrderDemand(
                order_id=node.id,
                deadline=deadline,
                priority=priority,
                parts=[
                    PartDemand(part_id=p, quantity=sum(x.quantity for x in ls), lines=ls)
                    for p, ls in sorted(by_part.items())
                ],
            )
        )
    for fact in [*parts.values(), *offers, *orders]:
        identity = fact.order_id if isinstance(fact, OrderDemand) else fact.id
        fact.issues = sorted(set(fact.issues + [i.code for i in issues if i.entity_id == identity]))
    payload = json.dumps(
        {
            "nodes": {k: v.model_dump(mode="json") for k, v in sorted(node_map.items())},
            "relationships": {
                k: v.model_dump(mode="json") for k, v in sorted(relation_map.items())
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return GraphSnapshot(
        fingerprint=hashlib.sha256(payload.encode()).hexdigest(),
        nodes=node_map,
        relationships=relation_map,
        parts=parts,
        orders=orders,
        offers=offers,
        shipments=shipments,
        issues=sorted(issues, key=lambda i: (i.entity_id, i.code, i.detail)),
        global_supply_unknown=global_unknown,
    )


def sorted_orders(snapshot: GraphSnapshot) -> list[OrderDemand]:
    return sorted(
        snapshot.orders,
        key=lambda o: (
            o.deadline or date.max,
            -(o.priority if o.priority is not None else 0),
            o.order_id,
        ),
    )


def dependencies(snapshot: GraphSnapshot, supplier_id: str) -> list[EvidencePath]:
    offers = {
        offer.part_id: offer
        for offer in snapshot.offers
        if offer.supplier_id == supplier_id and offer.is_primary is True
    }
    paths = []
    for order in sorted_orders(snapshot):
        for demand in order.parts:
            offer = offers.get(demand.part_id)
            if not offer:
                continue
            for line in demand.lines:
                original = line.evidence
                paths.append(
                    connected_path(
                        [
                            snapshot.nodes[supplier_id],
                            original.nodes[2],
                            original.nodes[1],
                            original.nodes[0],
                        ],
                        [
                            snapshot.relationships[offer.id],
                            original.relationships[1],
                            original.relationships[0],
                        ],
                    )
                )
    return paths
