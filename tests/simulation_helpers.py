"""Small synthetic graph objects for pure algorithm tests, never integration DB substitutes."""

from falkordb.edge import Edge
from falkordb.node import Node

from rippleproof.simulation.models import ScenarioRequest
from rippleproof.simulation.snapshot import normalize


def request(**overrides):
    return ScenarioRequest(
        **{
            "supplier_id": "S-04",
            "as_of": "2026-10-15",
            "outage_start": "2026-10-16",
            "outage_end_exclusive": "2026-10-24",
            **overrides,
        }
    )


class GraphBuilder:
    def __init__(self, stock=0, capacity=60, lead=3, price="14.50"):
        self.nodes = {}
        self.edges = {}
        for identity in ("S-04", "S-08", "S-09", "S-10", "S-11"):
            self.node("Supplier", identity, status="active")
        self.node("Part", "P-22", stock_on_hand=stock, inbound_schedule_complete=True)
        for identity in ("C-01", "C-02"):
            self.node("Certificate", identity, name=identity)
            self.edge("REQUIRES_CERT", "P-22", identity)
        for supplier, expiry in (
            ("S-09", "2027-10-15"),
            ("S-08", "2026-10-15"),
            ("S-10", "2027-10-15"),
            ("S-11", "2026-10-14"),
        ):
            for certificate in ("C-01", "C-02"):
                if supplier == "S-10" and certificate == "C-02":
                    continue
                self.edge("HOLDS_CERT", supplier, certificate, valid_until=expiry)
        self.offer("S-04", primary=True, capacity=52, lead=2, price="25.40")
        self.offer("S-09", capacity=capacity, lead=lead, price=price)

    def node(self, label, identity, **properties):
        self.nodes[identity] = (label, {"id": identity, **properties})
        return self

    def edge(self, relation, source, target, **properties):
        identity = f"{relation}:{source}:{target}"
        self.edges[identity] = (relation, source, target, {"id": identity, **properties})
        return self

    def offer(self, supplier, part="P-22", primary=False, capacity=60, lead=3, price="14.50"):
        return self.edge(
            "SUPPLIES",
            supplier,
            part,
            is_primary=primary,
            daily_capacity=capacity,
            lead_days=lead,
            unit_cost=price,
        )

    def order(
        self,
        identity="O-01",
        quantity=5,
        deadline="2026-10-20",
        priority=1,
        product="PR-01",
        part="P-22",
        units=1,
    ):
        self.node("Order", identity, deadline=deadline, priority=priority, status="open")
        self.node("Product", product, production_days=1)
        self.edge("CONTAINS", identity, product, quantity=quantity)
        self.edge("USES", product, part, units_per_product=units)
        return self

    def shipment(
        self,
        identity="IN-01",
        supplier="S-04",
        quantity=5,
        dispatch="2026-10-16",
        arrival="2026-10-17",
        status="PLANNED",
        part="P-22",
    ):
        self.node(
            "InboundShipment",
            identity,
            quantity=quantity,
            dispatch_date=dispatch,
            expected_arrival_date=arrival,
            status=status,
        )
        self.edge("FULFILLS", supplier, identity)
        self.edge("FOR_PART", identity, part)
        return self

    def snapshot(self):
        native = {identity: index for index, identity in enumerate(self.nodes)}
        nodes = [
            Node(node_id=native[i], labels=label, properties=props)
            for i, (label, props) in self.nodes.items()
        ]
        edges = [
            Edge(native[s], relation, native[t], edge_id=index, properties=props)
            for index, (relation, s, t, props) in enumerate(self.edges.values())
        ]
        return normalize(nodes, edges)
