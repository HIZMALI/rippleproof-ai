# RippleProof AI — Product UI design direction

## Concept
An **industrial decision intelligence cockpit**, not a generic chatbot, financial trading board, admin template or science-fiction simulation. Serious enterprise software: high information density only where necessary, clear cause-and-effect, and excellent typography. Emphasize "why this conclusion" and "which evidence proves it".

Judge's first impression must answer in 10 seconds:
1. What is broken? (`S-04` supplier outage)
2. What is affected? (graph relationships and at-risk orders)
3. Can we fix it safely? (plan feasibility, certifications, comparative cost)
4. Is the result traceable? (clickable source edges and timestamps)

## Brand and tokens
- Product name: **RippleProof**. Subtitle: **Supply Chain Decision Intelligence**.
- UI language: **English**. Strong grammar and no exaggerated claims like "guaranteed delivery" or "100% safe".
- No emoji anywhere. Use consistent outlined Lucide icons only where they aid meaning.
- Neutral dark theme with restrained industrial character:
  - primary background `#0D1218`, elevated panel `#151D26`, inset `#10171F`
  - border `#293540`, primary text `#EDF2F6`, secondary `#A5B4C1`
  - action accent `#79A6C7` (desaturated blue), positive `#71B29A`, risk `#D6A16B`, critical `#D78080`
  - never make color the sole distinction; pair with label and icon.
- Typography: system UI / Inter-like if already available, clear number tables with tabular numerals; avoid downloading custom font assets just for style.
- Shape: moderate 8–12px radii, 1px hairline borders, controlled shadows. No giant neon gradients, excessive blur/glass, cartoon avatars, animated particles or decorative stock images.
- Spacing system based on 4/8/12/16/24/32px. Large data hierarchy, concise labels and calm negative space.

## Screens and hierarchy

### 1) Command Center / Overview
- Desktop app shell: compact vertical nav with brand and 3 core sections: Overview, Scenario Workbench, Decision Ledger. Top bar: API health, dataset scope, scenario date and local demo context.
- Dominant horizontal "active disruption" strip with supplier, outage period, affected order count, action to analyze. This information only appears if API returns it; else show clear empty state.
- Three comparison columns: baseline, outage, mitigated; where no simulation exists display setup CTA rather than guessed figures.
- Right rail: contextual "Evidence confidence" with number of actual paths and data freshness, *not invented percentages*.

### 2) Scenario Workbench — the hero screen
- At 1440 px, 12-column grid: left 3 columns for inputs + selected supplier; center 6 for evidence graph; right 3 for explanation and alternative vendor inspection. Below: full-width outcomes comparison + impacted orders + proposal schedule.
- Put **comparison** next to **evidence**, not disconnected pages. Selected node highlights path and its order, costs and requirements. Clicking a table row centers path in graph.
- Colored edges differentiate kinds via legend AND text label; use restrained colors, dashed edge only for explicit proposal vs persisted operational edge. Do not imply proposed shipments already exist in DB.
- Graph initially render only scope-relevant paths. Relevant filter chips: impacted / mitigated / rejected / all, but only when backed by real statuses. Fast reset, fit, search by `S-04` / `P-22` / `O-105`.
- Show precise time words: end exclusive, arrival date, expiry, as-of. Use units for every monetary/quantity value.
- Data results: baseline/on-time/disruption/mitigated counts and at-risk order **sets**; show "newly at risk" and "restored" as distinct sets. A mitigation count can exceed baseline if it resolves a pre-existing baseline risk — show explanatory tooltip only if computed output demonstrates it.
- Alternative offer detail: "S-10 / P-22 — Not eligible: C-02 missing" BUT "S-10 / P-12 — Eligible if C-01 valid" only when current response supports it. No vendor-wide pass/fail status.

### 3) Agent Trace & Decision Review
- Embedded in Workbench as accessible right-side drawer or toggle tabs, not a generic chatbot default.
- Transcript style resembles operations timeline: step index, tool, factual returned source, duration/status, evidence refs. Clear fixed state banner:
  - "Guided walkthrough · real MCP tools · 0 model calls"
  - "AI agent · provider not authorized" when 503
  - "AI agent · real provider call" ONLY when backend explicitly confirms model_requests > 0.
- Decision preview modal shows exact plan and full evidence BEFORE any approval action. Confirmation copy: "Approve internal planning record" and typed phrase `APPROVE INTERNAL`. Never label this "Place Order" or "Send to supplier".
- Decision Ledger: calm timeline with decision status, scenario, plan, date, provenance, stable ID, archived evidence link and empty-state explanation. Detail should show original facts and acknowledge staleness where backend exposes it.

## Responsive adaptations
- >=1280 px: 3-column Workbench as above.
- 768–1279 px: responsive 2-column workspace; inspector becomes drawer.
- <768 px: inputs first, compact compare tiles, evidence rendered in a constrained canvas with a usable linear/list alternative, sticky primary action and bottom nav or collapsed top nav. Avoid horizontal overflow. On phones the graph should not be required for evidence accessibility.
- Respect `prefers-reduced-motion`. Use meaningful skeleton placeholders only while loading; no fake streaming words or numerical loading animations.

## Microcopy examples (not hardcoded data)
- `Material coverage, not guaranteed shipping`
- `Certificate valid on projected arrival date`
- `Reason: C-02 not held by supplier`
- `Planned purchase only — no external order placed`
- `Graph evidence: Supplier → Part ← Product ← Order`
- `Data source unavailable. Previous simulation not shown as current.`
- `Preview is stale. Refresh and review the recalculated plan.`

## Anti-patterns to reject in review
- Invented charts, placeholder statistics, hardcoded fixture-only UI, card-grid filler, fake autonomous AI status, showing an approval record as a real purchase, broad "supplier compliant" status, hidden timestamps, raw graph 145+ node hairball, persistent browser secret, or "backend ready" based only on a timer.
