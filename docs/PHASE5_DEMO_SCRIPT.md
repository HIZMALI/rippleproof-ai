# RippleProof — proposed finalist demo script (approx. 3 minutes, not a contest-mandated limit)

Record actual app/browser, no composited false states, no pasted credentials. English voice-over may be helpful for the international judges. Replace placeholders only with real observed recordings. Track 1.

**0:00–0:20 — Context and problem.** “A supplier outage can disrupt multiple orders through shared parts. Spreadsheet checks miss connected dependencies. RippleProof uses FalkorDB to trace what actually changes.” Show Overview, graph operational counts and provenance. State synthetic demo.

**0:20–0:50 — Graph work, not graph decoration.** Run S-04 outage in Scenario Workbench: as-of 2026-10-15, start 2026-10-16, end-exclusive 2026-10-24, mitigation on. Click path S-04 → P-22 ← PR-05 ← O-101, show real edge IDs. Clarify connected ≠ late. Run genuine graph query proof or open inspected source.

**0:50–1:20 — Measurable effect.** Show baseline 19, disruption 18, mitigation 20 materially covered open orders (out of 21). Point out newly at risk O-105 and O-106, restored by proposal; O-101 remains covered. Show 1,364.00 extra gross synthetic procurement cost, not “savings.”

**1:20–1:48 — Constraint reasoning.** Show P-22: cheap S-10 rejected because mandatory C-02 missing. Show S-09 acceptable, and S-10 is usable for P-12 because its certificate needs differ. Include arrivals, quantities, existing booked capacity, evidence refs.

**1:48–2:18 — Agent uses real graph tools.** Preferred: AFTER explicit provider budget/key authorization, record a genuine `mode:agent` call that chooses MCP tools and cites graph references, and show provider metadata, `model_requests > 0`, real transport trace. Never edit the recording to suggest guided calls were autonomous. If no real-provider verification, show only **“guided MCP tools — deterministic, zero LLM calls”** with its accurate label; this is weaker for Track 1 and must be disclosed.

**2:18–2:50 — Decision and memory.** Show fresh READ-ONLY plan preview with sources and costs. If the human operator explicitly chooses, privately configure the token, review and type `APPROVE INTERNAL`, then inspect a genuine stored decision in Ledger and fetch again after a backend restart. No real purchase or allocation occurs. If no human approval, demonstrate the isolated persisted test separately and label it synthetic; NEVER impersonate an operator approval.

**2:50–3:00 — Technical proof.** Very briefly flash source README/FalkorDB/Cypher/tool tests. Say: “FalkorDB drives impact traversal, supply constraints and evidence-backed decision memory.” Close with project name + track, no invented awards/claims.

## Video recording checklist
- Make an operator walkthrough first, then record once without surprises.
- Use stable 1440×900 or 1920×1080 screen with readable 125% zoom as needed.
- Close private tabs, browser downloads, devtools logs, passwords and personal desktop pop-ups.
- Do not alter the authentic API responses in editing; normal cuts/transitions/voice-over okay.
- Show enough time for the judge to read one evidence path and one rejected alternative.
- Verify video on a second device / signed-out window once published.
- Capture final video URL exactly; do not assume uploading or publication happened.
