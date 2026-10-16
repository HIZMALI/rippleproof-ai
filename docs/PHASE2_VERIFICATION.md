# Phase 2 verification — 2026-10-15

**COMPLETE: Phase 2 acceptance gates passed.** The implementation uses the
existing project, real FalkorDB and deterministic calculations. Phase 3 has not
started. No database reset, volume deletion, GitHub push, external procurement,
frontend, LLM or MCP integration was performed.

## Baseline protection

Before any persistent change, both original suites passed: **47 host tests in
3.28s; 47 Docker tests in 1.20s**. Git was and remains on `main`, with no commits
or remote. The live graph was accessible and contained 63 nodes / 127
relationships. Its complete fingerprint matched Phase 1:

```text
f1849b43b4ad9c3cb7ef64b7d6f3537bd76bddffd90a7c55d48cc5be8701e79a
```

Backed up the complete project graph to
`.local/backups/phase2-baseline-20261015.json` before migration. That ignored
workspace file is verification/backup data, not an application knowledge store.
No unrelated graph or volume was touched. Later checks compared **every original
node label/property and every original edge's type/endpoints/properties** with
this backup and asserted equality.

## Features and architecture

- A fresh, coherent snapshot of actual FalkorDB nodes/relationships per request,
  obtained through one fixed read-only Cypher command; no answer cache or fixture fallback.
- Exact order-line quantity × BOM units, summed for shared parts within each order,
  with each contributing graph path retained.
- One global stock/receipt ledger, deadline-aware FIFO allocation and whole-order
  commits only. Failed orders reserve no stock.
- Baseline versus disrupted shipment timelines, exclusive outage ends, unaffected
  dispatched stock, cancelled receipts excluded, and no late or past-due double counting.
- Optional multi-supplier procurement using actual offers, per-part daily capacity
  after existing bookings, dispatch-plus-lead arrivals and arrival-valid certificates.
- Deterministic policy comparisons with explicit heuristic ranking, unused-unit
  trimming, protection of already-covered disrupted orders and no global-optimum claim.
- Decimal prices and gross additional procurement costs, serialized as strings.
- Per-order quantities, allocations, shortfalls, latest allocated arrival, late
  receipt references, candidate rejection codes and connected graph evidence.
- Typed `POST /api/scenarios/simulate`, with 422/404/503 failures and explicit
  `incomplete_data`/`insufficient_data` handling.

The repository fetches facts; `simulation/snapshot.py` normalizes them;
`simulation/engine.py` contains pure allocation, timeline and scheduling
functions; `simulation/models.py` defines the contracts. No simulation code
imports synthetic fixture data.

## Additive schema and counts

Added `InboundShipment` and directed `FULFILLS` / `FOR_PART` relationships.
Each shipment has a stable ID, positive quantity, scheduled dispatch, expected
arrival and PLANNED/DISPATCHED/CANCELLED status. Its endpoints and actual
`SUPPLIES` relationship are validated.

The migration command uses preflight validation and a parameterized
`UNWIND`/`MERGE` template with `ON CREATE SET`. It preserves existing base
facts and shipment edits, refuses conflicting identities/endpoints, and does
not run through HTTP. The Phase 1 base seed is unchanged and remains a separate
fresh-fixture command; it was **not** rerun against the live graph.

| Live count | Before | Migration 1 | Migration 2 | After recreation + migration |
| --- | ---: | ---: | ---: | ---: |
| All nodes | 63 | 145 | 145 | 145 |
| All relationships | 127 | 291 | 291 | 291 |
| InboundShipment | 0 | 82 | 82 | 82 |
| FULFILLS | 0 | 82 | 82 | 82 |
| FOR_PART | 0 | 82 | 82 | 82 |
| Supplier / Part / Product / Order / Certificate | 12 / 16 / 8 / 24 / 3 | unchanged | unchanged | unchanged |
| Original relationship types and all original properties | 127 | unchanged | unchanged | unchanged |

The new fixture includes 80 primary receipts (five per part), one cancelled
P-22 receipt, and an existing S-09/P-03 receipt: 82 total, of which three are
DISPATCHED, 78 PLANNED and one CANCELLED. Commitments are synthetic explicit
graph records, not receipts manufactured by simulation code.

All post-migration graph checkpoints had this identical raw graph fingerprint:

```text
049b24d6972faf91765ffd99eaa620b8eba321cc3662ec472fd87cd1a92e2f11
```

This fingerprint sorts raw node labels/properties and raw relationship
endpoints/types/properties, excluding internal numeric IDs. The separate
normalized simulation snapshot fingerprint is:

```text
d3c35628f3c00ce059907dfbe57a6acfa639d5b95f931b650a7faeb55abee19e
```

Different representations intentionally have different hashes. The normalized
snapshot uses typed evidence, including decimal-text prices.

## Actual HTTP simulation

Request to `http://127.0.0.1:18000/api/scenarios/simulate`:

```json
{
  "supplier_id": "S-04",
  "as_of": "2026-10-15",
  "outage_start": "2026-10-16",
  "outage_end_exclusive": "2026-10-24",
  "include_mitigation": true
}
```

The full captured response is
verification/phase2-demo-response.json (historical local artifact; excluded from public candidate).
The file was saved from a real HTTP response and is not used by the application.

Observed response projection:

```json
{
  "scenario_id": "SC-4990e7e493adea7efa18",
  "baseline_at_risk_orders": ["O-122", "O-123"],
  "disrupted_at_risk_orders": ["O-105", "O-106", "O-123"],
  "newly_at_risk_orders": ["O-105", "O-106"],
  "restored_orders": ["O-105", "O-106"],
  "estimated_additional_procurement_cost": "1364.00",
  "incomplete_data": false
}
```

| Actual value | Result |
| --- | --- |
| Open / dependent orders | 21 / 11 |
| Baseline on-time / at-risk / unresolved | 19 / 2 / 0 |
| Disrupted on-time / at-risk / unresolved | 18 / 3 / 0 |
| Mitigated on-time / at-risk / unresolved | 20 / 1 / 0 |
| Newly at-risk and restored | O-105, O-106 |
| Remaining mitigated risk | O-123 |
| O-101 P-22 demand | 8 × 4 = 32 |
| O-105 disrupted P-22 demand / available / shortfall | 76 / 49 / 27 |
| O-106 disrupted P-12 demand / available / shortfall | 108 / 8 / 100 |
| Selected heuristic | cost_first |
| New proposed / unused units | 132 / 0 |
| Estimated gross additional procurement cost | "1364.00" |

O-101 remains covered; graph dependency does not automatically make it late.
O-122 has a baseline P-12 shortfall (72 required, 48 available) and is **not**
newly at risk. When O-106 fails in the disruption plan, it reserves nothing,
freeing stock for O-122. This is the documented global allocator, not a
scenario-specific exception.

Recovering O-105 consumes the P-22 inventory that would otherwise cover O-106.
The second recovery therefore needs five more P-22 units, in addition to its
100-unit P-12 shortage. This is why the plan proposes 32 total P-22 units,
rather than independently reusing the same inventory for both orders.

| Supplier / part | Units | Dispatch | Arrival | Graph unit cost | Additional cost |
| --- | ---: | --- | --- | ---: | ---: |
| S-09 / P-22 | 27 | 2026-10-15 | 2026-10-18 | "14.5" | "391.50" |
| S-10 / P-12 | 70 | 2026-10-15 | 2026-10-17 | "9.0" | "630.00" |
| S-10 / P-12 | 30 | 2026-10-16 | 2026-10-18 | "9.0" | "270.00" |
| S-09 / P-22 | 5 | 2026-10-15 | 2026-10-18 | "14.5" | "72.50" |

S-09 ships 32 P-22 units on October 15, within its daily capacity of 60.
S-10's P-12 units span two days, respecting its daily capacity of 70.
Costs are gross additional proposed procurement only; no existing commitment
is charged again and no net savings figure is claimed.

### Certification evidence

| P-22 candidate | Earliest arrival | Actual decision |
| --- | --- | --- |
| S-09 | 2026-10-18 | Eligible; C-01 and C-02 valid through 2027-10-15 |
| S-10 | 2026-10-17 | Rejected: MISSING_REQUIRED_CERTIFICATE, C-02 holding null |
| S-11 | 2026-10-19 | Rejected: CERTIFICATE_EXPIRED_AT_ARRIVAL, C-02 expired 2026-10-14 |
| S-08 | 2026-10-20 | Rejected: C-02 valid at as-of but expired before arrival |

Qualification is per part. S-10's P-12 offer is valid because P-12 requires C-01,
which S-10 holds through the planned arrival. It is not globally approved for
P-22. The boundary unit test accepts S-08 when its modeled arrival is exactly
its valid-until date and rejects an arrival one day later.

### Actual receipt timing and connected evidence

`IN-P-22-02` is PLANNED for dispatch 2026-10-16 / arrival 2026-10-18.
The outage moves dispatch to October 24 and arrival to October 26, preserving
two transit days. `IN-P-22-01` was already dispatched on October 15 and remains
unaffected. `IN-P-22-05` dispatches exactly October 24, outside the window.
`IN-CANCELLED-22` contributes no stock.

Example graph-backed identities returned in the response:

```text
Supplier S-04 -[SUPPLIES]-> Part P-22 <-[USES]- Product PR-05 <-[CONTAINS]- Order O-101
SUPPLIES:S-04:P-22
USES:PR-05:P-22
CONTAINS:O-101:PR-05

Supplier S-04 -[FULFILLS]-> InboundShipment IN-P-22-02 -[FOR_PART]-> Part P-22
FULFILLS:S-04:IN-P-22-02
FOR_PART:IN-P-22-02:P-22
```

The fixed snapshot query is:

```cypher
MATCH (n) WITH collect(n) AS nodes
OPTIONAL MATCH ()-[r]->()
RETURN nodes, collect(r)
```

BOM and supplier paths are assembled only from connected node/edge facts in
that same actual result. Proposals carry references to the real offer and all
required/held certificate evidence, with clearly marked `PROPOSED:` identities.
They are never asserted to be committed graph shipment nodes.

### HTTP failures, repeatability and persistence

Observed HTTP 404 for S-99, 422 for an invalid window and malformed ISO date,
and 200 with `mitigated: null` / no proposals when mitigation was disabled.
All four legacy readiness/data endpoints also returned 200 after migration.

Stopped the real FalkorDB service while FastAPI remained running. **All five**
readiness/data/scenario routes returned 503, including the new POST, with:

```json
{"error":{"code":"database_unavailable","message":"FalkorDB is unavailable. Try again later."}}
```

The same request was repeated before restart, after restarting both services,
and after forced recreation of both containers. Complete JSON responses were
identical, including scenario ID, graph snapshot hash, allocations, candidate
checks and cost. Raw graph fingerprints remained identical, with the original
63/127 subgraph fully preserved. Re-running the additive migration after
recreation changed nothing. No seed/reset/flush operation was used.

## Actual tests and acceptance coverage

| Check | Actual outcome |
| --- | --- |
| Full Docker suite, Python 3.12.15 | **103 passed in 2.99s** |
| Full host suite, Python 3.14.0 | **103 passed in 6.61s** |
| Included test composition | 79 local/pure/HTTP-input/transport cases; 24 real FalkorDB cases |
| Ruff | All checks passed; 28 Python files formatted |
| Host/runtime/test-container dependencies | No broken requirements |
| Compose configuration | Exit 0 |
| Build/start / restart / forced recreation | Exit 0; services healthy |
| Migration repeat fingerprint / base-entity preservation | Passed before and after recreation |
| Repeated live HTTP response equality | Passed |
| Live DB outage -> POST 503 | Passed |

The original 47 cases remain in the suite. The exact OpenAPI route set was
extended for the new route, and the existing real transport-failure test now
also checks the POST. Base-fixture counts remain 63/127. Migrated integration
fixtures assert **145/291**; original nodes/edges/properties are compared, not
discarded or replaced with weakened count checks.

| Task acceptance gates | Automated coverage |
| --- | --- |
| 1 | Request validation parameters; live unknown-supplier 404 |
| 2 | Live O-101 demand 8 × 4 = 32; repeated-part aggregation |
| 3–4 | Shared stock, failed-order rollback, priority/ID sorting, identical repeats |
| 5–6 | Initial stock protection, non-shared unrelated order, actual supplier paths |
| 7–9 | Planned/dispatched dispatch boundaries and late-receipt tests |
| 10–11 | Exact seeded baseline/disrupted/new-risk ID assertions |
| 12–13 | Capacity spanning multiple days and dispatch-plus-lead assertions |
| 14–17 | Missing, expired, inclusive-boundary and arrival-expiry qualification tests |
| 18–19 | Existing alternative bookings, no double receipt count, cancellation |
| 20 | Invalid/missing stock, dates, BOM units, quantity, cost, lead and capacity; explicit unresolved results |
| 21–22 | Decimal 0.10 × 5 = "0.50"; zero capacity/long lead cannot invent inventory |
| 23 | Pure snapshot immutability and real graph unchanged across repeat POSTs |
| 24 | Isolated P-22 stock mutation changes cost from "1364.00" to "1074.00" |
| 25 | Live graph snapshot and connected BOM/supplier evidence |
| 26 | Actual refused TCP connection and controlled live database outage |
| 27 | Additive migration idempotency and actual recreation fingerprint checks |
| 28 | Retained Phase 1 suite plus real HTTP backward-compatibility checks |

No behavioral test was reported passed without executing it. Intermediate Ruff
format findings were corrected. Code review also hardened calendar overflow,
migration endpoint collisions and monetary evidence serialization; tests cover
these behaviors. The final full test runs had no warnings or failures.
Docker build emits the normal root-pip installation warning during image
construction; containers themselves run the API as the existing non-root user.

## Exact commands and output artifacts

The runtime transcript (historical local artifact; excluded from public candidate) contains exact commands
and captured output for baseline tests/backup, migration, fingerprints, builds,
tests, HTTP, outage and persistence checks. Main commands actually executed:

```powershell
.venv\Scripts\python -m pytest -q
docker compose --profile test run --rm tests
docker compose config --quiet
docker compose up --build -d
docker compose exec -T backend python -m rippleproof.migrate
docker compose exec -T backend python -m rippleproof.migrate
docker compose --profile test build tests
docker compose --profile test run --rm tests
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m pip check
docker compose exec -T backend python -m pip --no-cache-dir check
docker compose --profile test run --rm --no-deps tests python -m pip --no-cache-dir check
docker compose stop falkordb
docker compose start falkordb
docker compose restart falkordb backend
docker compose up -d --wait
docker compose up -d --force-recreate --wait falkordb backend
docker compose exec -T backend python -m rippleproof.migrate
docker compose ps
```

Exact read-only snapshot/export and urllib POST scripts are retained in that
transcript. The complete actual response JSON is linked above.

## Files and remaining risks

Created:

- `rippleproof/inbound_data.py`, `rippleproof/migrate.py`
- `rippleproof/simulation/__init__.py`, `models.py`, `snapshot.py`, `engine.py`
- `tests/simulation_helpers.py`, `tests/test_simulation.py`,
  `tests/integration/test_simulation.py`
- This verification document, runtime log and captured demo response.

Modified:

- `rippleproof/app.py`, `queries.py`, `repository.py`, `__init__.py`
- `tests/test_validation.py`, `tests/test_failure_behavior.py`
- `README.md`, `docs/ARCHITECTURE.md`, `docs/GRAPH_MODEL.md`

No dependency, Docker data-path or Compose service change was needed. Existing
historical verification documents remain intact.

Limits are explicit in every response and the architecture documentation:
materials-only feasibility, day-level dates, no production/factory scheduling,
no historical stock reconstruction, committed receipts treated as authoritative,
no outage-backlog capacity smoothing, no real-world forecasting guarantee,
and no global optimality claim. Search is bounded to 366 days; valid graph
integer fields are bounded to 1e9 and prices to 1e12. Schedule completeness is a
disclosed assumption rather than an audited enterprise-data guarantee.

The API returns verbose evidence for a small graph; large-graph projections,
pagination, request concurrency controls, pricing currencies and advanced
optimization remain future work. Costs are synthetic units, gross additional
procurement only. Operator migration should be serialized against external
writers. There is no authentication product or public deployment.

**Readiness for Phase 3:** the deterministic, typed and graph-backed engine is
verified and suitable to expose later through constrained agent tools. Real
tool calling, LLM explanation, MCP, human approval and persisted decisions are
not implemented. No further setup action is required for this Phase 2 demo;
services are left healthy. STOP here pending explicit Phase 3 approval.

