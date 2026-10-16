# Later-phase checklist (NOT a task to implement now)

## Phase 2 — Evidence-based scenario engine
- Define deterministic stock allocation and purchasing arrival assumptions.
- Separate supplier outage dependency detection from actual late-delivery risk.
- Compare the baseline with supplier alternatives.
- Enforce expiry-valid certifications for every required part certificate.
- Enforce lead times and supplier capacity across multiple orders.
- Show per-order reason codes, cost changes and uncertainty/assumptions.
- Snapshot changes must alter the result in an integration test.

## Phase 3 — AI agent with controlled tools
- Real tool calling with constrained parameters and fixed validated tools.
- Tools discover graph paths, evaluate candidates and explain the result.
- No generated unrestricted Cypher or fabricated numbers.
- Optional MCP interface; no-key scripted/demo mode clearly labeled.
- Store human-approved plan and evidence in FalkorDB; retrieve next session.

## Phase 4 — Frontend
- React + TS, clean high-quality command center and graph explorer.
- Distinguish confirmed graph facts, forecasts, and recommendations.
- Scenario details, candidate rejection, evidence path inspection.
- Accessible responsive UI, clean handling of loading/empty/failure states.

## Phase 5 — Test and submit
- At least 15 curated deterministic scenarios with ground truth.
- Report actual results: impacted order recall, invalid-source rejection,
  evidence-path completeness and failure behavior.
- Confirm repeatable one-command setup and restart persistence.
- Public GitHub repo, README, graph schema, Cypher, AI-use disclosure.
- Working demo video with database / app / scenario / decision evidence.
- Submit in Track 1 through official WeMakeDevs panel before
  2026-10-18 21:29 TRT (GMT+3).
- Side-prize blog is optional and only after core demo is complete.
