"""Reviewed Cypher allowlist. User values are passed ONLY via params.

Relationship id properties are stable domain identities, not FalkorDB's reusable
internal numeric IDs. Read endpoints use GRAPH.RO_QUERY through the official client.
"""

NODE_LABELS = (
    "Supplier",
    "Part",
    "Product",
    "Order",
    "Certificate",
    "Decision",
    "Evidence",
    "InboundShipment",
)
OPERATIONAL_LABELS = frozenset(
    {"Supplier", "Part", "Product", "Order", "Certificate", "InboundShipment"}
)
OPERATIONAL_RELATIONSHIPS = frozenset(
    {"SUPPLIES", "USES", "CONTAINS", "REQUIRES_CERT", "HOLDS_CERT", "FULFILLS", "FOR_PART"}
)
RELATIONSHIP_TYPES = (
    "SUPPLIES",
    "USES",
    "CONTAINS",
    "REQUIRES_CERT",
    "HOLDS_CERT",
    "SELECTS",
    "AFFECTS",
    "SUPPORTED_BY",
    "FULFILLS",
    "FOR_PART",
    "REFERENCES",
)

READINESS = "RETURN 1"
NODE_COUNTS = "MATCH (n) RETURN labels(n), count(n)"
RELATIONSHIP_COUNTS = "MATCH ()-[r]->() RETURN type(r), count(r)"
SUPPLIER_EXISTS = "MATCH (n:Supplier {id: $id}) RETURN n.id"
PART = "MATCH (n:Part {id: $id}) RETURN n"

# One read command returns a coherent set of connected facts for simulation.
SNAPSHOT = """
MATCH (n) WITH collect(n) AS nodes
OPTIONAL MATCH ()-[r]->()
RETURN nodes, collect(r)
"""

OPERATIONAL_SNAPSHOT = """
MATCH (n) WHERE any(label IN labels(n) WHERE label IN $labels)
WITH n ORDER BY n.id LIMIT 2001
WITH collect(n) AS nodes
OPTIONAL MATCH ()-[r]->() WHERE type(r) IN $types
WITH nodes, r LIMIT 4001
RETURN nodes, collect(r)
"""

DECISION = "MATCH (d:Decision {id: $id}) RETURN d"
DECISION_HISTORY = """
MATCH (d:Decision)
WHERE d.status = 'APPROVED_INTERNAL' AND ($scenario_id IS NULL OR d.scenario_id = $scenario_id)
RETURN d ORDER BY d.created_at DESC, d.id SKIP $offset LIMIT $limit
"""
DECISION_COUNT = """
MATCH (d:Decision)
WHERE d.status = 'APPROVED_INTERNAL' AND ($scenario_id IS NULL OR d.scenario_id = $scenario_id)
RETURN count(d)
"""
MEMORY_EVIDENCE = "MATCH (e:Evidence {id: $id}) RETURN e"

# One graph write creates a decision, its archived snapshot and all links.
# Compare request_digest inside the write too; a conflicting identity never
# attaches evidence to another approval. Source completeness is checked before MERGE.
SAVE_DECISION = """
MATCH (source) WHERE source.id IN $source_ids
WITH collect(source) AS sources
WHERE size(sources) = $source_count
OPTIONAL MATCH (supplier:Supplier) WHERE supplier.id IN $supplier_ids
WITH sources, collect(supplier) AS suppliers
OPTIONAL MATCH (purchase_order:Order) WHERE purchase_order.id IN $order_ids
WITH sources, suppliers, collect(purchase_order) AS orders
OPTIONAL MATCH (archive:Evidence {id: $evidence_id})
WITH sources, suppliers, orders, archive WHERE archive IS NULL
MERGE (d:Decision {id: $decision_id})
ON CREATE SET d = $decision
WITH d, sources, suppliers, orders WHERE d.request_digest = $request_digest
MERGE (e:Evidence {id: $evidence_id})
ON CREATE SET e = $evidence
MERGE (d)-[supports:SUPPORTED_BY]->(e)
ON CREATE SET supports.id = 'SUPPORTED_BY:' + d.id + ':' + e.id
FOREACH (s IN suppliers |
  MERGE (d)-[selects:SELECTS]->(s)
  ON CREATE SET selects.id = 'SELECTS:' + d.id + ':' + s.id)
FOREACH (o IN orders |
  MERGE (d)-[affects:AFFECTS]->(o)
  ON CREATE SET affects.id = 'AFFECTS:' + d.id + ':' + o.id)
FOREACH (source IN sources |
  MERGE (e)-[ref:REFERENCES]->(source)
  ON CREATE SET ref.id = 'REFERENCES:' + e.id + ':' + source.id)
RETURN d
"""

MIGRATE_INBOUND = """
UNWIND $rows AS row
MATCH (supplier:Supplier {id: row.supplier_id}), (part:Part {id: row.part_id})
MERGE (shipment:InboundShipment {id: row.properties.id})
ON CREATE SET shipment = row.properties
MERGE (supplier)-[fulfills:FULFILLS]->(shipment)
ON CREATE SET fulfills.id = row.fulfills_id
MERGE (shipment)-[for_part:FOR_PART]->(part)
ON CREATE SET for_part.id = row.for_part_id
RETURN count(shipment)
"""

IMPACT_PATHS = """
MATCH evidence = (supplier:Supplier {id: $supplier_id})
  -[:SUPPLIES {is_primary: true}]->(part:Part)
  <-[:USES]-(product:Product)<-[:CONTAINS]-(purchase_order:Order)
WHERE purchase_order.status = $order_status
RETURN evidence
ORDER BY purchase_order.id, part.id, product.id
"""

REQUIRED_CERTIFICATES = """
MATCH (part:Part {id: $part_id})-[requires:REQUIRES_CERT]->(certificate:Certificate)
RETURN part, requires, certificate
ORDER BY certificate.id
"""

ALTERNATIVE_SUPPLIERS = """
MATCH (supplier:Supplier)-[supplies:SUPPLIES]->(part:Part {id: $part_id})
WHERE supplies.is_primary = false
OPTIONAL MATCH (supplier)-[holds:HOLDS_CERT]->(certificate:Certificate)
RETURN supplier, supplies, part, holds, certificate
ORDER BY supplier.id, certificate.id
"""

SEED_NODES = {
    "Supplier": "UNWIND $rows AS row MERGE (n:Supplier {id: row.id}) SET n = row",
    "Part": "UNWIND $rows AS row MERGE (n:Part {id: row.id}) SET n = row",
    "Product": "UNWIND $rows AS row MERGE (n:Product {id: row.id}) SET n = row",
    "Order": "UNWIND $rows AS row MERGE (n:Order {id: row.id}) SET n = row",
    "Certificate": "UNWIND $rows AS row MERGE (n:Certificate {id: row.id}) SET n = row",
}

SEED_RELATIONSHIPS = {
    "SUPPLIES": """
        UNWIND $rows AS row
        MATCH (source:Supplier {id: row.source_id}), (target:Part {id: row.target_id})
        MERGE (source)-[r:SUPPLIES]->(target) SET r = row.properties
    """,
    "USES": """
        UNWIND $rows AS row
        MATCH (source:Product {id: row.source_id}), (target:Part {id: row.target_id})
        MERGE (source)-[r:USES]->(target) SET r = row.properties
    """,
    "CONTAINS": """
        UNWIND $rows AS row
        MATCH (source:Order {id: row.source_id}), (target:Product {id: row.target_id})
        MERGE (source)-[r:CONTAINS]->(target) SET r = row.properties
    """,
    "REQUIRES_CERT": """
        UNWIND $rows AS row
        MATCH (source:Part {id: row.source_id}), (target:Certificate {id: row.target_id})
        MERGE (source)-[r:REQUIRES_CERT]->(target) SET r = row.properties
    """,
    "HOLDS_CERT": """
        UNWIND $rows AS row
        MATCH (source:Supplier {id: row.source_id}), (target:Certificate {id: row.target_id})
        MERGE (source)-[r:HOLDS_CERT]->(target) SET r = row.properties
    """,
}

READ_QUERIES = frozenset(
    {
        READINESS,
        NODE_COUNTS,
        RELATIONSHIP_COUNTS,
        SUPPLIER_EXISTS,
        PART,
        IMPACT_PATHS,
        REQUIRED_CERTIFICATES,
        ALTERNATIVE_SUPPLIERS,
        SNAPSHOT,
        OPERATIONAL_SNAPSHOT,
        DECISION,
        DECISION_HISTORY,
        DECISION_COUNT,
        MEMORY_EVIDENCE,
    }
)
