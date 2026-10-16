# FalkorDB graph model

Use FalkorDB as the sole canonical domain datastore.
Use parameterized Cypher and stable IDs. Avoid hardcoding demo answers.

## Node labels
- `Supplier {id, name, region, status}`
- `Part {id, name, stock_on_hand}`
- `Product {id, name, production_days}`
- `Order {id, customer_name, deadline, priority, status}`
- `Certificate {id, name}`
- `InboundShipment {id, quantity, dispatch_date, expected_arrival_date, status}`
  (status is `PLANNED`, `DISPATCHED`, or `CANCELLED`; dates are ISO calendar dates).
- `Decision` and `Evidence` (Phase 3 properties and archival semantics below).

## Relationship directions and properties
- `(Supplier)-[:SUPPLIES {unit_cost, lead_days, daily_capacity,
    is_primary}]->(Part)`
- `(Product)-[:USES {units_per_product}]->(Part)`
- `(Order)-[:CONTAINS {quantity}]->(Product)`
- `(Part)-[:REQUIRES_CERT]->(Certificate)`
- `(Supplier)-[:HOLDS_CERT {valid_until}]->(Certificate)`
- `(Supplier)-[:FULFILLS {id}]->(InboundShipment)`
- `(InboundShipment)-[:FOR_PART {id}]->(Part)`
- `(Decision)-[:SELECTS]->(Supplier)`
- `(Decision)-[:AFFECTS]->(Order)`
- `(Decision)-[:SUPPORTED_BY]->(Evidence)`

Names like 'affected', 'candidate', 'fully compliant' must be computed by
real graph queries and corresponding deterministic validations.

## Scenario invariants
- Supplier S-04 is a primary source for Part P-22.
- Product PR-05 uses P-22; Order O-101 contains PR-05.
- S-09 offers P-22 as an alternative and has currently valid required certs.
- S-10 offers P-22 and is lower cost but lacks a required certification.
- Additional suppliers, products, shared parts, non-affected orders, and
  alternative suppliers exist so results are not single-case special-casing.
- Seed 10+ suppliers, 15+ parts, 6+ products, 20+ orders, 3+ certificates.
- Use a fixed seed and reference date 2026-10-15.
- Re-running seed never duplicates nodes, edges, or incorrect properties.

## Required Phase 1 graph queries
1. Dependency expansion from a primary supplier to open orders using at
   least three relationship hops, returning order/part/product identifiers
   and a connected evidence path obtained from the same query.
2. Supplier alternatives for a specified Part, with real `SUPPLIES`
   properties, certificate requirements and certificate expiry information.
3. Summary counts by node label and relationship type.

## Notes on evidence
Graph paths are directed as modeled; narrative arrows may display both
directions. Evidence must include stable node/relationship IDs and a
human-readable path, backed by FalkorDB. Do not use hardcoded strings
saying “S-04 caused O-101” instead of querying the path.

## Query security
- Only fixed whitelisted Cypher strings in the backend.
- All user-supplied values passed as parameters, not string concatenation.
- Strict ID and ISO date validation; meaningful errors when no matches.
- Prefer portable Cypher syntax supported by the FalkorDB release used.

## Phase 2 additive planned-receipt model

The original 63 nodes and 127 relationships remain unchanged. The explicit
`python -m rippleproof.migrate` command adds 82 synthetic shipment nodes and
82 relationships of each new type, giving **145 nodes / 291 relationships**.
The Phase 1 base seed remains a separate, unchanged fixture for compatibility
tests and fresh installations; it is not the upgrade command.

Each shipment belongs to exactly one supplier and one part, with positive
integer quantity and expected arrival on or after dispatch. Its supplier must
have a real `SUPPLIES` offer for the part. Stable shipment IDs use the `IN-`
prefix; relationship IDs follow the existing `TYPE:source_id:target_id` rule.

The additive migration preflights endpoints and ID conflicts, then uses a fixed
parameterized `UNWIND`/`MERGE` template with `ON CREATE SET`. Repetition adds
nothing and does not overwrite existing shipment edits or base facts. The CLI
must run without concurrent external graph writers. API simulations never
write shipments, scenarios or decisions to FalkorDB.

The fixture has five primary-source receipts per part (80 total), one cancelled
P-22 receipt, and one existing alternative S-09/P-03 receipt. Three S-04
receipts were dispatched on the as-of date, 2026-10-15. S-04 planned dispatches
on October 16, 18 and 20 are delayed by the demo outage; October 24 dispatches
are outside its exclusive end. Other suppliers' shipments remain unchanged.
Existing planned transit intervals are authoritative graph facts; only new
alternative proposals use `SUPPLIES.lead_days`.

For custom datasets, an explicitly complete empty inbound schedule can be
represented by `Part.inbound_schedule_complete = true`. An intentionally
uncertified part needs `Part.certification_policy = 'none'`. These optional
properties are not added to existing Phase 1 parts. Without shipment records
or a completeness flag, or without required-cert edges or an explicit `none`
policy, the simulator marks the affected material data unresolved.

## Simulation snapshot and evidence

One fixed `GRAPH.RO_QUERY` returns all nodes and relationships coherently:

```cypher
MATCH (n) WITH collect(n) AS nodes
OPTIONAL MATCH ()-[r]->()
RETURN nodes, collect(r)
```

The request-scoped `GraphSnapshot` is normalized from that response. Stable
node and relationship IDs, endpoint directions and stored properties back
every BOM line, supplier path, receipt and certificate check. There is no
fixture fallback, persistent JSON knowledge store or snapshot cache.

Proposed shipments exist only in the response and have `PROPOSED:` IDs, with
references to their real offer, required certificates and valid holding edges.
They are clearly distinguished from graph-backed committed receipts. Monetary
values in simulation output, including normalized price evidence, are decimal
strings. Phase 1 response property types remain compatible.

## Phase 3 internal decision memory

No migration changes existing operational facts. Approval lazily adds:

- `Decision {id, status:'APPROVED_INTERNAL', scenario_id, created_at,
  operational_fingerprint, plan_revision, operator_id, rationale,
  request_digest, evidence_id, preview_json}`.
- `Evidence {id, kind:'operational_snapshot', observed_at,
  operational_fingerprint, snapshot_json}`. This archives actual normalized
  source nodes and relationships, including source IDs, endpoint directions and
  properties; it does not pretend to be an external supplier record.
- `(Decision)-[:SUPPORTED_BY {id}]->(Evidence)`.
- `(Decision)-[:SELECTS {id}]->(Supplier)` for each selected alternative supplier.
- `(Decision)-[:AFFECTS {id}]->(Order)` for each restored newly-at-risk order.
- `(Evidence)-[:REFERENCES {id}]->(source)` for every actual operational source
  node in its coherent archived snapshot.

Decision and Evidence IDs are stable per graph/idempotency key. Every relationship
has the existing `TYPE:source_id:target_id` property identity. The approval write
is one parameterized server command; source-count and archive-ID preconditions
precede MERGE. Replays read the existing record and create nothing.

A reference-dataset cost-first test approval grows physical counts from 145/291
to 147/441: two nodes, one support edge, two selections, two affected orders,
and 145 source references. Operational counts remain exactly 145/291 and 82
inbound shipments. The live demo graph is preserved; actual approval protocol
tests use isolated graphs. Token credentials are never persisted in the graph.

Only the six operational labels and seven operational edge types contribute to
the material fingerprint. Memory writes leave scenario identity unchanged.
Changes to relevant source properties invalidate previews. Full physical counts
are exposed separately. Archived relationship evidence is historical snapshot
data; current evidence resolution requires the current operational fingerprint.
