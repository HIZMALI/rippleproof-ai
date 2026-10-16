# RippleProof AI — Phase 3 Codex implementation contract

**Event:** Graph Hacks 2026, Track 1 — Agents That Act on Connected Data  
**Team:** MORVE, solo  
**Status:** Phase 2 approved, Phase 3 authorized by the human participant only after this task is supplied to Codex.  
**Submission deadline:** 2026-10-18 23:59 IST / 21:29 Türkiye (UTC+03:00).  
**Primary objective:** a **real graph-driven AI agent**, MCP tool selection, independently reviewable and safely human-approved internal mitigation decisions persisted in FalkorDB.

## 0. Scope and boundaries

Continue IN THE EXISTING REPOSITORY. Read `AGENTS.md`, `docs/PRODUCT_SPEC.md`, `docs/GRAPH_MODEL.md`, `docs/ARCHITECTURE.md`, `docs/PHASE2_VERIFICATION.md`, `tasks/02-simulation.md`, and inspect actual existing source and tests before changes.

The current reference deployment is **145 nodes / 291 relationships**, including 82 inbound shipments. Full test suite last reported **103 passing**, of which **24 are real FalkorDB integration cases**. Reviewer independently reran **79 tests, 79 passed** using the uploaded source (the 24 real DB tests could not be rerun outside the operator's Docker environment). The demo projection is: baseline risk O-122 and O-123; newly at risk O-105 and O-106; both restored with selected 32 P-22 units from S-09 and 100 P-12 units from S-10, gross additional procurement cost **1364.00**.

Retain all previously verified behavior. Do **not** reset/delete containers, graph volumes, previous graph facts, seed data, or backups. Do not run the Phase 1 destructive-style base seed on a live operational graph. Do not push to GitHub, deploy, pay for LLM APIs, place real purchases, contact suppliers, or start frontend/Phase 4. Stop after Phase 3 and provide an actual verification report.

**Development time is limited.** Prioritize Phase 3A, 3B, 3C and 3D. Optional extras are strictly after those gates pass. Use a maintainable minimal implementation, not a speculative agent framework rewrite.

## 1. Phase 3A — Fix a demonstrated graph fingerprint / memory bug (MANDATORY FIRST)

In the uploaded Phase 2 source, `rippleproof/simulation/snapshot.py:normalize()` calculates `GraphSnapshot.fingerprint` from **all** graph nodes and relationships. `rippleproof/simulation/engine.py:simulate()` uses that fingerprint to construct `scenario_id`. Once `Decision`, `Evidence` or their edges are written, an unchanged supply chain produces a different `scenario_id`.

The reviewer **reproduced the bug independently:** appending an isolated `Decision` and `Evidence` node plus `SUPPORTED_BY` edge preserved all material-risk results but changed both fingerprint and scenario ID.

Implement a **separate operational/material fingerprint**, based on exactly the relevant operational facts (Supplier, Part, Product, Order, Certificate, InboundShipment and SUPPLIES, USES, CONTAINS, REQUIRES_CERT, HOLDS_CERT, FULFILLS, FOR_PART edges). Decision/Evidence/agent memory nodes and their edges must not affect the operational fingerprint. A change to relevant source data *must* change it. Preserve coherent snapshot reads and explicit evidence references. If retaining a complete physical-graph fingerprint is useful, give it a separate clearly named field, but do not use it for scenario validity.

Keep existing `scenario_id` semantics stable before/after adding decision memory, and make backward-compatibility/migration choices explicit. Never allow memory writes alone to trigger a fake "source data changed" conflict.

**Tests:** verify unchanged risk + unchanged operational fingerprint + unchanged scenario ID after inserting Decision/Evidence. Test change to stock, supplier status, offer price, order deadline, certification expiry and shipment timing changes fingerprint; tests must query real FalkorDB for at least one material-change and one memory-only change.

## 2. Phase 3B — Actual MCP graph tools, not a naming-only wrapper

Use a pinned, maintained Python implementation of the Model Context Protocol SDK. Create an executable MCP server using a supported transport, preferably `stdio` for a simple local demo, and cleanly documented start commands. The service must expose a constrained, typed tool registry with genuine FalkorDB-backed operations:

- `graph_summary`: scoped counts, graph readiness.
- `trace_supplier_impact`: multi-hop supplier–part–product–order paths, with stable evidence node/edge refs.
- `evaluate_part_alternatives`: actual alternative terms and certification checks on specified date.
- `simulate_supply_disruption`: invoke the existing deterministic Phase 2 engine with validated date boundaries; compact result of baseline/disruption/mitigation, missing-data flags, costs, selected supplier allocations and citation/evidence refs.
- `get_decision_history`: read approved/internal decision history and linked evidence from FalkorDB.

MCP methods are **read-only or pure simulations**. Do not expose raw Cypher, unrestricted database writes, filesystem access, network downloads or generic code execution as MCP tools. Every parameter must use the existing Pydantic validators or equivalent strict validation. Handle non-existent IDs, excessive data, timed-out queries, missing database, and tool errors explicitly. Cap payloads; never silently omit critical information (return counts, truncation indicators, and a way to inspect specific evidence). Do not pass the existing ~900 KB full simulation JSON into the LLM context as a tool response.

Provide a documented smoke test that uses an **actual MCP client** to enumerate and invoke the MCP tools and returns FalkorDB-backed evidence from the running service. Calling a Python helper directly does not satisfy the MCP end-to-end acceptance gate.

## 3. Phase 3C — Real model tool-calling agent (with truthful no-key behavior)

Implement a small bounded agent coordinator capable of answering a natural-language question by **actually selecting and invoking MCP tools**. The chosen language-model integration must be explicitly configured by environment variables. Prefer one clear provider abstraction rather than several competing frameworks. Use pinned dependencies, bounded timeouts, tool-call limits, a finite turn budget, and safe input validation. Do not make billable remote requests without the operator's approval.

Expected agent flow:
1. Parse the operator's request and identify missing fields. If necessary, ask for the supplier ID and outage dates instead of inventing them.
2. Choose among constrained MCP tools; execute calls through an actual MCP client and read actual graph-backed output.
3. Use the deterministic engine's computed amounts/statuses as ground truth. If the model invents quantities, discounts, certificate facts or evidence IDs, detect/reject and produce a safe structured answer.
4. Respond with explicit scenario window, at-risk and restored orders, proposed *internal* plan and gross incremental procurement cost; show the **graph evidence paths** and limitations.
5. If the graph is unavailable, issue a visible error and never return fixture-based or hardcoded answers.

Make the real model integration testable using a mock transport/provider that emits tool calls. A "no API key" mode may offer a deterministic, expressly labeled **guided walkthrough** of the same MCP tools for the jury, but **MUST NOT** claim to be an autonomous AI agent or silently produce fake tool traces. Document that full agent acceptance requires at least one operator-authorized real provider run and captured MCP call trace. It is acceptable to report real-provider verification as pending when credentials are unavailable; it is NOT acceptable to claim it passed.

Suggested API (adjust to existing FastAPI patterns without breaking Phase 1/2): `POST /api/agent/run` with typed question and optional structured scenario fields; return structured `mode`, `response`, `tool_trace` (names, timestamps, status, small evidence refs), `scenario_id`, assumptions, warnings, and error status. No secret values or chain-of-thought disclosure in logs/traces.

Track 1 explicitly values multi-hop reasoning, graph tools, MCP tool selection, actions based on the graph and explainable output; demonstrate all five.

## 4. Phase 3D — Human-approved, graph-persisted INTERNAL decisions

Write *decisions*, not supplier purchase orders. An approved mitigation plan is an internal scenario decision — it does not mutate inventory, create actual inbound shipments, change order status, contact suppliers, or transact real money.

Implement a two-step control path with strict API models:

**Prepare:** accept a scenario and a selected server-calculated `mitigation_plan_id` / policy. Re-run or retrieve and validate that plan from the actual graph, show complete quantities, cost, certification evidence, selected suppliers and snapshot operational fingerprint, and return a typed preview. The client may **choose a plan identifier** but must not be able to set authoritative costs, quantities, certificate validity or evidence IDs. The preparing step MUST NOT persist an approval.

**Approve:** require explicit human confirmation and a server-configured approval secret (for a localhost-only demo, document safe local setup and never hardcode the token). Require an idempotency key, expected `scenario_id` and expected **operational fingerprint** from the preview. Recalculate and compare the scenario from fresh graph data, fail with **HTTP 409** when relevant facts or selected plan changed. Reject unknown plans, fake evidence, altered prices, unapproved auto-actions and malformed input. Approval remains an *internal*, non-procurement record.

Persist in FalkorDB using stable identities, e.g. `Decision`, `Evidence` and connections such as `SELECTS`, `AFFECTS`, `SUPPORTED_BY`. Evidence must reference actual prior source nodes/relationships and capture the stored plan revision, operational snapshot reference, decision time, operator ID (non-sensitive demo pseudonym), selected policy, quantities, total cost, rationale, and limitations. No fabricated graph evidence nodes posing as supplier data. Make the approval write idempotent and as atomic as practical with tested FalkorDB Cypher: repeated same key/same request returns the original decision, while the same key/different payload conflicts (409). Prevent partial edge writes and duplicate Decision/Evidence records. Reconcile persistence correctness after Docker restarts and process restarts.

Recommended API: `POST /api/decisions/prepare`, `POST /api/decisions/approve`, `GET /api/decisions/{decision_id}`, and optional read-only `GET /api/decisions?scenario_id=...`. The agent can produce a prepare link/plan suggestion, but **MUST NOT approve it autonomously**. A direct LLM tool call must not perform approval. Do not open write endpoints to a public Internet deployment without a stronger authenticated operator workflow and rate limits; current stack binds to localhost.

Avoid stale-check race claims: either implement and test an effective compare-and-write guard in one server-side transaction, or document/localize the limitation and ensure single-worker demo operation; never label an untested check "atomic".

## 5. Tests, mandatory proofs and adversarial checks

At minimum maintain all **103** reported Phase 2 tests, then add tests for:

1. Memory-only graph changes do not change operational fingerprints or scenario IDs.
2. Material graph changes do change them.
3. Real MCP client invokes actual typed tools with graph-derived responses.
4. Agent mock model selects tools and receives actual tool results, including multi-step calls.
5. Wrong/missing model credentials produce an honest error/guided mode, never pretend to run a model.
6. Tool selection is bounded; no arbitrary Cypher, system commands or local file operations.
7. Scenario ID and evidence refs agree with actual tool inputs and graph facts.
8. Existing cost/capacity/certification invariants still hold.
9. Preparing a decision does **not** mutate graph.
10. Approval requires correct explicit token, confirmation and idempotency key.
11. Tampering with quantities, cost, supplier or evidence is blocked (authoritative recomputation).
12. After stock, certificate, offer or shipment change, stale previews reject with HTTP 409.
13. Same-key same-decision replay is idempotent, even after restart.
14. Same-key different-decision request is a conflict.
15. Decision/Evidence relationships reference actual graph facts and remain retrievable across service/container recreation.
16. Approved internal decisions do not alter next simulation's actual inventory or procurement bookings.
17. Graph unavailability produces 503 for read, agent, prepare and approval flows.
18. Model timeout, malformed tool output, malicious graph text, unknown IDs, long questions and over-budget graph results fail safely.
19. At least one real integration test confirms the original graph's 145/291 operational facts stay unchanged by decision persistence (overall totals may grow as decisions are added).
20. Existing API compatibility, Ruff lint/formatting, pinned dependencies and Compose validation.

Avoid test pollution: use a dedicated isolated test graph or transactional cleanup that never deletes the live `rippleproof` graph. **Never run destructive tests against the existing demo graph**. Validate a full README demo run on localhost. Publish real command logs, real passed counts, real HTTP samples, and the actual MCP transcript without secrets in `docs/PHASE3_VERIFICATION.md`.

## 6. Efficiency and presentation requirements

- Do not overload the LLM with the existing massive `ScenarioResponse` (~924 KB captured in Phase 2). Provide a compact structured summary; allow later evidence drill-down.
- Deterministic calculations and constraints stay in `simulation/engine.py`; agent must not recompute prices or allocate material using hallucinated numbers.
- Keep filenames clean, use stable IDs and explicit `created_at` timestamps, preserving auditability.
- Seed/demo fixtures remain synthetic only.
- Keep keyboard-friendly endpoint demo and clear, self-contained PowerShell examples.
- Prepare a 3-minute demo walkthrough: disruption → MCP tools → evidence → plan comparison → human approval → process restart → same decision retrieved → fresh operational data change causes stale rejection.
- Review README for machine-specific absolute Windows paths, and write copy/paste commands that work from an arbitrary extracted project directory.
- **Publication hygiene:** the uploaded working ZIP includes `.venv`, `.git`, `.local/backups` and large verification logs. They were needed for private review but must not be uploaded as a public source-code release. Existing `.gitignore`/`.dockerignore` should stay effective; use Git-tracked project files for the public repo and audit for secrets/PII before pushing. Do not delete the originals.

## 7. Phase 3 completion report required from Codex

1. Files created/modified; short architecture diagram.
2. Existing vs new graph labels/relationships, and whether the original operational graph facts survived untouched.
3. Exact MCP tool inventory and a **real MCP-client call trace**.
4. An actual agent response and whether it came from real model API vs labeled guided mode.
5. Real prepare/approve/stale/replay HTTP status codes and evidence refs.
6. Full exact test results, including real FalkorDB integration tests.
7. Independent evidence that decision persistence does not alter scenario fingerprint or supplies.
8. No passwords, keys, `.env`, private paths or personal data in publishable outputs.
9. Unresolved blockers and credentials the operator must supply; no made-up successes.
10. **STOP**. No Phase 4 UI; no GitHub push, deployment, paid API call, graph reset or volume deletion.

## 8. Acceptance gates

- P3A fingerprint bug repaired and tested in real FalkorDB.
- P3B actual MCP client/server working with graph-derived evidence.
- P3C genuine agent tooling functioning (using a mock provider in CI; real-provider smoke run separately pending permission/key if necessary).
- P3D preview, manual approval, durable decision, stale rejection and replay safety working.
- All prior test gates pass; new cases pass; data persists across restart.
- Honest verification report and disclosed limitations; do not claim full acceptance of the real LLM until independently executed.
