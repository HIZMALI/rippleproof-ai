# Phase 1 verification record — 2026-10-15

> Historical initial attempt. Its Docker blocker was resolved in the completed
> [current verification record](PHASE1_VERIFICATION.md). Results below are kept
> as originally recorded, including failed and unexecuted checks.

Workspace: `<repository>`.
Execution used PowerShell on Windows. Scenario dates are fixed at 2026-10-15.

**Status: implementation prepared; container acceptance BLOCKED.** Do not mark
Phase 1 complete until the real-server checks below pass. No Phase 2 work began.

## Environment actually observed

| Tool | Observed result |
| --- | --- |
| Docker CLI | 29.4.2; `desktop-linux` context |
| Docker Compose | v5.1.3 |
| Python | 3.14.0 |
| pip | 25.2 via `python -m pip`; standalone `pip` absent |
| Python launcher | `py` absent |
| Git | 2.51.0.windows.2; initialized locally on `main`; no remote or commit |
| WSL | Version 2 Docker Desktop distribution, stopped |

Docker initially had no running engine. `docker desktop start` did not restore
it and was interrupted. `docker desktop status` reported it could not retrieve
status. Read-only inspection found this Docker backend error:

```text
initializing Inference manager
listening on unix://<local-path>
remove <local-path>
The file cannot be accessed by the system.
```

No Docker system files were deleted/reset, no WSL distributions were removed,
and no remote account or deployment was changed. Docker Desktop recovery is a
required human action. After restarting/repairing Docker Desktop, `docker version`
must show a working **Server** section before resuming acceptance tests.

Windows excluded TCP ports 7919–8018, which includes 8000. A direct Uvicorn bind
to 8000 failed with WinError 10013. Binding to 18000 succeeded. The published
Compose API port default and `.env.example` were updated to 18000; no Windows
port reservations were changed.

## Actual results

| Check | Result |
| --- | --- |
| Dependency installation from final requirements | Succeeded in workspace `.venv` |
| `pip check` | No broken requirements found |
| CPython 3.12/Linux wheel resolution dry run | Succeeded; this was **not** container installation/execution |
| Local non-container tests | **36 passed, 11 deselected**, final recorded run 1.23s |
| Ruff lint | All checks passed |
| Ruff format check | 19 files already formatted |
| Python syntax check | 19 source/test files parsed with Python 3.12 grammar; not a Python 3.12 runtime test |
| Compose config validation | Exit 0 |
| `docker compose up --build -d` | Exit 1: missing `dockerDesktopLinuxEngine` pipe; no container build/start verified |
| Integration test attempt | Stopped at first fixture: **1 error, 36 deselected**, FalkorDB unavailable; no integration test passed |
| Host Uvicorn on 18000 | Started; HTTP requests confirmed expected 503 and 422 behavior; process stopped afterward |
| Graph seed execution/idempotency in FalkorDB | Not executed; prerequisite blocked |
| Successful graph-backed HTTP responses | Not observed; prerequisite blocked |
| GitHub push / deployment | Not performed |

The initial local run passed with an upstream TestClient deprecation warning
about `httpx`. The final dev lock uses the supported `httpx2` transport and the
repeated local tests passed without warnings. Early lint findings were fixed.

The deterministic generator was executed and its input counts were observed:

```text
Supplier=12 Part=16 Product=8 Order=24 Certificate=3
SUPPLIES=24 USES=24 CONTAINS=29 REQUIRES_CERT=17 HOLDS_CERT=33
```

These are synthetic input counts, not a substitute for live graph counts.

## Exact setup, diagnostic and verification commands executed

The following commands were executed, including unsuccessful attempts. Repeated
checks are shown once unless their repetition explains the final state. File
reads and workspace edits used Get-Content/rg and the patch tool; no existing
requirements document was edited.

```powershell
Get-Content -Raw AGENTS.md
Get-Content -Raw docs/PRODUCT_SPEC.md
Get-Content -Raw docs/GRAPH_MODEL.md
Get-Content -Raw tasks/01-foundation.md
Get-Content -Raw START_HERE.md; Get-Content -Raw docs/DELIVERY_AND_DEMO.md
git status --short --branch
rg --files --hidden -g '! .git' -g '!.git/**'
docker version
docker compose version
python --version; py --list-paths; pip --version
python -m pip --version; python -c "import sys; print(sys.executable)"; git --version
Get-ChildItem -Force | Select-Object Mode,Name; Get-Command docker,python,py,uv,git -ErrorAction SilentlyContinue | Select-Object Name,Source
docker desktop start
python -m venv .venv
wsl --status; wsl --list --verbose
Get-Process -Name '*docker*','*wsl*' -ErrorAction SilentlyContinue | Select-Object ProcessName,Id; Get-ChildItem -LiteralPath "$env:LOCALAPPDATA\Docker\log\host" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 5 Name,LastWriteTime
docker desktop status; Get-Service -Name '*docker*' | Format-Table Name,Status; Get-Item -LiteralPath 'C:\Program Files\Docker\Docker\Docker Desktop.exe' -ErrorAction SilentlyContinue | Select-Object FullName
Get-ChildItem -LiteralPath "$env:LOCALAPPDATA\Docker" -Force -ErrorAction SilentlyContinue | Select-Object Name,LastWriteTime; Get-CimInstance Win32_Process -Filter "Name='docker-desktop.exe'" | Select-Object ExecutablePath,CommandLine
Get-Content -Raw -LiteralPath "$env:LOCALAPPDATA\Docker\backend.error.json"; Get-ChildItem -LiteralPath "$env:LOCALAPPDATA\Docker\log" -Force | Select-Object Name; Get-Service -Name '*docker*' | Format-Table Name,Status; Get-Item -LiteralPath 'C:\Program Files\Docker\Docker\Docker Desktop.exe' -ErrorAction SilentlyContinue | Select-Object FullName
.venv\Scripts\python -m pip index versions falkordb; .venv\Scripts\python -m pip index versions fastapi; .venv\Scripts\python -m pip index versions pytest
.venv\Scripts\python -m pip install falkordb==1.8.0 fastapi==0.143.2 uvicorn==0.49.0 pydantic-settings==2.14.0 pytest==9.1.1 httpx==0.28.1 ruff==0.15.17
.venv\Scripts\python -m ruff check . --fix; .venv\Scripts\python -m ruff format .
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
docker compose config --quiet
.venv\Scripts\python -m pip check
.venv\Scripts\python -m pytest -q -m 'not integration'
docker compose up --build -d
.venv\Scripts\python -m pytest -q -m integration -x
.venv\Scripts\python -m pip index versions httpx2
git init -b main
.venv\Scripts\python -m uvicorn rippleproof.app:app --host 127.0.0.1 --port 8000
netsh interface ipv4 show excludedportrange protocol=tcp
.venv\Scripts\python -m pip install httpx2==2.13.1
.venv\Scripts\python -m uvicorn rippleproof.app:app --host 127.0.0.1 --port 18000
.venv\Scripts\python -c "from rippleproof.seed_data import build_dataset; d=build_dataset(); print({k:len(v) for k,v in d.nodes.items()}); print({k:len(v) for k,v in d.relationships.items()})"
.venv\Scripts\python -m pip uninstall -y httpx httpcore certifi; .venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pip install --dry-run --ignore-installed --python-version 3.12 --only-binary=:all: --platform manylinux2014_x86_64 --implementation cp --abi cp312 -r requirements-dev.txt
git status --short --branch; git remote -v; rg --files -g '!.venv/**' -g '!.git/**'
.venv\Scripts\python -c "import ast; from pathlib import Path; files=list(Path('rippleproof').rglob('*.py'))+list(Path('tests').rglob('*.py')); [ast.parse(p.read_text(encoding='utf-8'), filename=str(p), feature_version=(3,12)) for p in files]; print(f'{len(files)} Python files parsed with Python 3.12 grammar')"; git status --short --branch; git diff --check
```

The local live HTTP probe was executed with PowerShell 7's
`-SkipHttpErrorCheck` (the README's happy-path commands also work in Windows
PowerShell 5). Exact probe:

```powershell
$paths = @('/health', '/api/graph/summary', '/api/impact-paths?supplier_id=S-04', '/api/alternatives?part_id=P-22&as_of=2026-10-15', '/api/impact-paths?supplier_id=invalid'); foreach ($path in $paths) { $response = Invoke-WebRequest -Uri ('http://127.0.0.1:18000' + $path) -SkipHttpErrorCheck; [pscustomobject]@{ Path = $path; Status = [int]$response.StatusCode; Body = $response.Content } | ConvertTo-Json -Compress }
```

Observed health body (503):

```json
{"status":"unavailable","database":"unavailable","graph":"rippleproof","graph_exists":null}
```

Observed summary, impact and alternatives body (each 503):

```json
{"error":{"code":"database_unavailable","message":"FalkorDB is unavailable. Try again later."}}
```

Observed invalid supplier body (422):

```json
{"detail":[{"type":"string_pattern_mismatch","loc":["query","supplier_id"],"msg":"String should match pattern '^S-[0-9]{2,5}$'","input":"invalid","ctx":{"pattern":"^S-[0-9]{2,5}$"}}]}
```

## Remaining Phase 1 acceptance commands — NOT executed successfully

Once Docker Desktop has a working Linux engine, run the following in this
workspace. These are follow-up instructions, not evidence of completed tests.

```powershell
docker compose up --build -d
docker compose ps
docker compose exec backend python -m rippleproof.seed
docker compose exec backend python -m rippleproof.seed
docker compose --profile test build tests
docker compose --profile test run --rm tests
```

Then capture real 200 responses for the four documented endpoints, including
O-101/P-22/PR-05 evidence, S-09 validity, S-10's missing C-02, S-12's empty
dependencies, and unchanged counts on second seed. Inspect logs and fix any
live query/container issues found. Container persistence is configured but has
not been restart-tested. Only after Phase 1 gates pass should the human review
Phase 1 and decide whether to authorize Phase 2.


