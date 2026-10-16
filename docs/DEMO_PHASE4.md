# Phase 4 live demonstration

Run `docker compose up -d --build` from the repository root. Open
[RippleProof](http://127.0.0.1:18080). Existing Phase 2/3 data needs no seed or
migration. Use synthetic data; no paid provider or real procurement is involved.

1. **0:00–0:25 — Establish the source.** Overview reads backend health and graph
   counts. Explain operational facts versus physical decision memory. Click
   **Open scenario workbench**. Results initially have an honest empty state.
2. **0:25–0:55 — Follow the ripple.** Keep S-04, as-of 2026-10-15 and outage
   [2026-10-16, 2026-10-24), mitigation enabled. Click **Run scenario**. Inspect
   S-04 → P-22 ← PR-05 ← O-101. The buttons under the graph expose actual source
   properties; O-101 is connected but covered in this run.
3. **0:55–1:35 — Compare material coverage.** The reference graph computes
   19 → 18 → 20 covered open orders. Newly at risk O-105/O-106 are restored at
   1,364.00 gross additional synthetic cost units. Explain that reallocation also
   fixes a pre-existing baseline shortage. Coverage is not guaranteed shipping.
4. **1:35–2:05 — Prove feasibility.** Select P-22 in the material inspector.
   S-09 has valid C-01/C-02; S-10 lacks C-02. Select P-12: S-10 holds required
   C-01 on projected arrival. Inspect a certificate holding/source edge.
   Tablet: use **Open material inspector**; mobile: expand **Material constraints**.
5. **2:05–2:30 — Show actual MCP.** Open **Guided MCP tools**, then **Run guided
   tools**. Show actual ordered trace entries and zero model calls. Guided mode
   is deterministic tool execution; real remote-provider verification remains
   separately authorized operator work.
6. **2:30–3:00 — Review before recording.** Click **Review internal plan**.
   Show complete proposed schedule, certification evidence, costs and revisions.
   This preview is read-only. The live graph has no new decision from our automated
   work. If a human has configured the backend token and wants to demonstrate an
   internal record, acknowledge the preview, enter the local token off-camera,
   pseudonym and rationale, type `APPROVE INTERNAL`, and explicitly approve.
   Open the persisted record in the Ledger and check its source revision.

Never paste a credential into the question, URL, browser storage or screenshot.
Approval places no purchase, reserves no inventory and contacts no supplier.
Do not display isolated automated records as human-approved live decisions.
The screenshots named `isolated-*` in `verification/phase4/` are explicitly
test-harness evidence from a separate graph. An empty live Ledger is correct.

For failure demonstration, enter an invalid end date (inline error), or unknown
supplier S-999 (real 404). Actual service stop/start is covered by the browser
suite with a recovery block. Do not stop FalkorDB or delete a volume to stage a
recording. See [verification](PHASE4_VERIFICATION.md) for executed evidence and
startup/testing details. Stop at Phase 4; Phase 5 is not implemented.
