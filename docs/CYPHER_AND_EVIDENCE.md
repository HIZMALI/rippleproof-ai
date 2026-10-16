# FalkorDB queries, evidence and guarded internal actions

The executable source is [queries.py](../rippleproof/queries.py), called only by
[repository.py](../rippleproof/repository.py). These excerpts reproduce those
templates; they are not LLM-generated Cypher or pseudocode. Node and relationship
properties carry stable domain IDs, independent of reusable internal graph IDs.
See [the complete graph schema](GRAPH_MODEL.md) and [architecture](ARCHITECTURE.md).

## Multi-hop impact (`IMPACT_PATHS`)

```cypher
MATCH evidence = (supplier:Supplier {id: $supplier_id})
  -[:SUPPLIES {is_primary: true}]->(part:Part)
  <-[:USES]-(product:Product)<-[:CONTAINS]-(purchase_order:Order)
WHERE purchase_order.status = $order_status
RETURN evidence
ORDER BY purchase_order.id, part.id, product.id
```

Parameters are validated supplier ID and `OPEN` status. Traversal follows actual
relationships in both directions; it does not reverse their stored endpoints.
S-04 → P-22 ← PR-05 ← O-101 is an observed reference path, not a source-code
answer. The same path supplies order quantity 8 and BOM coefficient 4, giving
32 material units. Reachability identifies dependency, not lateness; O-101 is
covered in the reference scenario after stock and arrival allocation.

## Part requirements (`REQUIRED_CERTIFICATES`) and offers (`ALTERNATIVE_SUPPLIERS`)

```cypher
MATCH (part:Part {id: $part_id})-[requires:REQUIRES_CERT]->(certificate:Certificate)
RETURN part, requires, certificate
ORDER BY certificate.id
```

```cypher
MATCH (supplier:Supplier)-[supplies:SUPPLIES]->(part:Part {id: $part_id})
WHERE supplies.is_primary = false
OPTIONAL MATCH (supplier)-[holds:HOLDS_CERT]->(certificate:Certificate)
RETURN supplier, supplies, part, holds, certificate
ORDER BY supplier.id, certificate.id
```

Prices, lead days, per-part daily capacities, requirement edges and holding/expiry
edges are returned as graph facts. Deterministic Python checks each required
certificate on projected arrival, inclusive of valid_until. S-10 lacks C-02 for
P-22, while C-01 can qualify it for P-12. There is no global supplier approval.
The legacy alternatives API checks as-of; simulation checks arrivals and capacity.

## Coherent operational facts and revision

`SNAPSHOT` is the Phase 2 coherent full read; normalization excludes memory.
The bounded MCP/current-memory path uses `OPERATIONAL_SNAPSHOT`:

```cypher
MATCH (n) WHERE any(label IN labels(n) WHERE label IN $labels)
WITH n ORDER BY n.id LIMIT 2001
WITH collect(n) AS nodes
OPTIONAL MATCH ()-[r]->() WHERE type(r) IN $types
WITH nodes, r LIMIT 4001
RETURN nodes, collect(r)
```

The caller supplies fixed operational label/type allowlists. Sentinel overflows
fail explicitly. Actual sorted labels, properties, relationship IDs/endpoints and
properties produce the operational fingerprint. Decision/Evidence additions do
not change it. A request-scoped snapshot is derived from FalkorDB, never loaded
from a parallel JSON/SQL knowledge store. Archived JSON lives inside Evidence
nodes in FalkorDB. Existing full simulation responses remain subject to the
original dataset-size limitations; no unbounded graph query is exposed to users.

## Deterministic constraints after traversal

[snapshot.py](../rippleproof/simulation/snapshot.py) validates graph facts;
[engine.py](../rippleproof/simulation/engine.py) commits shared stock/receipts
only for a complete order BOM. Orders sort by deadline, descending numeric
priority and stable ID. Planned dispatches inside the exclusive outage window
move to its end, preserving original transit duration. Dispatched and cancelled
receipts are distinct. New proposals respect per-supplier/part dispatch capacity,
booked volume, lead time and arrival-date certifications. Decimal computes cost.
The planner compares bounded greedy policies; it does not prove global optimality,
factory scheduling or guaranteed delivery. Missing vital facts remain unresolved.

## Decision memory: preview, replay and one guarded write

`DECISION`, `DECISION_HISTORY` and `DECISION_COUNT` use parameterized IDs/filter
and bounded paging. `MEMORY_EVIDENCE` retrieves an actual archive. The
[DecisionService](../rippleproof/decisions.py) prepares a fresh selected policy,
checks source and plan revisions plus explicit human confirmation and constant-time
token comparison, and derives stable identity from graph + idempotency key.
Same-request replay returns its actual stored record; changed intent conflicts.

The complete executable `SAVE_DECISION` template is in queries.py. It first
matches all source/supplier/order nodes, verifies source count and absence of an
archive-ID collision, then MERGEs Decision/Evidence and SUPPORTED_BY, SELECTS,
AFFECTS and REFERENCES edges in one command. No partial source-matching write is
allowed. It stores the authoritative plan, snapshot, pseudonym, rationale and UTC
timestamp. It places no purchase, reserves no stock and contacts no supplier.
The one-worker process lock does not exclude external writers between source
read and write; serialize other writers. This is not a production transaction or
identity/authentication service.

## Six MCP tools and graph removal proof

`graph_summary`, `trace_supplier_impact`, `evaluate_part_alternatives`,
`simulate_supply_disruption`, `get_decision_history`, and `resolve_evidence`
use the genuine SDK stdio client/server and reviewed repository templates.
The model selects these tools in agent mode; guided mode uses a fixed sequence
with zero model calls. `resolve_evidence` requires a matching operational revision
for current facts; archived citations retain their historical scope.

The source-only clean-install test disconnects **only its isolated FalkorDB service**.
Impact, simulation and guided MCP must return actual 503/error evidence, then
recover with identical results when the service returns. No fixture answer or
fallback datastore is available. See [testing and reproducibility](TESTING.md).
