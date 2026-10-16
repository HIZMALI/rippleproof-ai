# RippleProof AI — Phase 5B staged final-delivery brief

Event: Graph Hacks 2026. Team: MORVE (single participant). Priority track: Track 1, Agents That Act on Connected Data.

Source candidate examined: `rippleproof-ai-phase5a-candidate.zip` (481 members).
SHA-256: `cb5867ca577631aae334e0723e06c2eeec2c19468dd54a2673c0d4bce9de78f7`

Current acceptance evidence, not independently re-executed in this review: 184 host + Docker backend checks each, 51 frontend tests, 17 real-browser tests, 77 real-FalkorDB integration cases. Real remote provider is NOT verified. The source candidate has no `.git`, `.local`, `.venv`, `.env` or `node_modules`; `.env.example` is permitted. No original-project LICENSE; see RIGHTS.md and third-party notices.

## Codex: preparation-only instruction (authorized without public or paid actions)

**Read the complete existing documentation first**, including `AGENTS.md`, `docs/PHASE5A_VERIFICATION.md`, `docs/AGENT_DEMO_GATE.md`, `docs/PHASE5_RELEASE_GATES.md`, `docs/PUBLICATION_CHECKLIST.md`, and `docs/SUBMISSION_TEXT.md`.

1. Preserve the current application, existing `rippleproof` graph, operational fingerprint, environment, backups, and phase verification artifacts.
2. Inspect the exact reviewed candidate and check SHA-256 against the digest above. If source changes are required later, build and review a new candidate; never pretend it has the previous hash.
3. Perform a *read-only, no-network* API-model compatibility preflight: verify tool schemas and strict final JSON schema requirements against the current Responses API contract. Report compatibility questions and planned smallest possible patches; do not silently change the tested release candidate.
4. Prepare a script/command checklist for **one isolated, read-only real-provider acceptance run**, with no purchases and no approval tool. Do not configure a provider key, enable billing settings, execute the real provider, or charge anything yet.
5. Draft GitHub publication steps from the reviewed candidate in a NEW clean folder, including `git status`, staged-file inspection, source provenance, secret scanning, third-party license acknowledgments, and one truthful current-time initial commit. Do not initialize a public remote or publish/push without user approval. Preserve All Rights Reserved, and do not invent a copyright holder or fabricated commits.
6. Prepare a repeatable authentic ~3-minute screen recording plan: graph relationship, three simulation states 19/18/20, part-specific cert rejection, then **only the observed agent mode**, read-only decision preview, source/docs. Never label controlled or guided mode as real LLM; do not fabricate a video or approval. Recordings may be made by the participant in a later authorized step.
7. Verify the official Track 1 form fields by inspecting organizer instructions available to the operator; do not invent URLs, paste imaginary submissions, or click final submission.
8. Give operator a minimal handoff report: exact remaining human authorization gates, current source snapshot status, candidate hash, any preflight defects, evidence to collect, and the sequence that minimizes deadline risk.

**STOP after preparation.** No model calls; no public GitHub push; no video upload; no hackathon submission; no live decision approval; no data reset. Keep any account credentials private. Do not start open-ended refactors or introduce new features.

## Separate, explicit HUMAN GATE A: real-provider acceptance

Do not proceed without a user statement approving ALL of the following:
- Provider and exact model ID (candidate: OpenAI `gpt-6-luna`; supports Responses function calling and structured outputs per official model documentation).
- Spending ceiling and number of **agent invocations** (recommended: one attempt first, no automatic retry; monetary ceiling to be specified by user).
- Which isolated graph/dataset may be read (prefer fresh synthetic isolated graph); never write to or reset the live operational graph.
- User configures API key *locally* in ignored server-side configuration; never paste key in chat, browser UI, logs, Git or prompts.
- User explicitly authorizes any billable invocation. Application turn/tool/token limits do NOT equal a hard USD budget; confirm account-side controls.

After authorization only: use one agent invocation with actual provider, observe `provider=openai`, `mode=agent`, `model_requests>0`, authentic ordered MCP/FalkorDB tool events, source revision/citations and grounded results; capture redacted provider request/usage metadata. Treat 401, incompatible JSON schema, model timeout or refusal as a FAILED remote acceptance, not a success. Do not auto-retry or change providers silently. Re-disable the provider afterward and verify secrets remain outside published source.

## Separate, explicit HUMAN GATE B: publication

Requires user confirmation of the actual legal rights owner, GitHub account/organization, exact repo name and `public` visibility. Use the reviewed source candidate; do not include private working state or a fabricated Git timeline. Ensure public README/setup/schema/Cypher/AI-disclosure/third-party-notices remain accurate. Verify the URL in a signed-out browser after the real push; do not claim a public repo before then.

## Separate, explicit HUMAN GATE C: video and submission

Participant records authentic screens, checks no credentials are visible, uploads with their chosen provider and verifies the video URL while signed out. Participant submits the reviewed repository/video URLs and track through the real WeMakeDevs form, then captures an actual receipt. Official deadline: 18 October 2026, 23:59 IST = 18 October 2026, 21:29 TRT. Plan for early submission with margin.

### Submission truthfulness

- Synthetic scenario, 145 operational graph nodes, 291 relationships, 19 baseline/18 disrupted/20 mitigated materially covered orders.
- 1,364.00 additional **synthetic** procurement units (not savings, sales, or a real currency quote).
- No actual vendor contact, stock reservation, purchase, guaranteed delivery or global optimization.
- Guided mode: genuine MCP tools but zero model calls.
- Controlled mode: simulated model response that invokes genuine MCP tools.
- Remote model: claim only after an actual recorded, consented run.
- Automated isolated decision persistence is **not** human sign-off.

Useful official references:
- https://www.wemakedevs.org/hackathons/falkordb/rules
- https://www.wemakedevs.org/hackathons/falkordb
- https://developers.openai.com/api/docs/models/gpt-6-luna
