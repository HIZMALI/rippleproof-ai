# RippleProof AI — Phase 2: Deterministic Supply-Chain Decision & Simulation Engine

**Event:** Graph Hacks 2026 (FalkorDB)  
**Team:** MORVE (solo)  
**Target:** Track 1 — Agents That Act on Connected Data  
**Execution mode:** Continue the **existing repository**; do not restart the project.  
**Scope:** Phase 2 ONLY. No frontend, LLM, MCP, cloud deployment, external API, remote Git push, or real procurement action.

## 0. Read, inspect, and protect the working baseline

Read these existing files before changing any code:

- `AGENTS.md`
- `docs/PRODUCT_SPEC.md`
- `docs/GRAPH_MODEL.md`
- `tasks/01-foundation.md`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/PHASE1_VERIFICATION.md`

Inspect the actual implementation and tests. Do not assume the schema or Python module paths still match the initial documents. Record current git status, graph fingerprint, and the existing test results **before** modifying any persistent data. Do not alter unrelated Docker volumes. Preserve existing nodes, edges, graph identity, phase-1 endpoints, and historical evidence. If this task requires adding a new node or relationship label, do so via a safe, idempotent **additive** migration/seed extension; explain why the old 63-node/127-relationship counts will then increase. Adjust old count-based assertions to the newly documented reproducible dataset, not by weakening all assertions.

Stop if the working database cannot be accessed or the existing test suite unexpectedly fails; diagnose first. Back up the project-owned graph before persistent schema changes if possible without affecting unrelated Docker data. No destructive data reset or volume deletion.

## 1. Product objective

The user enters a disruption affecting one supplier for a specific date window. The engine must calculate, using **real FalkorDB entities/edges/properties**:

1. What customer orders depend on the disrupted supplier (dependency graph evidence).
2. What orders can be fulfilled on time using shared on-hand inventory and planned incoming shipments in the **baseline** plan.
3. How disrupted shipment timing changes on-time fulfillment (**disrupted** plan).
4. What one or more certified, capacity-constrained alternative suppliers could recover, with realistic lead times and explicitly estimated **additional procurement** costs (**mitigation** plan).
5. Why each order and alternative received its classification, including traceable paths, dates, quantities and reason codes.

**Critical distinction:** Graph reachability indicates possible dependency, not automatically a late order. Report `dependent_orders`, `at_risk_orders`, and `newly_at_risk_orders` as distinct concepts.

## 2. Ground-truth data and time semantics

### Existing data to reuse

- `Supplier` nodes and `SUPPLIES` relationships with `unit_cost`, `lead_days`, `daily_capacity` where actually available.
- `Part` nodes with `stock_on_hand`.
- `Product` → `Part` `USES` relationships with `units_per_product`.
- `Order` → `Product` `CONTAINS` relationships with order-line `quantity`, plus `deadline`, `priority`, and `status` on Order.
- `Part` → `Certificate` `REQUIRES_CERT`, `Supplier` → `Certificate` `HOLDS_CERT` with `valid_until`.

Adapt to actual repository names, but retain their semantics.

### Add planned inbound supply, not imagined arrivals

A disruption cannot truthfully produce projected late orders if the dataset holds only inventory and supplier master records. Add an explicit, documented, deterministic fixture and graph model for planned incoming shipments such as:

- `(:InboundShipment {id, quantity, dispatch_date, expected_arrival_date, status})`
- `(supplier:Supplier)-[:FULFILLS]->(shipment:InboundShipment)`
- `(shipment:InboundShipment)-[:FOR_PART]->(part:Part)`

Use appropriate existing names if already modeled. Each planned shipment has an identifiable supplier, part, quantity, scheduled dispatch, and expected arrival; status must distinguish `PLANNED`, `DISPATCHED`, and `CANCELLED` (or equivalent). Ensure planned shipments are graph-backed, not invented in Python fixtures after a query. Include baseline deliveries for P-22 and at least one more part, plus unaffected receipts, such that some—**not every**—dependency order becomes newly at risk when S-04 is unavailable. Incorporate the real seed's order deadlines and quantities; inspect them first. Seed/migrate idempotently with stable shipment identifiers. Do not backdate purchasing or manufacture new committed orders by calling them historical facts.

### Date and supply rules — must be explicit and tested

- `as_of` is required, fixed to `2026-10-15` in demo fixture tests. The date window is `[outage_start, outage_end_exclusive)`. End is **exclusive**; reject end <= start.
- Today's on-hand inventory remains physically available even if the supplier shuts down. Inventory must be allocated once globally across all orders; it cannot be reused independently for each order.
- A shipment **already dispatched before outage_start** is unaffected by that outage. A **PLANNED** shipment whose planned dispatch falls within the outage window cannot depart until `outage_end_exclusive`; its transit time remains the originally documented dispatch→arrival interval. Explain this modeled assumption in the response.
- Planned shipments that are `CANCELLED` contribute nothing. No time travel: stock with an arrival after an order's deadline cannot fulfill that order on time.
- Use dates, not wall-clock timestamps, in this deterministic local model. Do not claim this is a real-world forecasting model.
- Supplier `lead_days` and `daily_capacity` are evaluated on the **supplier-to-part relationship** when projecting *new alternative shipments*. A supplier cannot exceed its per-part daily shipping capacity on a day. Account for its already planned dispatches when applicable, and avoid double-counting capacity or planned stock.
- An alternative shipment requested as of `as_of` can arrive no earlier than its feasible dispatch date plus `lead_days`; it must never materialize immediately unless legitimately modeled as zero lead days.
- Supplier qualifications must include **ALL** certificates required by the part; each must remain valid on the **planned arrival date** (inclusive `valid_until >= arrival_date`). S-10 (missing C-02) and S-11 (expired C-02) must be rejected with explicit evidence; S-09 and S-08 must be evaluated against the arrival date rather than a hardcoded result on `as_of`.
- Use Python Decimal for prices/cost computations and JSON-safe string serialization, not binary floating point.
- If the graph lacks vital data, return a clearly labeled `insufficient_data`/unresolved status; do not silently assume infinite stock, no certifications or infinite capacity.

## 3. Allocation, comparisons, and honesty about optimization

Build a **deterministic and documented** day-aware simulation. The following simple policy is sufficient for Phase 2; do not add a huge optimization stack:

1. Normalize all open order lines and bill-of-material needs from FalkorDB: required part units = order-line product quantity × `USES.units_per_product`. Sum repeated parts within an order.
2. For on-time fulfillment, sort orders in a documented stable order: earliest deadline, then higher priority, then lexicographic order ID. A single order is fulfilled **all-or-nothing** only if the complete bill-of-material can be covered on or before its deadline. Allocate units only when the whole order can be fulfilled; a failed order must not consume other orders' stock.
3. For each part, maintain an inventory ledger with initial stock, actual/planned receipts by arrival date, and reservations consumed by previously fulfilled orders. All allocations must conserve physical stock. Define how stock shared across deadlines is handled and test it.
4. Evaluate a **baseline** timeline with supplier shipments on planned dates; evaluate **disruption** timeline with only the affected planned shipments shifted by the outage. Keep every other input and allocation policy identical.
5. Compute separate `dependent`, `baseline_at_risk`, `disrupted_at_risk`, and `newly_at_risk` order lists. `newly_at_risk = disrupted_at_risk minus baseline_at_risk` with order identity preserved. Never equate all dependents with at-risk orders.
6. Generate **optional mitigation** plans using alternative `SUPPLIES` relationships, respecting lead days, capacity, certificate validity at arrival, shared demand, and already-booked supply. Do not create new supply from an unsupported seller. Evaluate mitigation with the same allocator.
7. Rank feasible mitigation plans deterministically: (i) maximize newly restored on-time orders / protected priority-weighted order value if value is available, (ii) minimize newly procured units not needed for fulfillment, (iii) minimize **gross additional procurement cost**, (iv) stable supplier ID tie-break. Clearly describe the heuristic; **do not claim a provably global optimum**.
8. Cost should be named `estimated_additional_procurement_cost` and should cover only new proposed units × the graph's unit cost. Do not mislabel it net savings or total operating loss: cancellation fees, already paid commitments, labor, and transport are not modeled.
9. Provide reproducible reasoning per order: demand quantity, allocations, latest arriving input(s), shortfall reason, baseline-versus-disrupted status, and the FalkorDB evidence path. Provide rejection reason codes and graph evidence per alternative.

Use small typed domain classes and pure deterministic functions for allocation/calculation. Graph repository fetching must remain separate from simulation calculations. The LLM must not be necessary for accurate answers.

## 4. API design — validate and adapt to existing conventions

Add a POST endpoint (preferred):

`POST /api/scenarios/simulate`

Suggested request:

```json
{
  "supplier_id": "S-04",
  "as_of": "2026-10-15",
  "outage_start": "2026-10-16",
  "outage_end_exclusive": "2026-10-24",
  "include_mitigation": true
}
```

Return a typed, documented JSON result with at least:

- Scenario ID (deterministically derived or request-scoped) and assumptions.
- Supplier/outage details and underlying real FalkorDB evidence references.
- Baseline, disrupted and optional mitigated order fulfillment summaries.
- Distinct IDs of dependent, baseline-at-risk, disrupted-at-risk and newly-at-risk orders.
- Per-order demand, covered quantities, missing quantities, status and explanatory `reason_codes`.
- Candidate supplier evaluation with capability, lead time, daily capacity, cert evidence and infeasibility reasons.
- Proposed additional shipment schedule including dispatch date, arrival date, quantity, part, supplier and estimated additional cost.
- Data coverage / unsupported-assumption caveats, with a machine-readable `incomplete_data` marker when needed.

Follow current FastAPI error shape: 422 on invalid payloads, 404 for unknown supplier, 503 on FalkorDB outage. Use parameterized whitelisted Cypher only. Do not implement arbitrary query execution, mutation or external procurement in this phase.

Prefer an internal normalized `GraphSnapshot` for predictable algorithms. It must be generated on demand from the live graph (and optionally cached only with explicit invalidation rules). A query result changing in FalkorDB must change the output without changing a Python constant.

## 5. Tests and acceptance gates

**No Phase 3 work until ALL gates below pass.** Preserve the previously passing 47-test Phase 1 suite (update intentional count assertions only when explaining additive seed changes).

At minimum cover these cases with automated tests and documented expected values:

1. Empty/unknown supplier and invalid IDs/date windows.
2. Exact multi-level BOM for O-101: 8 products × 4 P-22 units = 32 required units.
3. Two orders sharing one stock pool cannot each consume the same units.
4. Equal deadlines and priorities use stable order ID tie-breaking; repeat outputs identical.
5. Available initial inventory can keep an order on time despite supplier disruption.
6. Only graph-dependent orders considered in dependency paths; unrelated orders unaffected.
7. Planned supplier shipment within outage is delayed; dispatched shipment is unaffected.
8. Outage end-date is exclusive; boundary-day dispatch allowed.
9. Later receipt cannot fulfill an earlier due order.
10. Delayed receipt causes at least one `newly_at_risk` order in seeded demo.
11. `baseline_at_risk` is not mislabeled as `newly_at_risk`.
12. Supplier capacity limits proposed procurement across multiple days.
13. Lead time postpones alternative arrival correctly.
14. Missing certificate causes explicit rejection (S-10).
15. Expired certificate causes explicit rejection (S-11).
16. Valid-through-arrival-date boundary is accepted (S-08 when feasible).
17. Certificate valid at as-of but expired by arrival is rejected.
18. Already planned receipts for an alternative consume capacity; no double count.
19. Shipment statuses and cancellation handled correctly.
20. Nonpositive units, negative price/capacity, malformed dates and missing required graph data rejected or marked unresolved.
21. `estimated_additional_procurement_cost` computed with Decimal.
22. Alternative plan cannot reduce order risk by introducing nonexistent inventory.
23. Repeating the simulation does not mutate the live graph or create receipts.
24. Changing one underlying graph value in an **isolated test graph** predictably changes the response, restoring original value afterward or disposing only the isolated graph.
25. Real integration test proves live FalkorDB-backed scenario with expected graph evidence.
26. DB unavailable produces 503, never a canned output.
27. Seed/migration idempotency before and after Compose recreation (new nodes allowed only where documented).
28. Backward compatibility of all Phase 1 API routes and evidence fields.

Do not change the project-owned live test graph to force passing results; use disposable, isolated test datasets. Use the repository's established unit/integration testing patterns.

## 6. Required actual verification

- `docker compose config --quiet`
- `docker compose up --build -d`
- Existing documented seed/migration command (twice, verifying graph fingerprint matches between repeats).
- Python complete test suite locally and in Docker as feasible.
- Ruff lint, Ruff format, dependency checks.
- Real HTTP `POST /api/scenarios/simulate` with a demo disruption, plus one failure case.
- Repeat the same request; assert deterministic identical substantive results.
- Restart app/DB containers without wiping volumes, rerun demo and verify no data loss.
- Record actual before/after graph counts and changes; preserve all baseline entities and edges.

Write `docs/PHASE2_VERIFICATION.md` containing exact run commands and observed outputs, a table of known real API values, scenario result explanations, graph query/evidence examples, and limitations. Update README and architecture docs. Include concise model assumptions so a judge can understand why output is trustworthy.

## 7. Quality and stop conditions

- No frontend, LLM provider integration, MCP agent, Graph Hacks submission, real external supply API, real supplier contact, paid services, Docker reset, or GitHub push in Phase 2.
- No hardcoded result values, arbitrary string-built Cypher, fabricated timings/benchmarks/test outcomes, or invisible DB fallbacks.
- Do not confuse graph connections with stock shortages; do not claim proof of global optimization.
- Keep existing working service and graph as intact as practical, extending via explainable migrations.
- If additional baseline data or schema changes require design trade-offs, make minimal explicit assumptions and document them; if genuinely blocked, stop and explain rather than silently simplifying.
- Once tests pass, **STOP** and return a structured report: files changed; data/schema migration; endpoints and sample actual responses; graph counts and fingerprint; real test counts and errors; decisions and caveats; readiness for Phase 3.
