# External Phase 4 review — 2026-10-16

## Reviewed materials
The user-supplied `rippleproof-ai(1).zip` was inspected locally. Phase 4 report, demo instructions, React/TypeScript source, FastAPI source, Docker Compose and Nginx configuration, manifest, E2E test scripts and actual saved Chromium screenshots were inspected. This reviewer cannot reach the user's 127.0.0.1 server, and did not execute the full test suite in the user's environment. Treat Codex's 168 backend/43 frontend/15 browser results as reported results supported by artifact files, **not independently rerun here**.

## Findings
- Screenshots show cohesive dark enterprise UI and a responsive narrow-screen workbench. The workbench has an interactive evidence area, constraints panel, readable form, and separate guided MCP trace. Native review modal lists actual proposed quantities, arrivals and certification references.
- Frontend `api/client.ts` uses contract validation, request cancellation/timeouts and safe error copy. Guided mode explicitly demands `model_requests === 0` and `guided_walkthrough`; current visible UI does not present guided workflow as an autonomous LLM.
- `compose.yaml` binds frontend 18080, API 18000 and FalkorDB 6379 to localhost. This is appropriate for a local demo but is **not an authenticated public deployment**. Nginx proxies API requests; publishing current local stack directly is not recommended.
- Uploaded ZIP size is ~105 MB compressed and includes `.git`, `.venv`, `.local`, `frontend/node_modules` and caches. No root `.env` was present in that upload, but a clean release artifact is essential. Root `LICENSE` was not present. Verify secrets in all material that might be uploaded.
- The organizer requires a real agent whose graph is load-bearing, plus a public repository, graph model/Cypher, video, installation/deployment proof and coding-assistance disclosure. No remote LLM-provider acceptance has been performed yet; this is the most important Track 1 demonstration gap.

## Clear next step
Phase 5A: non-billable release hardening, isolated clean-room install, optional real-agent UI wiring **without remote calls**, repo export and demo docs. Stop for explicit user decisions on API budget/provider, license and external publication. Then Phase 5B: authorized provider smoke, authentic video, clean GitHub publishing and official submission.

## Official sources
https://www.wemakedevs.org/hackathons/falkordb/rules
https://www.wemakedevs.org/hackathons/falkordb
