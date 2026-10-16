# Executed Phase 5A verification/build commands

Execution: 15 October UTC / 16 October 2026 Europe/Istanbul. Root working directory unless a frontend context is stated. This records verification/build commands, not every exploratory file read or editor patch. Polling continued asynchronous sessions; final test outcomes are in PHASE5A_VERIFICATION.md. Secrets and raw private logs are excluded.

## Baseline, backup and image pins

```powershell
git branch --show-current; git status --short; git log --all --format='%h %aI %cI' -5; docker compose ps; docker version --format '{{.Client.Version}} / {{.Server.Version}}'; docker image inspect falkordb/falkordb:latest --format '{{.Id}} {{json .RepoDigests}}'; docker image inspect python:3.12-slim node:24-alpine nginxinc/nginx-unprivileged:1.29-alpine --format '{{.RepoTags}} {{json .RepoDigests}}'
```

Initial command result: 1.

```powershell
@'
import json,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from rippleproof.config import Settings
from rippleproof.repository import GraphRepository
from rippleproof.simulation.snapshot import normalize
now=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
folder=Path('.local')/('phase5a_'+now);folder.mkdir(exist_ok=False)
repo=GraphRepository(Settings());snap=normalize(*repo.operational_facts())
(folder/'operational-backup.json').write_text(snap.model_dump_json(),encoding='utf-8')
def get(path):
 with urllib.request.urlopen('http://127.0.0.1:18000'+path,timeout=15) as r:return json.load(r)
scenario={'supplier_id':'S-04','as_of':'2026-10-15','outage_start':'2026-10-16','outage_end_exclusive':'2026-10-24','include_mitigation':True}
with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18000/api/scenarios/simulate',data=json.dumps(scenario).encode(),headers={'Content-Type':'application/json'}),timeout=30) as r:result=json.load(r)
with urllib.request.urlopen('http://127.0.0.1:18080/',timeout=15) as r:frontend=r.status
api=get('/openapi.json')
baseline={'utc':now,'health':get('/health'),'summary':get('/api/graph/summary'),'fingerprint':snap.fingerprint,'scenario_id':result['scenario_id'],'coverage':[len(result[k]['on_time_orders']) for k in ['baseline','disrupted','mitigated']],'cost':result['estimated_additional_procurement_cost'],'frontend_http':frontend,'routes':[{ 'path':p,'methods':sorted(v)} for p,v in api['paths'].items()]}
(folder/'baseline.json').write_text(json.dumps(baseline,indent=2),encoding='utf-8')
(folder/'scenario-before.json').write_text(json.dumps(result),encoding='utf-8')
Path('.local/phase5a-current.json').write_text(json.dumps({'directory':str(folder)}),encoding='utf-8')
print(json.dumps(baseline,indent=2));print('Private baseline directory:',folder)
'@ | .venv\Scripts\python -
```

Initial command result: 0.

```powershell
docker compose exec -T falkordb redis-cli BGSAVE
```

Initial command result: 0.

```powershell
@'
import json,subprocess,hashlib
from pathlib import Path
folder=Path(json.loads(Path('.local/phase5a-current.json').read_text(encoding='utf-8'))['directory'])
info=subprocess.check_output(['docker','compose','exec','-T','falkordb','redis-cli','INFO','persistence'],text=True)
assert 'rdb_bgsave_in_progress:0' in info and 'rdb_last_bgsave_status:ok' in info
backup=folder/'live-all-graphs.rdb';assert not backup.exists()
subprocess.run(['docker','compose','cp','falkordb:/var/lib/falkordb/data/dump.rdb',str(backup)],check=True,capture_output=True)
digest=hashlib.sha256(backup.read_bytes()).hexdigest();(folder/'backup-sha256.txt').write_text(digest,encoding='utf-8')
print('Exclusive new RDB backup complete:',backup.stat().st_size,'bytes; sha256',digest)
'@ | .venv\Scripts\python -
```

Initial command result: 0.

```powershell
.venv\Scripts\python -m pytest -q
```

Initial command result: asynchronous; completion recorded in verification report.

```powershell
docker compose --profile test run --rm tests
```

Initial command result: asynchronous; completion recorded in verification report.

```powershell
npm test
```

Initial command result: 0.

```powershell
npm run test:e2e
```

Initial command result: asynchronous; completion recorded in verification report.

```powershell
docker buildx imagetools inspect falkordb/falkordb@sha256:b0bdcac2cbaff989e77cb0610439b7a9289e86de033ccbbd4368b66fb680ae7a
```

Initial command result: 0.

```powershell
docker buildx imagetools inspect python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
```

Initial command result: 0.

```powershell
docker buildx imagetools inspect node:24-alpine@sha256:44fce696f38ba8c987c4db89954051000bbd05ffd8d8659ba15ed4a8602e937f
```

Initial command result: 0.

```powershell
docker buildx imagetools inspect nginxinc/nginx-unprivileged:1.29-alpine@sha256:0c79d56aee561a1d81c63f00eee5fb5fe29279560cdc55e91425133104c7fbe6
```

Initial command result: 0.

```powershell
docker compose up -d --no-deps --build backend
```

Initial command result: 0.

## Expanded implementation and final regression commands

These are exact commands executed, with the indicated working directory. Some
were repeated after fixes; repetitions and failed outcomes are recorded below.
The private `.local` helper compares the captured typed snapshot, backup hash,
full scenario JSON and actual HTTP responses; it never approves or seeds.

Root:

```powershell
.venv\Scripts\python -m pytest -q tests/test_agent_capabilities.py
.venv\Scripts\python -m pytest -q tests/test_release_candidate.py
.venv\Scripts\python -m pytest -q tests/test_validation.py tests/test_agent_capabilities.py
.venv\Scripts\python -m pytest -q tests/integration/test_mcp_agent.py::test_real_mcp_launches_from_an_unrelated_working_directory tests/test_release_candidate.py
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m pytest --collect-only -q -m integration | Select-Object -Last 2
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m ruff format scripts/verify_clean_install.py
.venv\Scripts\python -m pip check
.venv\Scripts\python scripts/third_party_notices.py
.venv\Scripts\python scripts/verify_clean_install.py
.venv\Scripts\python .local/phase5a_final.py
docker compose --profile test build tests
docker compose --profile test run --rm --no-deps tests
docker compose up -d --no-deps --build backend
docker compose up -d --no-deps --build frontend
docker compose exec -T backend python -m pip check
docker compose config --quiet
docker compose ps
git rev-list --all --count
git for-each-ref --format='%(refname) %(objecttype)'
```

Frontend working directory:

```powershell
npm run contracts
npx prettier --write e2e scripts/*.mjs
npx prettier --write scripts/capture-agent.mjs
npm run typecheck
npm run lint
npm run format:check
npx prettier --check scripts/*.mjs
npm test
npm run build
npm audit --audit-level=low
$env:EVIDENCE_DIRECTORY='../docs/verification/phase5a/regression'; npm run test:e2e
$env:EVIDENCE_DIRECTORY='../docs/verification/phase5a/visual'; node scripts/capture.mjs
node scripts/capture-agent.mjs
```

The first expanded host/Docker suites each returned 182 passed and one failed
OpenAPI-inventory assertion. After the path assertion and new MCP cwd regression,
full reruns returned 184 passed each. A combined PowerShell command later ran
successful Ruff/pip checks after the initial pytest failure; its shell exit code
alone did not establish that pytest passed. Test output was inspected separately.
The first expanded browser run returned 16 passed/one failed (MCP cwd import).
The complete rerun passed all 17. Standalone capture-driver selector/context
errors were repaired and the four scans rerun. No retries were hidden.

## Isolated install subprocess commands

The following exact argv arrays came from the **second** clean install's
executed subprocess log. Working directory: its newly extracted source root.
Environment was explicitly scrubbed, then supplied graph `clean_75262774c8ff`,
ports 11014/11015/11016, provider `disabled`, paid calls `false`. The first
installation independently executed the same lifecycle under its other unique
project/volume. No deletion/cleanup command was used.

```json
["docker", "compose", "-p", "phase5a_75262774c8ff", "up", "-d", "--build", "--wait", "--wait-timeout", "120"]
```

Exit: 0.

```json
["docker", "compose", "-p", "phase5a_75262774c8ff", "exec", "-T", "backend", "python", "-m", "rippleproof.seed"]
```

Exit: 0.

```json
["docker", "compose", "-p", "phase5a_75262774c8ff", "exec", "-T", "backend", "python", "-m", "rippleproof.migrate"]
```

Exit: 0.

```json
["docker", "compose", "-p", "phase5a_75262774c8ff", "exec", "-T", "backend", "python", "-m", "rippleproof.migrate"]
```

Exit: 0.

```json
["docker", "compose", "-p", "phase5a_75262774c8ff", "exec", "-T", "backend", "python", "-m", "rippleproof.mcp_smoke"]
```

Exit: 0.

```json
["docker", "compose", "-p", "phase5a_75262774c8ff", "restart"]
```

Exit: 0.

```json
["docker", "compose", "-p", "phase5a_75262774c8ff", "up", "-d", "--force-recreate", "--wait", "--wait-timeout", "120"]
```

Exit: 0.

```json
["docker", "compose", "-p", "phase5a_75262774c8ff", "stop", "--timeout", "3", "falkordb"]
```

Exit: 0.

```json
["docker", "compose", "-p", "phase5a_75262774c8ff", "start", "falkordb"]
```

Exit: 0.

```json
["node", "scripts/clean-demo.mjs", "http://127.0.0.1:11015", "<isolated-browser-evidence>"]
```

Exit: 0.

## Candidate and preservation audit

`python scripts/release_candidate.py` uses reviewed argv for `git rev-list --objects --all`, `git cat-file -t`, `git cat-file blob`, and `git rev-list --all --count`. It scans each selected file, each reachable blob and every ZIP member; records hashes and exclusions; makes no Git mutation. The final execution and runtime-source comparison are recorded in the external candidate manifest/companion. Private Python helpers restored only baseline-generated Phase 4 artifact files from the pre-work app snapshot, retaining replaced copies, and compared all 32 original hashes. No graph, volume or backup was restored/deleted.
