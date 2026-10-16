# Task 05 — Release readiness, genuine agent gate, and submission preparation

## Boundaries
Phase 5A is **authorized for local, non-billable preparation only**. Phase 5B (remote API calls, public push, demo video public upload, and organizer submission) requires **separate explicit human authorization**. Nothing in this task provides it. Do not interpret the presence of a key or an environment variable as authorization to spend or publish.

Project: RippleProof AI / MORVE / Track 1. Avoid large refactors, visual redesigns, new datasets, infrastructure migrations or unrelated enhancements. Keep the existing app, stable scenario and known-good recordings intact.

### Workstream A: baseline and regression protection (P0)
- Read AGENTS.md, Phase 4 report, READMEs, Compose and current source. Inventory all routes and runtime security settings.
- Before modifying code, capture **actual** working backend/frontend health, graph fingerprint, operational node/edge counts, scenario ID and canonical scenario result. Record the run environment/time.
- Ensure there is a recoverable backup of the existing graph. Do not generate or overwrite a backup at a path that already exists; never print contents, destroy, reset or reseed the live graph.
- Re-run the existing 168 backend tests (host and Docker if available), 43 Vitest tests, 15 browser E2E tests (if safe prerequisites available), typecheck, ESLint, formatting, Ruff, dependency checks and production build. Report deviations accurately, no fabricated passes.
- If tests require destructive isolated graphs, use uniquely named test graphs and a proof of isolation. Never run approval tests against the live graph.

### Workstream B: genuine graph-agent demonstration (P0, non-billable preparation)
- Critical gap: Phase 4 UI only exposes GUIDED mode (real MCP transport but `model_requests:0`). It must never be labeled an autonomous LLM agent.
- Inspect `POST /api/agent/run` modes, provider constraints and actual schemas. Prepare a **capability-gated** path to demonstrate `mode:'agent'` with explicit operator intent when the backend provider is independently authorized and enabled. Reuse the existing backend. Do not expose keys to browser or add provider keys to frontend build variables. Never make background or automatic paid calls. Provider-disabled UX must remain safe and make ZERO model calls. If implementing UI changes creates risk, prepare a separate controlled CLI demonstration instead; document which path is chosen and why.
- Distinguish in UI/reports: Guided MCP = deterministic real tool calls, Controlled/mock provider = model simulator, Real provider = externally executed LLM verified by provider metadata + trace. Never claim the third using the first two.
- Add tests that **simulate transport without network** to cover: real-mode button disabled if unavailable; explicit one-click intentional invocation when enabled; bounded timeouts/cost controls; cancels/duplicate-submit protection; schema validation and source-grounded trace; back-end status and stale data. Do not invoke billable APIs. Include a safe fallback for judges with no API key (guided mode, clearly labeled).
- Before a real provider acceptance test, STOP and ask operator: provider/model, spend limit, max number of invocations, whether the operator will configure a secure key themselves. Only after explicit approval may a **separate** bounded test be run. Capture sanitized model provider identity, actual `model_requests > 0`, MCP tool selection, real graph evidence and grounded answer. Strip credentials and sensitive raw requests from all reports. A model call without real MCP action is not sufficient.

### Workstream C: clean public repository candidate (P0, no public push)
- IMPORTANT: The user-uploaded ZIP contains `.git`, `.venv`, `.local`, `frontend/node_modules` and other state. It is not publishable wholesale. Generate a **separate clean export**, retaining source, tests, lockfile, Compose/Docker setup, LICENSE only if license chosen by operator, relevant docs, and synthetic fixtures.
- Exclude `.env`, `.local`, `.venv`, `.git`, `**/node_modules`, tests caches, test-run browser artifacts, backups, browser profiles, API keys, approval secrets, local history and raw logs. Verify exclusions inside the final clean export by enumerating its archive paths; do not trust `.gitignore` alone. Scan content and history for secrets before publication. Flag any potential real secret for operator review, do not print its value.
- Audit generated screenshots, verification logs and demo data for personal identifiers and tokens. Preserve useful small, **sanitized** evidence; put large raw/debug captures outside the release tree. Remove hardcoded Windows user home paths and localhost links that cannot work for judges unless explicitly labeled as local examples.
- `LICENSE` is missing from the uploaded root. Explain choices and request the owner's decision. Do not silently select a license, sign a CLA or change ownership statements.
- Check third-party license/attribution compliance. Keep README AI-assistance disclosure describing participant oversight and testing accurately.
- Verify git history after hackathon start: report it honestly; no rewriting/retroactive timestamps or fictitious authors. Public repository not created/pushed without explicit authorization.

### Workstream D: reproducible installation and failure-free demo (P0)
- Verify from a **separate pristine working directory** and **isolated named Compose project + own volume**, with unique localhost ports. Do not reuse the live `rippleproof` graph or its volume. On a fresh graph, use documented `seed` then `migrate`, run app and check all main UI/API functions. Avoid `docker compose down -v` in either project; clean up only after user consent.
- Carefully differentiate: `docker compose up --build -d` on existing graph needs no seed; freshly cloned repo needs explicit seed and additive migration. Both paths should be easy to follow on Windows PowerShell and macOS/Linux shell, no magic private fixtures.
- Verify open-source setup requirements: Docker Desktop/Compose, frontend availability, backend health, one-command start once seeded, persistent data after `restart` and `up --force-recreate`. New clean-clone validation must not rely on `.local` or preexisting volume data.
- Pin reproducible container images **by stable version or digest after verifying availability** instead of `latest` if feasible without destabilizing the tested volume. Do not silently upgrade FalkorDB or mutate the persistent data directory. No remote deployment in 5A.
- Verify graph-to-action anti-decoration: stop/disconnect FalkorDB in an **isolated** setup; prove dependency analysis/simulation/MCP cannot silently answer from fixtures; do not disable the live database to record a video. Restore isolated state in finally blocks.
- Create `docs/CYPHER_AND_EVIDENCE.md`, a concise transparent description of required read-only traversals, stable evidence paths and safe guarded decision persistence. Use real query files from this repo, not pseudocode passed off as source.
- Create a first-page README with project problem, three steps to run, graph centrality, source of truth, limitations, scenario output and short demo. Never claim delivery scheduling, real procurement, global optimization or autonomous work in guided mode.

### Workstream E: presentation and publication package (P0; preparation only)
- Prepare a truthful 3-ish-minute **screen-recording plan** in `docs/SUBMISSION_VIDEO_SCRIPT.md`, based on `docs/PHASE5_DEMO_SCRIPT.md`, showing actual browser graph, real simulator, certificate counterexample, MCP tool trace, separate live LLM proof if approved, and manually reviewed internal record if user chooses to do so. One story, no fabricated screen/video.
- Capture clean screenshots from current UI and document real source for each. Remove tokens, personal IDs, private paths, and browser history from captures.
- Prepare `docs/SUBMISSION_TEXT.md` with an English competition description, concise bullet-free summary paragraph, exact Track 1 name, problem/solution, FalkorDB indispensability, technical stack, tested metrics with scope, limitations, AI-use disclosure. Provide copy-paste-friendly fields, not invented URLs.
- Prepare a final checklist with slots for actual **public GitHub URL, accessible demo-video URL, README, Cypher docs, local setup** and actual submission receipt/confirmation. Never invent these.
- Make a GitHub repo candidate and publish plan, but **do not push to a remote** or publish to YouTube/organizer. Do not create public services or expose local Redis/API to the Internet.

### Release gates / STOP
Stop and report if any of these is true:
1. Real graph-data changes occurred unexpectedly, seeding touched existing data, or fingerprint changed without an explained intended change.
2. A test uses fake data but is described as real backend/LLM evidence.
3. Secrets appear in release exports, logs or screenshots.
4. Browser needs LLM key in JavaScript or local storage to operate.
5. Independent clean-room install does not work.
6. Public submission, paid call, live human approval or external deployment is requested without explicit human instruction.

### Evidence required when reporting Phase 5A
- Exact changed files and why.
- Exact command transcript (success AND failures), with sensitive lines redacted.
- Before/after graph operational counts, hash, scenario ID, route availability.
- Host/Docker backend, Vitest and E2E results separated; skipped tests named.
- Fresh isolated install proof (not the existing graph).
- Production/release artifact inventory + secret-scan result (do not print secrets).
- Agent provider gate status: remote call **not executed**, pending authorization, OR verified real trace if later approved.
- Draft README, Cypher/evidence document, submission description/video script.
- Clear human decisions: license, provider/cost, any operator approval, publication and submission.
- Final status: **STOP for review; no public/paid action.**
