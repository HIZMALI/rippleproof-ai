# RippleProof AI

An explainable supply-chain disruption agent for **Graph Hacks 2026, Track 1:
Agents That Act on Connected Data**. Team MORVE; one human participant.

When a supplier stops shipping, dependency lists cannot tell a planner which
orders still have enough material. RippleProof traverses FalkorDB, allocates
shared stock and receipts once, checks suppliers on arrival dates, and compares
explainable recovery plans. An optional bounded agent selects real MCP tools;
a human alone can authorize an internal decision record.

**Local release candidate; publication pending.** No API key is needed to explore.
Guided MCP is a deterministic walkthrough with zero remote LLM calls.
The bounded real-provider agent and redacted telemetry are implemented;
**real remote LLM acceptance has not been performed**. See
[executed Phase 5B-1 verification](docs/PHASE5B1_VERIFICATION.md),
[release gates](docs/PHASE5_RELEASE_GATES.md) and the
[publication checklist](docs/PUBLICATION_CHECKLIST.md).

Prepared for the owner's intended repository `hizmali/rippleproof-ai`.
Copyright © 2026 Mert Hızmalı. All rights reserved. See [RIGHTS.md](RIGHTS.md).
Public visibility, repository creation, commits, pushing, video upload and
competition submission still require separate authorization. Older phase reports
record the state at execution time; current rights and release gates are here.

## Run in three steps

Prerequisites: Docker Desktop (Linux containers) or Docker Engine with Compose v2.
Run at the repository root. These commands work in PowerShell and POSIX shells.

1. Start the production frontend, API and graph:

   ```sh
   docker compose up --build -d --wait
   ```

2. **Fresh empty demo graph only:** create the synthetic base and add receipts:

   ```sh
   docker compose exec backend python -m rippleproof.seed
   docker compose exec backend python -m rippleproof.migrate
   ```

   **Existing Phase 2/3/4 graph:** skip both commands. Starting services needs no
   reseed. The base seed restores fixture properties; never use it to upgrade an
   edited live graph. The additive migration is explicit, preserves existing
   properties, and is needed only when upgrading a Phase 1 graph.

3. Open the local [workspace](http://127.0.0.1:18080/#/overview), then Scenario
   Workbench. Click **Run scenario**. API docs: local
   [OpenAPI explorer](http://127.0.0.1:18000/docs).

These localhost links work only while your containers run. No public deployment
is provided. Default host ports: frontend 18080, API 18000, database 6379, all
bound to 127.0.0.1. Change `WEB_PORT`, `API_PORT`, or `FALKORDB_PORT` if occupied.
Optional configuration without replacing an existing file:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

```sh
test -e .env || cp .env.example .env
```

Container images are pinned by verified manifest digest, including the existing
tested FalkorDB image. Dependencies use pinned Python requirements and `npm ci`.
The `graph-data` named volume persists at `/var/lib/falkordb/data` with AOF enabled.
Restarting or recreating containers preserves it. Never remove it to troubleshoot
a populated installation; inspect `docker compose ps` and
`docker compose logs backend falkordb`. New installs are not seeded automatically.

## A short working demo

Use default as-of 2026-10-15 and S-04 outage [2026-10-16, 2026-10-24).
The synthetic graph has 145 operational nodes and 291 relationships, including
82 receipts. Results are calculated from the graph, not preloaded UI fixtures.

| Observation | Reference scenario result |
| --- | --- |
| Orders materially covered by deadline | Baseline 19 → disrupted 18 → mitigated 20 |
| Newly at-risk orders / restored by mitigation | O-105 and O-106 |
| Gross additional synthetic procurement cost | 1,364.00 synthetic units |
| Evidence path | S-04 → P-22 ← PR-05 ← O-101 |
| Part-specific certificate counterexample | S-10 lacks C-02 for P-22; can qualify for P-12 |

Inspect P-22 supplier and certificate evidence, then compare P-12. Open
**Guided MCP tools** and explicitly run guided tools: genuine SDK stdio calls
and real FalkorDB, **zero model requests**. Its fixed sequence is labeled a
deterministic walkthrough, usable without a key.

A separate **Run real agent** control remains disabled unless backend capability
permits it. Capability reads make no provider calls and return no credentials.
An enabled control also requires explicit run intent and fresh health. Controlled
tests are labeled **model simulator, not remote LLM**. No external LLM run has
been verified; paid testing is declined for now. Read [the agent gate](docs/AGENT_DEMO_GATE.md) before
configuring a provider. Key presence and settings do not authorize spending.
Resource bounds are enforced; this demo does not enforce a currency budget.

**Review internal plan** recalculates a full read-only preview. Approval is
optional, uses a separate server secret, explicit human confirmation and an
idempotency key, and is restricted to trusted localhost in the UI. No secret is
bundled or stored in browser storage. The default ledger is empty. Tests approve
only isolated graphs; no live approval has been performed. An internal record
places no order, reserves no stock and contacts no vendor.

## Why a graph is essential

FalkorDB is the sole canonical store for suppliers, BOMs, orders, inventory,
shipments, certificates and Decision/Evidence memory. Fixed parameterized Cypher
returns actual multi-hop paths and coherent snapshots. Deterministic Python
calculates demand, once-only allocation, dispatch capacity, lead time, expiry
checks and Decimal costs. The agent selects six constrained read-only MCP tools.
It cannot execute unrestricted Cypher, approve purchases, or supply authoritative
quantities or prices. There is no parallel SQL/JSON knowledge database or
graph-down fixture fallback.

React/TypeScript, Vite, TanStack Query, Zod and Cytoscape.js provide the responsive
interface. Unprivileged Nginx proxies same-origin requests to FastAPI, Pydantic
and the official FalkorDB client. API validators come from the running OpenAPI.

This is the actual `IMPACT_PATHS` template from
[queries.py](rippleproof/queries.py); user values are passed as parameters:

```cypher
MATCH evidence = (supplier:Supplier {id: $supplier_id})
  -[:SUPPLIES {is_primary: true}]->(part:Part)
  <-[:USES]-(product:Product)<-[:CONTAINS]-(purchase_order:Order)
WHERE purchase_order.status = $order_status
RETURN evidence
ORDER BY purchase_order.id, part.id, product.id
```

The read-only endpoint below runs this reviewed query with `supplier_id=S-04`
and `order_status=OPEN`, returning real connected evidence paths:

```sh
curl "http://127.0.0.1:18000/api/impact-paths?supplier_id=S-04"
```

Use `curl.exe` in Windows PowerShell if `curl` is an alias. A dependency path
alone does not establish lateness; the scenario engine checks quantities and dates.

- [Architecture](docs/ARCHITECTURE.md), [graph schema](docs/GRAPH_MODEL.md),
  [actual Cypher and evidence](docs/CYPHER_AND_EVIDENCE.md)
- [Detailed API/reference commands](docs/REFERENCE_API.md),
  [Phase 4 walkthrough](docs/DEMO_PHASE4.md)
- [Recording plan](docs/SUBMISSION_VIDEO_SCRIPT.md),
  [submission text](docs/SUBMISSION_TEXT.md),
  [publication checklist](docs/PUBLICATION_CHECKLIST.md)

## Verify and develop

No host Python/Node is required to run the application. For development, use
Python 3.12+ and Node 22.12+ (Node 24 verified). Exact test scopes and outcomes
are in [Phase 5B-1 verification](docs/PHASE5B1_VERIFICATION.md): 209 backend
tests (79 real-FalkorDB integration), 51 component tests and 17 browser tests.
Those are recorded executed results, not a claim that every later documentation
change reran the full suite. Isolated clean-install evidence and its exact tested
archive are documented in [Phase 5A verification](docs/PHASE5A_VERIFICATION.md).

```sh
docker compose --profile test build tests
docker compose --profile test run --rm tests
```

Integration tests query the real server using unique graphs, removing only graphs
they created. They fail if FalkorDB is unavailable; they do not silently skip.
Host workflow:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m pip check
```

On macOS/Linux use `.venv/bin/python` instead. Host integration tests default to
localhost:6379. Frontend workflow:

```sh
cd frontend
npm ci
npx playwright install chromium
npm test
npm run typecheck
npm run lint
npm run format:check
npm run build
npm run test:e2e
```

Browser tests require production services on default ports plus free 18001/18081
for their isolated backend/Vite harness. They approve only isolated graphs and
briefly stop/start the production **backend**, restoring it in a finally block;
the live graph is never reseeded. Avoid running during an operator session.
Set process environment `EVIDENCE_DIRECTORY=../docs/verification/phase5a/regression`
to preserve historical Phase 4 recordings. Traces/HAR/video are disabled to avoid
capturing approval credentials.

`npm run dev -- --port 18081` starts an optional development server.
`npm run contracts` regenerates validators from the running API. To verify a
separate source-only installation, from repository root:

```powershell
.venv\Scripts\python scripts/verify_clean_install.py
```

This opt-in tool creates a new export, Compose project, volume, graph and ports.
It checks empty state, explicitly seeds only that new graph, tests persistence
and isolated graph outage, then runs a read-only browser walkthrough. It leaves
the stack/data intact. The browser driver uses development dependencies as test
infrastructure; the installed app uses only exported source and Docker, with no
private fixtures or existing volume.

## Limits and release state

Coverage means material availability by deadline, not guaranteed production or
delivery. The bounded greedy planner is not globally optimal. Existing planned
transit intervals are authoritative; this is not a transport scheduler. All
entities and prices are synthetic. There is no enterprise API, real procurement
or production authentication. The one-worker approval lock does not exclude
external graph writers between read and write; serialize edits during approvals.
This localhost demo is not hardened for public hosting. Dataset/tool-payload
limits produce explicit errors.

Publish only an explicitly reviewed source candidate with its external per-file
manifest and ZIP SHA-256. The original workstation archive is **not publishable**.
`python scripts/release_candidate.py --phase phase5b1` is a development export
helper; a newly generated export is a different candidate requiring fresh review.
It excludes local state/secrets/dependencies/backups/Git metadata and scans
selected files and reachable history. It never commits, publishes or pushes.
Do not replace the reviewed publication tree with an unreviewed working copy.

A genuine local three-minute, silent English-captioned demonstration has been
produced and decoded/playback-checked. It shows real local application results,
deterministic Guided MCP and a read-only plan preview. It does not show a remote
LLM run or live approval. Video hosting/upload and a public URL remain pending;
private recordings and production evidence are excluded from this source tree.

Project rights remain **All Rights Reserved**, per the owner's explicit decision.
The declared personal copyright holder is Mert Hızmalı; no project open-source
LICENSE is granted. See [RIGHTS.md](RIGHTS.md). Preserve [third-party notices](THIRD_PARTY_NOTICES.md):
FalkorDB server is SSPLv1; the Python client is MIT. Container layers are not
redistributed in this source candidate. Commercial hosting/distribution requires
separate license review.

## AI-assistance disclosure

OpenAI Codex assisted with Phases 1–5B-1 implementation, synthetic fixtures, tests,
documentation and local verification during the event on 2026-10-15/16, followed
by local demo production and publication preparation. No Git history has been
backdated or invented.
The human participant chose scope, directed phased work, and reported reviewing
and approving prior phases. They remain responsible for reviewing, understanding
and explaining the final code and making the competition disclosure. This does
not claim an independent human code audit. Only recorded executed tests support
test claims. Remote LLM acceptance remains unexecuted; guided and controlled
evidence are disclosed separately.

This publication candidate stops for final review. Public repository/video URLs,
remote-provider acceptance, deployment and organizer submission are not completed.
