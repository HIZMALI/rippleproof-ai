# Phase 4 verification — RippleProof AI

Implementation and verification: 2026-10-15 UTC / 2026-10-15–16 Europe/Istanbul.
Scope: Phase 4 frontend only, preserving Phases 1–3. No Phase 5, GitHub push,
remote deployment, paid model call, real purchase, supplier contact or database
reset. Phase 4 is complete and verified; the running services are healthy.

## Running application

From `<repository>`:

```powershell
docker compose up -d --build
docker compose ps
```

Open [RippleProof](http://127.0.0.1:18080/#/overview).
[Workbench](http://127.0.0.1:18080/#/workbench),
[Ledger](http://127.0.0.1:18080/#/decisions), and
[FastAPI docs](http://127.0.0.1:18000/docs) are available locally.
No seed or migration is needed for the existing graph. Frontend/API/DB bind
only to 127.0.0.1 on ports 18080/18000/6379. The web service is an unprivileged
Nginx container serving the actual optimized React build, not a dev mock server.

Docker client/server: 29.4.2; Compose: 5.1.3. Host Node: 24.13.1, npm: 11.8.0,
Python: 3.14.0; Docker backend Python: 3.12.15. `nginx -t` passed. Index responses
have `Cache-Control: no-cache`; proxied health/API responses have `no-store`.
Actual index, health and summary responses include CSP and `X-Frame-Options: DENY`.

## Implemented behavior

- Overview: actual backend health, separate operational/physical counts, genuine
  empty analysis state, source scope, current evaluated disruption and comparison.
- Workbench: editable supplier and scenario dates, exclusive-end semantics,
  mitigation toggle, inline calendar/window validation, loading/cancel/retry,
  server-derived policy choice and fresh internal preview.
- Material engine views: actual coverage and at-risk sets for three scenarios,
  newly affected/restored sets, gross additional cost, order BOM shortfalls,
  pagination, proposed quantities/dispatch/arrival/cost and model assumptions.
- Evidence: focused Cytoscape chain with actual stored edge directions/IDs,
  source property inspector, searchable/filterable paths, fit/reset, bounded
  pagination, clickable nodes/edges and keyboard source-reference alternatives.
- Alternatives: per-part, projected-arrival qualification, offer terms, booked
  capacity, holding/requirement citations, rejected and unknown states. No global
  supplier compliance badge is inferred.
- Guided walkthrough: actual `/api/agent/run` guided execution and MCP trace;
  ordered tools, source references, timestamps, output size/hash and factual
  response. Explicitly deterministic, with zero model calls from the response.
  This interface has no paid-agent invocation control.
- Full decision review: freshly recalculated schedule, costs, all returned
  certificate evidence, limitations, scenario hash/revision and staleness rules
  before separate explicit manual authorization. Token clears per attempt,
  close and navigation; 409 discards all inputs and requires a fresh review.
  Exact-intent retry preserves its idempotency key. Non-loopback approval is
  disabled. Approval means an internal record, never a purchase or reservation.
- Ledger: real empty/populated history, scenario filter, five-record pagination,
  known-ID lookup, persisted detail, archive references and explicit fresh-source
  comparison. Historical records are not silently described as current plans.
- Responsive design: three-column desktop, two-column tablet with inspector
  drawer, stacked mobile comparison/vertical graph/expandable material panel and
  fixed scenario action. Named horizontal table regions contain their overflow.
  Native modal focus containment/Escape, focus restoration, skip link, explicit
  accessible names, reduced motion and status text accompany visual states.

## Contracts and backend change

The running `/openapi.json`, Python Pydantic models and actual responses were
read before frontend contracts were written. The generator produces 41 Zod
validators with inferred strict TypeScript types. Every successful response is
validated; oversized results fail closed at 6 MiB. Cancellable requests have
bounded timeouts. Only transient safe GETs retry once; POST retry is manual.
Full graph JSON is not rendered by default; Cytoscape loads as a separate chunk.
Costs use backend decimal strings without client monetary arithmetic.

No route was added or renamed and no graph schema/engine logic was changed.
One independently observed existing API defect was fixed in `rippleproof/app.py`:
strict MCP paging integers rejected ordinary URL `offset=0&limit=5`, returning
422. `DecisionHistoryQuery` converts ASCII decimal query values then applies
the inherited strict bounds. JSON/MCP `HistoryInput` remains strict. Two genuine
FalkorDB regression tests cover successful paging/filtering and invalid queries.

| Actual route | Frontend use / observed behavior |
| --- | --- |
| GET `/health` | Backend readiness, graph existence; empty and unavailable tested |
| GET `/api/graph/summary` | Real source and physical-memory counts |
| GET `/api/impact-paths?supplier_id=S-04` | Real dependency paths before calculation |
| GET `/api/alternatives?part_id=P-22&as_of=2026-10-15` | Certificate-only checks, explicitly distinguished from simulation feasibility |
| POST `/api/scenarios/simulate` | Full deterministic comparison and evidence; mitigation-off verified |
| POST `/api/agent/run` | Guided real MCP trace; unauthorized agent request tested on isolated backend with zero model calls |
| POST `/api/decisions/prepare` | Read-only full server plan for selected policy |
| POST `/api/decisions/approve` | Isolated internal persistence, 401/409/422/503, replay and lost-response recovery |
| GET `/api/decisions?offset=0&limit=5` | Real empty/live and populated/isolated history; paging and filtering |
| GET `/api/decisions/{id}` | Actual persisted detail and actual missing-ID 404 |

History has no typed OpenAPI response. Its explicit Zod schema was checked
against `history_item`, empty live HTTP and populated isolated HTTP. The existing
untyped endpoint remains compatible.

## Actual graph and API evidence

The live graph was **145 operational/physical nodes and 291 relationships** before
work, including 82 inbound shipments and zero Decision/Evidence nodes. It remains
the same. The complete normalized operational snapshot was compared to the private
pre-work backup, not just aggregate counts. No live seed/migration was run.
The existing volume and previous backups/audit graphs were preserved.

```text
graph: rippleproof
scenario_id: SC-4990e7e493adea7efa18
operational fingerprint:
d3c35628f3c00ce059907dfbe57a6acfa639d5b95f931b650a7faeb55abee19e
```

Actual simulation projection (not a runtime fixture):

```json
{
  "materialCovered": {"baseline": 19, "disrupted": 18, "mitigated": 20},
  "newly_at_risk_orders": ["O-105", "O-106"],
  "restored_orders": ["O-105", "O-106"],
  "additional_cost": "1364.00"
}
```

S-04 → P-22 ← PR-05 ← O-101 is returned by actual graph evidence, with SUPPLIES,
USES and CONTAINS source identities. O-101 is connected and remains covered.
The reference run reports 11 dependent open orders, distinct from two newly
at-risk orders. At P-22's evaluated arrival, S-09 has C-01/C-02 and S-10 lacks
C-02; at P-12's arrival, S-10 has required C-01. The source response includes
holding IDs and valid-through dates, not only boolean eligibility.

The selected plan proposes S-09/P-22 quantities 27 and 5 (costs 391.50 and 72.50),
and S-10/P-12 quantities 70 and 30 (630.00 and 270.00). The 132 new units cost
1,364.00 gross synthetic cost units. These are optional proposals; no shipment
was booked in the operational graph.

Actual guided response: `guided_walkthrough`, `model_requests: 0`. Its real MCP
tools, all `ok`, are:

1. `graph_summary` — 874 output bytes.
2. `trace_supplier_impact` — 1,508 output bytes.
3. `simulate_supply_disruption` — 11,841 output bytes.
4. `get_decision_history` — 126 output bytes for the empty live ledger.

The UI trace uses actual timestamps/hashes/refs. No model call was fabricated or
paid for. See [sanitized HTTP evidence](verification/phase4/live-api-evidence.json).

## Approval and persistence evidence

Successful browser approval was exercised **only** in a newly created
`test_rippleproof_p4ui_*` graph, using `browser-test-harness` and an explicit
synthetic test rationale. It is not represented as a live human approval.
The same FastAPI app, real FalkorDB, real preview and real write were used.

The test committed once, deliberately dropped that browser response, then
re-entered its transient test credential and retried the exact action. The key
and request stayed identical; the backend returned the existing Decision.
At that checkpoint counts changed 145/291 → **147/441**, with one Decision and
one Evidence archive, actual provenance links and unchanged operational hash.
The Ledger retrieved the record and verified its current source. After restarting
the isolated backend, the same stored record was retrieved unchanged.
Later paging tests create six additional synthetic internal records in that
isolated graph; they do not change the live graph. Its final verified physical
counts are 159 nodes / 1,341 relationships, with seven Decision and seven Evidence
nodes. See [isolated final counts](verification/phase4/isolated-final-summary.json).
Graphs are retained for audit.

Real 409 was induced by a parameterized P-22 stock change only in the isolated
graph, restored afterwards. Inputs/credential/confirmation were discarded,
the scenario result removed, and the server preview refreshed for manual review.
401 used a wrong test token; 422 modified the actual wire confirmation before
calling the real server; 503 used the same backend with approval disabled.
No failure test fabricated a success response. Traces, HAR and videos were off;
browser local/session storage stayed empty. Test secrets/control files are
ignored under `.local`; screenshots contain no token.

See [isolated persistence](verification/phase4/isolated-persistence.json),
[data preservation](verification/phase4/data-preservation.json), and
[production restart](verification/phase4/production-restart.json).
The live graph still contains zero internal decisions from this work.

## Actual test results

| Check | Executed result |
| --- | --- |
| Pre-change backend baseline | 166 passed in 55.62s |
| Focused real decision integration after fix | 21 passed in 7.45s |
| Full backend, host Python 3.14 | **168 passed in 60.89s** |
| Full backend, Docker Python 3.12 | **168 passed in 45.62s** |
| Real integration coverage | 76 of 168 collected as integration; 92 other tests |
| Vitest component/unit tests | **43 passed**, three files, final check duration 1.45s |
| Full browser suite | **15 passed (2.2m)**; zero failed/skipped; Chromium 156 |
| Ruff lint / formatting | Passed; 45 Python files formatted |
| TypeScript / ESLint / Prettier | Passed |
| Production Vite build / Docker image | Passed |
| Python dependency validation | No broken requirements |
| `npm audit` | Zero reported vulnerabilities |
| Compose config / Nginx config | Passed |
| Complete live operational snapshot comparison | Equal to pre-work backup |

See [sanitized browser results](verification/phase4/browser-results.json) and
[visual capture review](verification/phase4/visual-review.json).

The previous 166 backend tests remain; two paging regressions were added.
Vitest's transport mocks and isolated component props are explicitly separate
from integration evidence. Browser tests use actual production same-origin HTTP,
real graph calculations, genuine MCP and the real isolated approval backend.
They check all four widths, no document overflow, source-reference interaction,
no uncaught page errors or console/network failures on the happy path, and axe
violations equal to zero on the workbench at each width and decision preview.
Native dialog containment/Escape and credential clearing are checked in a real
browser. Automated accessibility checks are not a full assistive-technology audit.

The empty/unavailable tests run the real app against an absent isolated graph
and a real unavailable database TCP address, without mocks. The separate Docker
test actually stops and starts the production backend, checks disabled actions
and hidden stale outcomes, recovers, and verifies identical full simulation and
counts. FalkorDB and its volume are never stopped/deleted for that test.
Expected negative HTTP responses and database-connection warnings are recorded
as failure-path evidence, not described as clean happy-path traffic.
The final production capture run also reported zero console/page errors. A
byte-level scan of the frontend bundle and public verification artifacts found
no occurrence of the private browser-test credential.

## Problems found and fixed during execution

- Existing HTTP history query bug: strict JSON integer validation rejected URL
  digits. Fixed at the HTTP adapter, with two real-server regression tests.
- Browser accessibility findings: missing names in collapsed navigation and
  concatenated brand label; corrected visible/accessible text. The mobile action
  bar gained an explicit landmark. Final axe checks report no violations.
- Visual defects: sticky form action overlapped a mobile date input; replaced
  with a separate fixed mobile action. Mobile graph became a legible vertical
  chain; tablet received an actual drawer; schedule/assumption panel spacing and
  route scroll/focus were refined. All widths contain their table overflow.
- Actual Docker stop test exposed HTTP **504** handling: old health remained
  ready after a proxy connect timeout. Added source invalidation and safe 504
  messaging plus three unit regressions; bounded Nginx DNS resolution to 3s.
  The focused real stop/start browser rerun passed in 10.1s.
- Windows test-control file replacement briefly raised `PermissionError` while
  another local process held the file. Added bounded replacement retry; no graph
  was reset or silently substituted.
- Chromium DevTools intermittently could not retrieve a streamed no-store
  simulation body. Tests now assert the actual browser HTTP status and UI result,
  and validate an identical independent read-only HTTP calculation. No browser
  response is replaced or forged in the happy path. The lost-response and 422
  tests explicitly inject faults while still using real server results.
- Test expectation corrected: an agent request missing a scenario legitimately
  asks for clarification with 200; the authorization-gate test now supplies the
  complete scenario and observes the real 503/zero model calls.
- Development checks initially caught two Python formatting lines; corrected.
  The PowerShell check logger needed `Tee-Object -FilePath` for append support;
  corrected and the complete script was executed successfully.
- A one-off report assembly command used the Windows default text encoding;
  it failed visibly on UTF-8 text. Re-ran with explicit UTF-8 and corrected two
  README en-dash encoding artifacts. Product source and test results were intact.

Earlier failed browser runs were used to diagnose these issues; they were not
reported as passes. Final results above replace neither the failures nor their
explanations. Non-blocking install warnings: jsdom's transitive `whatwg-encoding`
deprecation and Playwright's NO_COLOR/FORCE_COLOR environment warning.

## Screenshots and review

All captures are actual Chromium UI connected to the backend. No generated
dashboard imagery or image editing was used. `isolated-*` images are test-only.

| View | Actual screenshot |
| --- | --- |
| Desktop 1440 | [Workbench](verification/phase4/workbench-1440.png), [Overview](verification/phase4/overview-1440.png) |
| Tablet/laptop 1024 | [Workbench](verification/phase4/workbench-1024.png), [Overview](verification/phase4/overview-1024.png) |
| Tablet 768 | [Workbench](verification/phase4/workbench-768.png), [Overview](verification/phase4/overview-768.png) |
| Mobile 390 | [Workbench](verification/phase4/workbench-390.png), [Overview](verification/phase4/overview-390.png) |
| Actual guided MCP | [Trace](verification/phase4/guided-mcp-desktop.png) |
| Fresh read-only decision preview | [Preview](verification/phase4/decision-preview-desktop.png) |
| Isolated persistence / history | [Record](verification/phase4/isolated-persisted-record.png), [Ledger](verification/phase4/isolated-decision-ledger.png) |
| Isolated failures | [Stale preview](verification/phase4/isolated-stale-preview.png), [Unavailable](verification/phase4/isolated-unavailable.png) |

Full-page browser captures can show fixed controls at the original viewport's
bottom. The additional `*-viewport.png` images show their actual viewport placement.
See [mobile evidence](verification/phase4/mobile-evidence.png) and
[tablet inspector](verification/phase4/tablet-inspector.png).

## Files created and modified

Created frontend package:

- `frontend/package.json`, `package-lock.json`, `tsconfig.json`, `vite.config.ts`,
  `eslint.config.mjs`, `playwright.config.ts`, `index.html`, `public/favicon.svg`.
- `frontend/Dockerfile`, `nginx.conf`, `.dockerignore`.
- `frontend/src/main.tsx`, `App.tsx`, `styles.css`, `api/client.ts`, `api/contracts.ts`,
  `lib/format.ts`, `lib/useMediaQuery.ts`, `components/ui.tsx`.
- `frontend/src/features/overview/Overview.tsx`; `scenarios/ScenarioForm.tsx`,
  `Comparison.tsx`, `OutcomeDetails.tsx`; `evidence/GraphCanvas.tsx`,
  `EvidenceExplorer.tsx`, `MaterialInspector.tsx`; `agent/AgentPanel.tsx`;
  `decisions/DecisionReview.tsx`, `PlanDetails.tsx`, `Ledger.tsx`.
- `frontend/tests/setup.ts`, `format.test.ts`, `client.test.ts`, `components.test.tsx`;
  `frontend/e2e/approval.spec.ts`, `workspace.spec.ts`, `z-restart.spec.ts`;
  `frontend/scripts/generate-contracts.mjs`, `capture.mjs`.
- `scripts/phase4_test_backend.py`, `verify_phase4.ps1`, `verify_phase4_data.py`;
  this report, `docs/DEMO_PHASE4.md`, and `docs/verification/phase4/` evidence.

Modified existing files: `rippleproof/app.py`, `tests/integration/test_decisions.py`,
`compose.yaml`, `.env.example`, `.dockerignore`, `.gitignore`, `README.md`,
`docs/ARCHITECTURE.md`. No operational schema, seed or simulation engine changed.
Repository remains on `main`; no commits or remote push were created.

## Exact implementation/verification commands

Commands were executed from the repository root unless a frontend directory is
shown. Read-only file discovery used `rg`/`Get-Content`. Complete named check output
is in checks.txt (historical local artifact; excluded from public candidate). Script sources contain exact
HTTP paths, bodies, isolated controls and browser assertions; private tokens are
read locally and never included here.

```powershell
docker version --format '{{.Client.Version}} / {{.Server.Version}}'
docker compose version
node --version
npm --version
.venv\Scripts\python --version
docker compose exec backend python --version
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m pytest -q tests/integration/test_decisions.py
.venv\Scripts\python -m pytest --collect-only -q -m integration
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m ruff format rippleproof/app.py scripts/phase4_test_backend.py tests/integration/test_decisions.py
docker compose up -d --build backend
docker compose build frontend
docker compose up -d --build frontend
docker compose --profile test build tests
docker compose --profile test run --rm tests
docker compose config --quiet
docker compose ps
docker compose exec frontend nginx -t
.\scripts\verify_phase4.ps1
.venv\Scripts\python scripts/verify_phase4_data.py

Set-Location frontend
npm run contracts
npm run dev
npx playwright install chromium
npm install --save-dev --save-exact prettier@3.9.10
npx prettier --write src tests e2e *.ts *.mjs *.json index.html scripts/*.mjs
npm run typecheck
npm run lint
npm run format:check
npm test
npm run build
npm audit
npm run test:e2e -- workspace.spec.ts
npm run test:e2e -- z-restart.spec.ts
npm run test:e2e
node scripts/capture.mjs
```

The initial Vite process was stopped with Ctrl+C before binding the Compose
frontend to 18080. Browser controls execute the real test app through
`.venv\Scripts\python scripts/phase4_test_backend.py serve` on 18001, and Vite
`npm run dev -- --port 18081` with server-only `BACKEND_ORIGIN` pointing to it.
They invoke `normal`, `restore`, `stale`, `restart`, `empty`, `unavailable`, and
`approval-disabled` actions against that isolated harness. The separate production
restart test invokes exactly `docker compose stop --timeout 3 backend`, then
`docker compose start backend` in `finally`. No volume command is used.

## Limits and remaining human actions

- A real paid LLM call remains unexecuted and unauthorized. Guided MCP is fully
  exercised; real-provider credentials and separate permission remain required.
- No live human approved a record during automated work. Live approval remains
  disabled until an operator configures a backend secret and performs the explicit
  localhost review. The isolated evidence is labeled accordingly.
- Local token authorization is not production authentication. No XSS-free or
  secure memory-erasure guarantee is claimed. No multi-writer transactional
  guarantee is claimed; preserve the backend's one-worker/serialized-writer rule.
- Chromium 156 was tested at desktop/tablet/mobile viewport sizes. Physical
  touch devices, Safari, Firefox and a complete screen-reader audit remain
  unverified. Axe success does not replace manual assistive-technology testing.
- The deterministic engine retains all Phase 2 limitations: synthetic data,
  materials-only deadlines, greedy allocation and modeled arrival/capacity/cert
  semantics. No execution of procurement or guarantee of delivery exists.
- Availability is polled (10s health / 15s summary), not pushed. Network requests
  and proxy resolution are bounded; a just-failed service may be detected at the
  next poll unless an explicit calculation reports failure first.
- Frontend accepts up to 6 MiB per response; broader datasets may need a future
  bounded projection. Tables/path/history paginate; archived source JSON is not
  loaded wholesale into the UI. Source changes still require re-evaluation.
- Test `.venv`, Chromium install, local test ports, private backup and `.local`
  audit state are local prerequisites. Retained isolated graphs consume storage;
  none were deleted by Phase 4 verification. Review sources before submission.

Phase 4 stops here. Phase 5 remains unstarted and requires separate approval.
