# Codex working agreement — RippleProof AI

## Identity and goal
- Product: RippleProof AI, an **explainable supply-chain disruption agent**.
- Event: Graph Hacks 2026 (15–18 Oct 2026), Track 1.
- Team: MORVE, one human participant.
- Implement new hackathon code within the event period, from scratch.
- The competition requires FalkorDB to be essential, not a visualization layer.

## Instructions
1. Read `docs/PRODUCT_SPEC.md`, `docs/GRAPH_MODEL.md`, and active task before coding.
2. Execute **only** the requested phase; stop at its acceptance gates.
3. Prefer demonstrable, maintainable functionality over decorative complexity.
4. Use FalkorDB as the canonical store for entities, edges, provenance, and decisions.
   Do not create a parallel SQLite/Postgres/JSON knowledge store as the source of truth.
5. Query FalkorDB with parameterized, reviewed Cypher templates; never execute
   unrestricted Cypher composed by an LLM or directly from user input.
6. Derive answers and evidence paths from real graph responses; do not hardcode
   the answers to the demo scenario.
7. Separate deterministic constraints and math from LLM explanation/tool selection.
   A model must never invent stock numbers, monetary figures or compliance status.
8. Only use synthetic, public, or human-authorized data. Never put private data,
   API keys, or credentials in the repository or generated test fixtures.
9. Keep the happy path simple: Docker Compose, FastAPI, deterministic seeding.
10. Make seed operation idempotent; no multiplying nodes/edges on second run.
11. Tests must assert real behavior, including at least one integration test
    querying a running FalkorDB container, not solely mocked database calls.
12. Verify API inputs, handle missing suppliers and empty graph, use meaningful
    HTTP error codes, use typed Pydantic models, and add health checks.
13. Do not run destructive operations outside this workspace. No remote push,
    deployment, paid cloud service, or external account mutation without approval.
14. Do not hide errors, fabricate screenshots/logs, claim unexecuted tests passed,
    or silently substitute in-memory data when FalkorDB is down.
15. On completion, report: files changed; architecture choices; exact commands
    executed; real tests and results; known limitations; next recommended phase.
16. Keep an AI-assistance disclosure section in README for competition rules.

## Stack
- Python 3.12+ with FastAPI, Pydantic, pytest, official `falkordb` Python client.
- Docker Compose with `falkordb/falkordb:latest` and backend service.
- TypeScript + React + Vite and Cytoscape.js, **in later phases only**.
- Real tool-calling agent and optional MCP integration, **in later phases only**.
- Docker ports should bind to 127.0.0.1 during local development.
- Use fixed 2026-10-15 scenario reference dates for deterministic tests.

## Non-goals until later phases
- Do not build frontend, chat UI, LLM integration, external enterprise API,
  authentication product, production billing, or optimizers in phase 1.
- Do not claim future simulation correctness based on reachability alone.
- Do not generate a static slideshow masquerading as a functional demo.
