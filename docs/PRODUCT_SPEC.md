# Product specification — RippleProof AI

## Core user story
An operations planner learns that supplier `S-04` is unavailable for eight days.
They ask: “Which orders may be affected, why, and what alternative source
could help?”

RippleProof explores the supply-chain graph and returns evidence chains such
as `Supplier S-04 -> Part P-22 <- Product PR-05 <- Order O-101`.
In later phases, a deterministic simulation allocates stock, checks
certificate requirements, lead times and capacity, compares candidate plans,
and records a human-approved decision back to FalkorDB.

## Hackathon differentiator
The agent must take graph-dependent, explainable actions. A cheap but
non-compliant supplier must be rejected with a traceable reason. A chosen plan
must require operator approval. A future session should retrieve the persisted
decision and be able to reconsider it when facts change.

## Main user-facing features (end state)
- Interactive supply-chain dependency graph and selectable evidence paths.
- Disruption scenario creation using supplier, outage window, and as-of date.
- At-risk order identification respecting inventory and order demand.
- Alternative vendor assessment using lead time, available capacity, cost,
  and required certificates (expiry-sensitive).
- Deterministic scenario ranking with assumptions explicitly stated.
- Graph-guided AI agent: chooses safe tools, queries graph, summarizes evidence.
- Approve/reject plan, store who/when/why/which evidence in the graph.
- Review decisions in a later session.
- Beautiful accessible responsive UI: no emojis, restrained colors,
  keyboard navigation, legible graphs, sensible empty/loading/error states.

## Scope
P0: working graph, impact paths, alternative supplier discovery.
P1: deterministic capacity/time/certification scenario engine.
P2: real LLM tool calling plus no-key transparent demo mode.
P3: polished React control center and persistent decisions.
P4: integration tests, scripted demo, technical docs, submission video.

## Data integrity
- Reachability does NOT imply lateness: first identify dependencies; then
  compute fulfillment risks using quantities, stock and dates.
- Use explicit as-of date and assumptions. Provide each order's demanded
  quantities and why it is classified as at-risk.
- No fabricated claims; expose the distinction between demonstrated data
  and real-world production integration.
- Safe approval should persist an **internal plan**, never place real orders
  or email suppliers without separate user authorization.

## Submission requirements
- Public repository; clear README including setup, graph model, queries.
- Working demo video; deployment or complete local setup.
- Track 1 named clearly; disclose AI assistance.
- All substantial implementation produced during hackathon.
