# Phase 1 verification record — 2026-10-15

**Status: COMPLETE — all Phase 1 acceptance gates passed.** Verification used
real FalkorDB, containerized FastAPI, and real HTTP requests. No Phase 2 work,
GitHub push, volume reset, or deletion of existing database contents occurred.

The previous blocked attempt is preserved in
[PHASE1_INITIAL_ATTEMPT.md](PHASE1_INITIAL_ATTEMPT.md). The Docker prerequisite
was restored before this continuation. The original failed attempt is not
counted as successful verification.

Workspace: `<repository>`.
Git remains on `main`, with no commits or configured remote. Scenario reference
date: **2026-10-15**. Docker's startup timestamps in the raw log are UTC.

## Observed environment and final services

| Component | Actual value |
| --- | --- |
| Docker client / server | 29.4.2 / 29.4.2 |
| Docker Desktop / context | 4.72.0 / desktop-linux |
| Docker Compose | v5.1.3 |
| Container Python | 3.12.15 |
| Host Python | 3.14.0 |
| FalkorDB / Redis | 4.22.1 (module 42201) / 8.10.2 |
| Official Python client | falkordb 1.8.0 |
| Backend | Healthy; 127.0.0.1:18000 -> container 8000 |
| FalkorDB | Healthy; 127.0.0.1:6379 -> container 6379 |

The required `falkordb/falkordb:latest` image resolved to:

```text
falkordb/falkordb@sha256:b0bdcac2cbaff989e77cb0610439b7a9289e86de033ccbbd4368b66fb680ae7a
```

The Python base resolved to
`python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1`.
Tags remain floating as configured; these are the actual images verified.

## Tests and quality results

| Executed check | Actual result |
| --- | --- |
| Dedicated real-server integration run after the fixture fix | **11 passed, 36 deselected in 1.01s** |
| Full Docker suite after the fix, Python 3.12.15 | **47 passed in 1.35s** |
| Full host suite after the fix, Python 3.14.0 | **47 passed in 3.15s** |
| Ruff lint | All checks passed |
| Ruff format check | 19 files already formatted |
| Runtime container dependency validation | No broken requirements found |
| Test container dependency validation | No broken requirements found |
| Host dependency validation | No broken requirements found |
| Docker Compose configuration validation | Exit 0 |
| Build/start and final forced container recreation | Exit 0; both services healthy |
| Real HTTP acceptance, errors, empty results and recovery | Passed |
| Restart/recreation persistence without reseeding | Passed; complete graph fingerprint identical |

The dedicated integration run executed every previously blocked case:

1. Seed idempotency and restoration of deliberately modified properties.
2. Readiness and absent graph, without creating it through reads.
3. Existing graph with zero nodes/relationships.
4. Three-hop traversal with independent verification of every evidence edge.
5. Existing supplier with no dependencies.
6. Nonexistent supplier.
7. Nonexistent part.
8. Alternative certificates, missing/expired certs and inclusive expiry boundary.
9. Another part and a part without alternative suppliers.
10. Repeatable reads that do not mutate graph contents.
11. Graph mutations changing the returned dependency and certificate answers.

Integration tests use the real Compose FalkorDB server and isolated
`test_rippleproof_*` graphs. They clean up only their own temporary test graphs;
the demo graph and existing volume are preserved. No graph client, repository,
or database was mocked. The separate transport failure test also uses an actual
refused TCP connection.

## Seed data and idempotency proof

Executed twice, sequentially:

```powershell
docker compose exec -T backend python -m rippleproof.seed
docker compose exec -T backend python -m rippleproof.seed
```

`-T` disables interactive TTY allocation for the documented seed command.

| Result from real FalkorDB | First run | Second run |
| --- | ---: | ---: |
| Nodes | 63 | 63 |
| Relationships | 127 | 127 |
| Supplier / Part / Product / Order / Certificate | 12 / 16 / 8 / 24 / 3 | 12 / 16 / 8 / 24 / 3 |
| SUPPLIES / USES / CONTAINS | 24 / 24 / 29 | 24 / 24 / 29 |
| REQUIRES_CERT / HOLDS_CERT | 17 / 33 | 17 / 33 |
| Decision / Evidence / later relationships | 0 | 0 |

The two complete seed JSON outputs were identical. Independent queries through
`redis-cli GRAPH.RO_QUERY` returned `[[63]]` and `[[127]]`. These are persisted
database counts, not generator-only assertions. The integration idempotency
test additionally verified that reseeding restores node and edge properties
without duplication.

## Real HTTP results

All requests used `http://127.0.0.1:18000`. The complete JSON responses before
and after final container recreation were compared and were identical.

| Request | Status | Observed result |
| --- | ---: | --- |
| `/health` | 200 | ready, database ready, graph exists |
| `/api/graph/summary` | 200 | 63 nodes, 127 relationships |
| `/api/impact-paths?supplier_id=S-04` | 200 | 20 paths, 11 distinct open orders, required acceptance chain present |
| `/api/alternatives?part_id=P-22&as_of=2026-10-15` | 200 | Four candidates with stored supply terms and certificate evidence |
| `/api/impact-paths?supplier_id=S-12` | 200 | Empty paths and order IDs |
| `/api/alternatives?part_id=P-01&as_of=2026-10-15` | 200 | Existing part, empty candidates |
| `/api/impact-paths?supplier_id=S-99` | 404 | entity_not_found |
| `/api/alternatives?part_id=P-99&as_of=2026-10-15` | 404 | entity_not_found |
| `/api/impact-paths?supplier_id=invalid` | 422 | Invalid supplier ID |
| `/api/alternatives?part_id=P-22&as_of=2026-02-30` | 422 | Invalid calendar date |
| `/docs`, `/openapi.json` | 200 | API documentation available |

Actual healthy response:

```json
{"status":"ready","database":"ready","graph":"rippleproof","graph_exists":true}
```

The acceptance path returned from the graph-backed HTTP endpoint is:

```text
Supplier S-04 -[SUPPLIES]-> Part P-22 <-[USES]- Product PR-05 <-[CONTAINS]- Order O-101
```

Stored relationship identities:

```text
SUPPLIES:S-04:P-22
USES:PR-05:P-22
CONTAINS:O-101:PR-05
```

For that path, actual order quantity was **8**, units per product **4**, and
path demand **32**. The deadline was 2026-10-18. P-22's stored stock was 80.
These are graph facts and deterministic multiplication, not a shortage or
late-delivery forecast. Runtime code contains no special-case scenario answers.

Observed P-22 alternatives at 2026-10-15:

| Supplier | Synthetic unit cost | C-01 | C-02 | certifications_valid |
| --- | ---: | --- | --- | --- |
| S-08 | 15.0 | valid through 2027-10-15 | valid through 2026-10-15 | true |
| S-09 | 14.5 | valid through 2027-10-15 | valid through 2027-10-15 | true |
| S-10 | 8.5 | valid through 2027-10-15 | missing; holding null | false |
| S-11 | 11.0 | valid through 2027-10-15 | expired 2026-10-14 | false |

S-10's missing-C-02 result includes the actual
`REQUIRES_CERT:P-22:C-02` requirement and no matching holding. S-09's checks
include its actual `HOLDS_CERT` edges. Certification validity is limited to the
modeled requirements; lead-time/capacity feasibility is not assessed.

### Controlled live database outage

Stopped only FalkorDB, while keeping FastAPI running:

```powershell
docker compose stop falkordb
```

The final strict HTTP probe returned **503 for all four** readiness/data routes.
Health returned `graph_exists: null`; graph routes returned:

```json
{"error":{"code":"database_unavailable","message":"FalkorDB is unavailable. Try again later."}}
```

After recovery, the normal responses returned again. No fixture fallback
appeared. An earlier outage probe was interrupted by a premature service
restart; PowerShell continued after transport errors. That probe was discarded.
The successful repeat used terminating errors and completed before recovery.
Both attempts are retained in the raw log.

## Defects found and fixed

### Named volume did not cover the actual database directory

The original Compose mount was `graph-data:/data`, with
`REDIS_ARGS=... --dir /data`. Inspection of this image's `run.sh` and
`CONFIG GET dir` showed that its entrypoint appended
`--dir /var/lib/falkordb/data`, overriding that argument. A simple restart kept
the container writable layer, so matching counts alone would have missed this.

Fixed Compose to mount the same existing named volume at
`/var/lib/falkordb/data` and removed the ineffective `--dir` argument.
This matches the [official repository setup](https://github.com/FalkorDB/FalkorDB#step-1).

Preservation procedure actually executed:

1. Gracefully stopped backend and FalkorDB so Redis flushed its files.
2. Copied the complete actual database directory to
   `.local/backups/falkordb-before-volume-fix-20261015` inside this workspace.
3. Copied those files into the previously unused named-volume root.
4. Compared all four database file SHA-256 checksums between backup and volume.
   Every file matched before recreating the service.
5. Recreated services using the corrected mount and verified the full graph
   fingerprint, HTTP responses, key count and graph list.

The backup is retained, excluded from Git and Docker build context through
`.local/`. No volume, existing graph or existing Redis key was reset/deleted.
Redis reported two keys before and after migration; `GRAPH.LIST` returned
`["rippleproof"]`.

### Empty test graph produced an invalid historical AOF delete

The old empty-graph test used `GRAPH.QUERY ... "RETURN 1"` to create a graph
without a mutating query. After its teardown, FalkorDB 4.22.1 logged
`Invalid graph operation on empty key` while replaying the corresponding
`graph.DELETE`. Tests passed but the startup log exposed this fixture defect.

Changed the test to create one temporary probe node through a real write and
then remove that node before asserting zero counts. Teardown now has a persisted
graph creation to replay. After backing up the old files, used Redis's standard
[`BGREWRITEAOF`](https://redis.io/docs/latest/commands/bgrewriteaof/) compaction
to replace historical test-command replay with the current state. Redis
reported `aof_last_bgrewrite_status:ok`, `aof_last_write_status:ok` and no rewrite
in progress. The original files remain in the workspace backup.

Reran the dedicated integration suite and both complete suites, then recreated
both services. The final startup log loaded all graph data and contained
**no CRITICAL or invalid-graph-operation replay messages**. An intermediate
format check required formatting the edited test; the final Ruff checks passed.

## Persistence proof

The same read-only fingerprint command sorted every graph node's labels and
properties, and every relationship's endpoints, type and properties, then
hashed canonical JSON. Internal numeric graph IDs were not part of the digest.

| Checkpoint | Nodes | Relationships | Graph fingerprint |
| --- | ---: | ---: | --- |
| Before outage/restart | 63 | 127 | same SHA-256 below |
| After service restart | 63 | 127 | same |
| After migration to corrected named-volume mount | 63 | 127 | same |
| After AOF compaction, fixed tests and forced recreation | 63 | 127 | same |

```text
f1849b43b4ad9c3cb7ef64b7d6f3537bd76bddffd90a7c55d48cc5be8701e79a
```

No seed command ran between these checkpoints. Final mount inspection showed
`rippleproof-ai_graph-data -> /var/lib/falkordb/data`. Runtime configuration was
`appendonly=yes`, `appendfsync=everysec`. Final startup included:

```text
Graph 'rippleproof' processed 63/63 nodes
Graph 'rippleproof' processed 127/127 edges
DB loaded from append only file
Ready to accept connections tcp
```

## Exact commands and captured output

The full runtime transcript, including both seed JSONs, every selected test
name/result, complete HTTP bodies, backup checksums, snapshot command, migration,
compaction, warnings and the discarded probe, is in
verification/phase1-runtime.log (historical local artifact; excluded from public candidate).
This is verification evidence, not a runtime knowledge store.

Main reproducible commands actually executed:

```powershell
docker version
docker compose version
docker compose up --build -d
docker compose exec -T backend python -m rippleproof.seed
docker compose exec -T backend python -m rippleproof.seed
docker compose --profile test build tests
docker compose --profile test run --rm tests python -m pytest -vv -m integration -p no:cacheprovider
docker compose --profile test run --rm tests
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m pip check
docker compose exec -T backend python -m pip --no-cache-dir check
docker compose --profile test run --rm --no-deps tests python -m pip --no-cache-dir check
docker compose config --quiet
docker compose restart falkordb backend
docker compose up -d --wait
docker compose up -d --force-recreate --wait falkordb backend
docker compose ps
```

The record also includes the exact stopped-container copy commands used once
to preserve the original incorrectly mounted database. They are migration
history, not normal startup steps.

## Files changed in this continuation and remaining limits

- `compose.yaml`: correct persistent data mount and Redis arguments.
- `tests/integration/test_graph.py`: persist empty-graph test setup in AOF.
- `.gitignore`, `.dockerignore`: keep local database backups out of Git/builds.
- `README.md`, `docs/ARCHITECTURE.md`: actual passing status, correct
  persistence description, observed responses and Phase 1 boundaries.
- This verification record, the preserved initial-attempt record and the raw
  runtime transcript.

FalkorDB remains the sole canonical domain datastore. API reads use fixed,
parameterized Cypher and the official client; deterministic certificate checks
and demand arithmetic remain separate from graph access. No runtime application
query or demo answer needed special-casing to pass verification.

Phase 1 demonstrates dependencies and modeled certificate status only. It
does not allocate stock, model outage durations, forecast lateness, assess
purchase feasibility, call an LLM, implement a frontend, or store approved
decisions. Seeding is recoverable but spans multiple query batches; concurrent
external writes are not snapshot-isolated. Floating image tags and the small
graph's lack of pagination/index tuning remain documented limits.

The required image's bundled browser is not published; its session-secret
warnings do not affect this graph API. Redis is unauthenticated in the local
development stack, with published ports bound to 127.0.0.1. No public deployment
or real procurement action was performed.

**No outstanding human setup action is required for Phase 1.** Services are
left healthy. The next recommended phase is the deterministic stock/time/
capacity/certification scenario engine, only after explicit human review and
approval. STOP: no Phase 2 implementation has begun.
