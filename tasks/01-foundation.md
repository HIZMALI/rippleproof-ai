# Task 01 — Graph-first foundation (ONLY active task)

## Outcome
Working Dockerized FastAPI service backed by a **real FalkorDB graph**,
with reproducible synthetic data and tests. No frontend or LLM in this task.

## Build
1. Inspect installed Docker, Docker Compose, Python tooling; show actual
   versions or give a clear prerequisite blocker. Do not pretend it's working.
2. Build minimal project tree, Docker Compose stack for FalkorDB + backend.
   Bind published ports to localhost. Include `.env.example`, `.gitignore`,
   dependency lock or reproducible package definitions, API Dockerfile.
3. Add `GET /health` for health/readiness that checks FalkorDB availability.
4. Implement graph repository layer using official Python client and fixed,
   parameterized Cypher templates.
5. Implement idempotent synthetic graph seeder invoked by a documented command.
   Include at least 10 Suppliers, 15 Parts, 6 Products, 20 Orders,
   3 Certificates and nontrivial edges, with reproducible IDs.
6. Implement:
   - `GET /api/graph/summary`: labels and relationship counts, zero for empty.
   - `GET /api/impact-paths?supplier_id=S-04`: FalkorDB-derived multi-hop
     affected dependency paths and order identifiers, **not a delay forecast**.
   - `GET /api/alternatives?part_id=P-22&as_of=2026-10-15`:
     FalkorDB-derived candidate suppliers and evidence of cert status.
7. Design typed JSON response models and useful errors. Ensure a
   database-down state cannot silently return fake fixture results.
8. Create unit tests for input validation and synthetic-data invariants.
   Create real integration tests against FalkorDB for seed idempotency,
   path traversal, alternative queries, nonexistent ID, repeatability,
   and database-down behavior.
9. README must show Windows PowerShell-friendly commands and response examples.
   Add diagrams/docs and explain how FalkorDB participates centrally.
10. Optionally initialize local Git but **do not push remotely**.

## Definition of done
- `docker compose up --build -d` starts containers.
- A documented seed command populates actual FalkorDB.
- Second seed run does not multiply nodes/relationships.
- `GET /health` reports true DB readiness.
- `GET /api/impact-paths?supplier_id=S-04` includes Order O-101 via
  Part P-22 and Product PR-05 with genuine graph evidence.
- `GET /api/alternatives?part_id=P-22&as_of=2026-10-15` lists S-09
  as valid according to the modeled certifications and S-10 with
  an evidence-backed certificate deficiency.
- Another supplier with no impacted orders returns an empty result.
- Integration tests really query the container and pass.
- Real executed commands and test summary are recorded.
- No API key, personal data, cloud deployment, or unrequested app mutation.

## Stop conditions
If Docker is unavailable or a dependency cannot be installed, stop and
report the exact failure plus what the human needs to do; provide code
that is independently reviewable but do not assert it ran.

Stop after Phase 1. Request review before proceeding to Phase 2.
