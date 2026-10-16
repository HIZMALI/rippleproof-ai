# Testing and reproducibility

The suite tests real graph behavior, deterministic planning, genuine MCP,
provider protocol failures and human approval boundaries. Controlled providers
and in-memory HTTP transport fixtures are explicitly simulations; no test calls
a remote LLM. All database integration tests use unique `test_rippleproof_*`
graphs. They fail if FalkorDB is unavailable and never substitute mock graph data.

## Backend

With Compose FalkorDB available:

```sh
docker compose --profile test build tests
docker compose --profile test run --rm -e RIPPLEPROOF_RETAIN_TEST_GRAPHS=1 tests
```

Host development requires Python 3.12+:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
$env:RIPPLEPROOF_RETAIN_TEST_GRAPHS='1'
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m pip check
```

On POSIX use `.venv/bin/python`. `-m 'not integration'` selects unit/transport
checks; `-m integration` selects actual FalkorDB tests. `FALKORDB_HOST` and
`FALKORDB_PORT` can point to a separate test server. The retention flag keeps
new test graphs; without it, fixtures remove only the graphs they created.
The empty-graph regression removes its own probe node. No test targets the live
`rippleproof` graph. Integration covers seed/migration idempotency, real paths,
capacity/time/expiry, source fingerprint changes, memory independence, replay,
conflict, concurrent confirmation and real MCP cancellation/timeout behavior.

## Frontend and browser

Node 22.12+ is required; Node 24 is verified. From `frontend/`:

```sh
npm ci
npx playwright install chromium
npm test
npm run typecheck
npm run lint
npm run format:check
npm run build
npm run test:e2e
```

Browser tests require the selected production stack plus free 18001/18081 for
their separate test backend/Vite harness. The harness creates its own graph and
credentials. Approval tests write only isolated synthetic records. No credentials
enter public captures; trace/HAR/video recording is disabled. Generated captures
go to ignored `.local/verification/`, with optional `EVIDENCE_DIRECTORY` override.

The restart regression briefly stops/starts the **selected Compose backend**.
For a populated operator installation, use a separate stack: set
`COMPOSE_PROJECT_NAME`, `API_PORT`, `WEB_PORT`, `FALKORDB_PORT`, `FALKORDB_GRAPH`
and `WEB_ORIGIN` to that stack before the browser command. Keep
`FALKORDB_HOST=127.0.0.1` for the host harness. All port values must match the
isolated stack. This preserves the live backend and operational graph.

## Source-only clean installation

From the repository root after installing dev dependencies:

```powershell
.venv\Scripts\python scripts/verify_clean_install.py
```

This opt-in script exports source into a new ignored directory, creates a unique
Compose project/graph/volume/ports, checks the graph is empty, then explicitly
seeds **only that new graph**. It verifies additive migration idempotency,
19/18/20 coverage, 1,364.00 cost, genuine MCP, restart/recreation persistence,
isolated DB outage/error recovery and a real browser walkthrough. Its stack and
evidence are retained under `.local/cleanrooms/`; no volume removal is performed.
The app uses only exported source and Docker; local dev dependencies are test
infrastructure. Images are digest-pinned and npm packages have lock integrity;
pip versions are pinned without artifact hash locks. Registry availability and
new-machine platform support are external prerequisites.

## Executed verification

Executed on **17 October 2026**, using the cleaned source and a new isolated
FalkorDB/Compose installation. No remote model call or live approval was made.

| Check | Actual result |
| --- | --- |
| Complete host backend suite | **209 passed**, 66.99s; includes 79 real-FalkorDB integration tests |
| Complete Docker backend suite | **209 passed**, 59.37s; same real integration scope |
| Frontend component suite | **51 passed**, four files, 22.54s |
| Chromium browser suite | **17 passed**, 157.19s; no failures, skips or retries |
| TypeScript, ESLint, Prettier, production build | PASS |
| Ruff lint/format and Python dependency validation | PASS |
| Source-only isolated Docker installation | PASS: empty graph, explicit seed, idempotent receipts, MCP, persistence, outage recovery and browser walkthrough |
| Offline provider contract / metadata | PASS with mocked transport; zero remote requests/network attempts |
| Source, legal and link audit | Zero secret matches or broken project-owned links; 269 upstream notice files byte-identical |

Browser tests ran against the isolated Compose stack, including its backend
restart; the original live graph and services were preserved. No test case or
assertion was removed. The export safety test adds screenshot-byte/link checks.
Detailed reports/captures remain in Git history and preserved local evidence;
they are not runtime inputs. One original pywin32 notice has an upstream relative
link affected by the flattened notice layout; the retained license texts are
correctly indexed in [third-party notices](../THIRD_PARTY_NOTICES.md). The notice
itself is unchanged.

Two authentic application screenshots are retained for reviewers in
[`images/`](images/). [API reference](REFERENCE_API.md), [security](SECURITY.md).
