# Phase 4 acceptance: one coherent, truthful 3-minute live demo

Target: FalkorDB Graph Hacks 2026, Track 1.
Use reference synthetic scenario **only as the initial prefilled UI state**:
- Supplier S-04
- As of 2026-10-15
- Outage 2026-10-16 to 2026-10-24 (exclusive)
- Mitigation enabled; cost_first policy where supported.

## 00:00–00:25 — Establish context
Open overview. Show backend ready, operational graph counts from real HTTP and selected synthetic reference scenario. Mention "synthetic decision intelligence demo".

## 00:25–00:55 — One failure, many dependencies
Submit supplier outage scenario. Highlight dependency chain S-04 → P-22 ← PR-05 ← O-101 from actual path endpoints. Distinguish "connected order" from "order forecast to be late"; O-101 is covered by inventory in the verified reference run.

## 00:55–01:35 — Explain three states
Open Baseline → Disruption → Mitigation view. Reference verified seed should compute **19 → 18 → 20** on-time orders; newly at risk O-105/O-106, both restored by suggested alternatives at **1364.00 synthetic cost units**. UI must dynamically read real response; don't hardcode. Explain that fixing an existing baseline shortfall can make mitigation outperform baseline.

## 01:35–02:05 — Prove constraints
Show why S-09 is valid for P-22 and S-10 lacks required C-02 for P-22, yet S-10 is eligible for P-12 with C-01 on the evaluated arrival. Select actual edge and source reference. The proof lies in per-part, time-sensitive constraints.

## 02:05–02:30 — Real MCP, honest agent status
Execute guided walkthrough. UI displays 0 LLM calls and actual MCP tool order and sources. If an explicitly authorized real LLM provider is later tested, record a separate alternate demo clip proving real provider calls; otherwise never call guided mode autonomous AI.

## 02:30–03:00 — Human boundary and durable memory
Open authoritative decision preview and show its fingerprint/revision, cost, schedule and explanation. If an actual human operator has configured a secret and approved the local internal plan during the recording, open the Decision Ledger to show it persisted; otherwise show the previously verified **isolated-test evidence** with a clear test label and do not present it as a live operator action. For the live approval path, reveal no token in screen recording.

## Live acceptance gates
- Docker Compose still runs original FalkorDB and backend without reseeding or clearing volumes.
- Frontend calls real HTTP endpoints. Browser network and console show no uncaught errors.
- Graph node and edge properties/citations come from stored graph, not built-in JSON fixtures.
- Wrong date/unknown supplier/DB outage produce meaningful safe UI states. No old results labeled current.
- MCP guided mode is genuinely executed, with model_requests:0. Real remote provider remains pending unless separately authorized and observed.
- If approval enabled: one explicit human action creates one internal decision, replay does not duplicate, and after restart the Ledger retrieves it. No purchase, no supplier communication.
- Evidence must include validated chain and meaningful original source links/IDs. Path pagination is supported or clearly visible.
- Desktop 1440px, laptop 1024px and mobile 390px screenshots demonstrate legible, coherent layout. No emoji.
- All existing 166 backend tests remain green, with new frontend typecheck, build, lint, unit and real-browser E2E results recorded in a verifiable report.
- No API credentials in screenshots, transcripts, JS bundles, .env.example values, commits, GitHub or browser storage.

## Completion report should explicitly state
1. Components/screens implemented and actual API contracts used.
2. Links and commands to view the frontend locally.
3. Backend modifications (if any) and their reasons.
4. Real captured UI screenshots and result values.
5. Actual full test results; browsers tested; accessibility limitations.
6. Remaining risks, especially real-provider acceptance and local demo authorization.
7. No Phase 5, remote deployment or GitHub push.
