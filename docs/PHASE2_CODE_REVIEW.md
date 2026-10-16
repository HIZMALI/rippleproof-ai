# RippleProof AI — Independent Phase 2 code review

Reviewed: uploaded `rippleproof-ai.zip` on 2026-10-15.

## Independent verification

- Reviewed modules: `rippleproof/app.py`, `repository.py`, `queries.py`, `simulation/engine.py`, `simulation/models.py`, `simulation/snapshot.py`, data fixtures, tests and verification documentation.
- Ran: `PYTHONPATH=<isolated libraries>:<project> pytest -q -m 'not integration' <project>/tests`.
- Observed: **79 passed, 24 deselected in 1.09s** under Linux Python 3.13.5 with local compatible dependencies. The project-reported test count was 103, including 24 real DB integration tests performed by Codex on Windows/Docker. Independent environment did not have an active FalkorDB container; do not represent the 24 DB tests as independently re-run.
- Verified that deterministic allocation uses common receipt balances and no hardcoded demo projection in runtime API path. Model limitations are disclosed (material feasibility only; no factory capacity or transport costs; greedy optimization, not globally optimal).

## Important reproducible Phase 3 prerequisite

`normalize()` hashes the entire graph into `GraphSnapshot.fingerprint`, and `simulate()` uses it for the scenario ID. Adding an isolated `Decision`/`Evidence` node + `SUPPORTED_BY` edge changed fingerprint and scenario ID despite identical procurement/stock/orders. Independently reproduced with the actual pure engine and a synthetic GraphBuilder snapshot.

**Must fix:** create operational/material fingerprint over only supply-chain node/edge types, excluding memory and approval nodes/edges. Verify in real DB that a decision write leaves it stable and a supplier/stock/cert/order change invalidates it.

## Other quality recommendations

- 923,556-byte captured scenario JSON is unsuitable as-is for LLM tool context. Return compact typed tool summaries with on-demand evidence resolution.
- Keep LLM tools strictly read-only; expose manual authenticated decision approval outside the model's tool set, with stale fingerprint 409 and idempotent graph write.
- Regression-test that decisions do not mutate `InboundShipment` or stock facts, since plans are simulated internal decisions.
- Before public GitHub publication, exclude workstation-specific `.venv`, `.git`, `.local` backup files, oversized logs and system-specific README paths; existing ignore files are already present.

## Decision

**Approve proceeding to Phase 3 with the fingerprint correction as its first mandatory task.** Phase 2 is a solid base; the remaining concerns are precisely bounded and testable in Phase 3.
