# Phase 5A verification — RippleProof AI

Executed 16 October 2026 Europe/Istanbul (15 October UTC). **Local, non-billable
preparation complete; STOP for human review.** No remote LLM invocation, live
approval attempt, real procurement, GitHub push, public deployment, video upload
or organizer submission was performed. The unrelated XP request was withdrawn.

## Preserved application and graph

The existing main branch was retained. No operational schema, seed fixture,
allocation formula, price, capacity, certification rule or approval protocol was
changed. There was no seed/migrate command against the live `rippleproof` graph.
Live backend/frontend were rebuilt with `--no-deps`, preserving the running
database container and volume. All services are available on localhost:
frontend 18080, API 18000, FalkorDB 6379.

| Proof | Before | After |
| --- | --- | --- |
| Physical/operational nodes | 145 | 145 |
| Physical/operational relationships | 291 | 291 |
| InboundShipment / Decision / Evidence | 82 / 0 / 0 | 82 / 0 / 0 |
| Scenario ID | SC-4990e7e493adea7efa18 | Same |
| Material-covered open orders | 19 / 18 / 20 | Same |
| Gross additional synthetic procurement cost | 1364.00 | Same |
| Complete typed operational snapshot | Captured before edits | Equal |
| Complete simulation JSON | Captured before edits | Equal |

Operational fingerprint:
`d3c35628f3c00ce059907dfbe57a6acfa639d5b95f931b650a7faeb55abee19e`.
The final check compares every normalized source fact and the full response,
not just counts. [Actual data/API proof](verification/phase5a/data-preservation.json).

A new exclusive private backup directory was created before code changes.
`BGSAVE` completed with `rdb_last_bgsave_status:ok`; the copied all-graphs RDB is
874,634 bytes, SHA-256
`5ad69eb09b0ad3e9ada799db349e41caac5d51076ecfab7bfeb866b1557ab874`.
Its checksum was reverified. A separate typed operational snapshot and reference
response were retained. No old backup was overwritten or removed. The backup is
retained locally; **an RDB restore drill was not performed**. Clean-room volume
persistence was tested separately, without restoring over live data.

The inherited baseline browser/check harness wrote historical Phase 4 artifact
names. All 32 historical files were subsequently verified byte-for-byte against
the pre-work local app checkpoint; changed files were restored and the replaced
rerun copies retained privately. New captures use a separate Phase 5A directory.
[Preservation evidence](verification/phase5a/historical-evidence-preserved.json).

## Implemented functionality and files

| Files | Actual change |
| --- | --- |
| `rippleproof/agent_models.py`, `app.py` | Strict capability/limit contracts and GET `/api/agent/capabilities`; configuration-only, no-store, no provider construction or secret output |
| `rippleproof/mcp_client.py` | Fixed package-root working directory for the real MCP subprocess, independent of caller cwd |
| `frontend/src/api/contracts.ts`, `client.ts` | 43 validators regenerated from actual OpenAPI; capability reads and bounded agent POST validation |
| `frontend/src/features/agent/AgentPanel.tsx` | Separate explicit agent intent, fresh capability/health, duplicate guard, one attempt per open panel, no automatic retry, truthful guided/controlled/provider labels and source checks |
| `tests/test_agent_capabilities.py`, `test_release_candidate.py` | 15 new local tests for disabled/partial configuration, no provider construction, no secret exposure, export exclusions/scanning and preservation of notice bytes |
| `tests/integration/test_mcp_agent.py`, `tests/test_validation.py` | Real unrelated-cwd MCP regression; expected OpenAPI inventory extended without removing prior endpoints |
| `frontend/tests/agent.test.tsx`, `client.test.ts` | Eight additional component/client tests, mocked transport explicitly confined to tests |
| `frontend/e2e/agent.spec.ts` | Disabled gate sends zero agent POSTs; controlled model simulator drives actual MCP/isolated FalkorDB |
| `frontend/e2e/approval.spec.ts`, `workspace.spec.ts`, `z-restart.spec.ts` | Configurable evidence output directory; original regression coverage retained |
| `frontend/scripts/capture.mjs`, `capture-agent.mjs`, `clean-demo.mjs` | Separate actual production captures, four-width agent gate/axe checks and read-only clean-install browser walkthrough |
| `scripts/phase4_test_backend.py` | Private test-only injected scripted-provider mode, no product HTTP control route |
| `scripts/release_candidate.py`, `verify_clean_install.py`, `third_party_notices.py` | Separate audited source ZIP; fresh project/volume install proof; inventory and retained upstream notices |
| `compose.yaml`, `Dockerfile`, `frontend/Dockerfile` | Verified manifest pins; test image copies release-tool source required by its unit tests |
| `README.md`, `docs/ARCHITECTURE.md` | Current quickstart, graph role, provider boundary, test commands, honest limits and AI disclosure |
| `RIGHTS.md`, `THIRD_PARTY_NOTICES.md`, `docs/notices/` | All Rights Reserved owner choice; 283 dependency entries and 269 retained notice files; no project LICENSE or invented holder |
| `docs/REFERENCE_API.md` | Preserved historical Phase 4 README/API reference, explicitly marked historical |
| `docs/AGENT_DEMO_GATE.md`, `CYPHER_AND_EVIDENCE.md` | Actual provider gate and resource limits; real reviewed query/source explanation |
| `docs/SUBMISSION_VIDEO_SCRIPT.md`, `SUBMISSION_TEXT.md`, `PUBLICATION_CHECKLIST.md`, `PHASE5_RELEASE_GATES.md` | Authentic recording plan, truthful English submission draft and remaining human gates |
| `docs/PHASE5A_VERIFICATION.md`, `docs/verification/phase5a/` | This report, sanitized executed evidence and real screenshots |

No frontend redesign, new dataset, parallel datastore, public service or account
mutation was introduced. Private backups/test infrastructure remain excluded
from the candidate. The export's manifest enumerates individual notice/evidence
files rather than treating directory names as an inventory.

## Agent demonstration gate and actual traces

The running API returns `agent_available:false`, `execution_kind:disabled`,
`reason_code:provider_not_authorized`; guided remains available. Limits are six
model requests, eight tools, 20 seconds per request, 90 seconds per run, 1,200
output tokens per request and 131,072 accumulated input bytes. Existing maximum
settings and backend validation remain in force. The capability endpoint itself
works without graph access or network/provider initialization.

The UI requires a separately authorized operator's explicit acknowledgement,
then fresh capability and graph health before sending agent intent. Closing the
panel cancels browser waiting; it cannot guarantee cancellation of a provider
charge. Duplicate clicks are blocked synchronously. There is no automatic agent
retry, switch to guided mode, key in the frontend, or implied currency budget.
The client rejects wrong mode/provider, out-of-bound request/tool counts, missing
successful simulation, mismatched scenario inputs/identity and malformed output.
Current evidence links require the open scenario revision.

Three kinds of evidence stay distinct:

- **Guided:** actual production HTTP + real MCP/FalkorDB; four tools in order:
  `graph_summary`, `trace_supplier_impact`, `simulate_supply_disruption`,
  `get_decision_history`; mode `guided_walkthrough`, model_requests **0**.
- **Controlled test:** private isolated test backend, injected `ScriptedProvider`,
  provider `mock-provider`, mode `agent`, status `completed`, four **simulated**
  model requests. Selected tools: `trace_supplier_impact`,
  `simulate_supply_disruption`, `evaluate_part_alternatives`. These tools used
  real SDK stdio and FalkorDB. Actual graph facts supplied scenario, 1364.00 cost
  and O-105/O-106 restoration. [Sanitized trace](verification/phase5a/controlled-agent-test.json)
  and [actual screenshot](verification/phase5a/controlled-agent-test.png).
- **Remote LLM:** **NOT EXECUTED**. No provider receipt, billing record, remote
  model result or autonomous demo success is claimed. This remains a material
  Track 1 demonstration gap requiring separate authorization and credentials.

An independent SDK smoke client listed exactly six constrained tools and called
all six successfully on the clean installation, including `resolve_evidence`.
[Actual MCP inventory/statuses](verification/phase5a/mcp-sdk.json). The full real
responses are retained privately with the clean install's exact command log.

Before any Phase 5B provider test: human selects provider/model, maximum spend,
maximum invocations and secure key setup. See [the gate](AGENT_DEMO_GATE.md).
Configuration alone is not permission. No such permission was requested or used
in Phase 5A; this report stops at the authorized non-billable boundary.

## Clean installation and load-bearing FalkorDB

Two separate source exports were installed successfully in fresh directories.
The second includes the MCP cwd fix. No `.git`, `.local`, `.venv`, `.env` or
node_modules was present in the installed source. Inherited graph/provider
environment was scrubbed; remote provider remained disabled. Docker built the
application solely from exported source; the external browser test driver used
the original development dependencies only as test infrastructure.

Second project: `phase5a_75262774c8ff`; graph `clean_75262774c8ff`; own named
volume `phase5a_75262774c8ff_graph-data`. Local-only API/web/database ports:
11014/11015/11016. First project uses `phase5a_78dc50c0371a` and 9764/9765/9766.
Both stacks/volumes remain retained locally; no deletion/cleanup was executed.

Executed checks on each:

1. Verified unique mounted volume and absent/empty graph **before** seeding.
2. Ran explicit `seed`, then additive `migrate` twice. Counts remained 145/291.
3. Verified complete reference simulation, 19/18/20, cost 1364.00 and six MCP tools.
4. Restarted all services, then force-recreated them with the same volume; full
   simulation responses remained equal.
5. Stopped **only isolated FalkorDB**. Impact, simulation and guided MCP each
   returned HTTP 503 `database_unavailable`. Restart in a finally block restored
   the identical response; no fixture answer appeared.
6. Actual Chromium walkthrough: graph, P-22/P-12 certification difference, guided
   four-tool/zero-model trace, read-only full plan preview, empty ledger and zero
   console errors. No approval endpoint was called by this walkthrough.

[Actual clean-install evidence](verification/phase5a/clean-install.json).
Final runtime source and dependency/image pins must match the tested export;
the final candidate comparison is retained in its external manifest companion.
Additional documentation and capture helpers are identified separately there.

## Actual test results

| Executed check | Result |
| --- | --- |
| Unmodified baseline host Python suite | 168 passed, 65.66s |
| Unmodified baseline Docker Python suite | 168 passed, 50.58s |
| Unmodified baseline Vitest | 43 passed, 3 files, 2.18s |
| Unmodified baseline Chromium | 15 passed, 2.2m |
| Final host Python suite | **184 passed, 60.62s** |
| Final Docker Python 3.12 suite | **184 passed, 45.88s** |
| Final collection split | 77 real-FalkorDB integration / 107 other tests |
| Final Vitest | **51 passed**, 4 files, 2.62s |
| Final Chromium E2E | **17 passed**, 168.66s; 0 skipped, 0 flaky, 0 unexpected |
| TypeScript / ESLint / Prettier / production build | PASS |
| Ruff lint / Ruff format | PASS; 50 Python source files formatted |
| Host and backend-container pip check | No broken requirements |
| npm audit --audit-level=low | 0 vulnerabilities reported |
| Compose configuration / image manifest availability | PASS |
| Additional actual agent panel at 1440/1024/768/390 px | Disabled; 0 agent POSTs, 0 axe violations, no horizontal overflow |
| Actual production layout captures at those widths | 0 page/console errors |

No provider test was skipped and called successful: external-provider acceptance
is an **unexecuted human gate**, outside this authorized test matrix. Tests which
need the database query it; local tests/mock transport are labeled by scope.
Existing approval tests persist only isolated synthetic records, including lost
response/replay, input clearing, stale 409, invalid 401/422, restart and paging.
[Browser results](verification/phase5a/browser-results.json) and
[isolated persistence](verification/phase5a/regression/isolated-persistence.json)
show the executed outcomes. Live Decision/Evidence counts remain zero.

## Errors found and corrected

- First expanded host and Docker suites each had **182 passed / 1 failed**:
  the exact OpenAPI path inventory needed the new capability endpoint. Updated
  the assertion without dropping earlier routes; focused 34 tests and final full
  suites passed.
- First expanded browser run had **16 passed / 1 failed**: MCP child launched
  from the frontend harness cwd could not import `rippleproof`. It returned zero
  model requests, so the controlled-provider test correctly failed. Fixed the
  package-root child cwd, added a real unrelated-directory integration test,
  and reran all 17 browser tests successfully.
- TypeScript initially rejected optional tool_trace access and a test matcher
  option; guarded the optional field and corrected the matcher. Ruff identified
  an unused import and a long generator line; both were fixed.
- The first new standalone axe capture used an attribute selector for a native
  dialog, then a browser-owned page instead of an explicit context. Both capture
  driver errors were fixed; the four actual scans subsequently passed.
- Export review caught notice Markdown being processed as project documentation.
  Upstream notice bytes are now excluded from sanitization and checked by test.
- A proof-extraction helper initially assumed ToolReply had `evidence_refs` at
  top level. Corrected it to extract actual inventory/statuses; no MCP result
  itself was changed. Initial local image-tag inspection failed for BuildKit-only
  base-image tags; registry manifest inspection and actual builds verified pins.
- Exploratory file/glob lookups and patch context attempts had errors, resolved
  before verification. Upstream license URL attempts returned 404/503; the
  official FalkorDB documentation and installed client notices were used instead.

No outstanding application failure was concealed or replaced by mock results.
See [executed commands](verification/phase5a/COMMANDS.md) for success/failure scopes.

## Public candidate, rights and publication readiness

The separate export selects source/tests/tasks/configuration, useful small
sanitized evidence and retained dependency notices. It excludes `.git`, `.local`,
`.venv`, `.env` except blank `.env.example`, node_modules, caches, browser traces,
HAR, backups, profiles, databases and raw workstation logs. All archive paths
are enumerated and their contents scanned again. No real token value is printed.
The external `manifest.json` lists each file, byte size and SHA-256, archive hash,
actual known-secret/pattern scan findings and history audit. It is outside the
ZIP to avoid a self-referential archive hash.

Executed final candidate audit: **481 files**, **0 secret matches**, two known
private values checked without printing them, **162 reachable Git blobs** scanned,
and every ZIP member enumerated. **76 runtime/configuration/Python-test files**
match the clean-tested export exactly; all **269 upstream notice files** match
their retained original bytes. Remaining differences are documentation, evidence
and release/capture helpers, listed in the external `verification.json`. Archive
size and SHA-256 are in that external manifest, so this report does not attempt
to contain the hash of its own enclosing ZIP. The candidate remains unpublished.

The audited working repository has **zero commits**. Its reachable local Codex
snapshot trees contain source blobs and are also scanned; they are not authored
Git commits or proof of participant authorship. No timestamp, author or history
was invented or rewritten. Final blob/file totals are recorded by the export.

Per explicit owner instruction, there is **no project LICENSE**. All Rights
Reserved is recorded without assuming a legal copyright holder. Preserve all
upstream terms. 283 dependency entries/269 actual notice files are retained;
upstream notice bytes are copied verbatim. FalkorDB server SSPLv1 and Python
client MIT are distinguished. Container layers are downloaded, not redistributed
in the source ZIP; no complete OS-image SBOM/commercial legal review is claimed.

Historical workstation paths and links to excluded oversized/private artifacts
are sanitized only in exported documentation; originals remain local. Current
screenshots were reviewed as actual UI captures: no credential, human identity,
developer home path or browser history is visible. Pattern/known-value scanning
and visual review reduce disclosure risk; they are not a guarantee against all
possible secret formats. Publication still requires human content/rights review.

## Screenshots and startup

- [Actual desktop workbench](verification/phase5a/visual/workbench-1440-viewport.png)
- [Actual mobile workbench](verification/phase5a/visual/workbench-390-viewport.png)
- [Actual mobile agent-disabled gate](verification/phase5a/agent-layouts/agent-disabled-390.png)
- [Controlled simulator with real MCP tools](verification/phase5a/controlled-agent-test.png)
- [Four-width gate and axe evidence](verification/phase5a/agent-layouts/checks.json)

For the existing graph, simply `docker compose up --build -d --wait`; no seed.
For a new empty installation, then explicitly run `docker compose exec backend
python -m rippleproof.seed` and `docker compose exec backend python -m
rippleproof.migrate`. Open local http://127.0.0.1:18080. PowerShell and POSIX
instructions, port settings and tests are in the current root README. These
commands were exercised in fresh isolated projects; the live graph was not seeded.

## Remaining human gates and risks

Review Phase 5A and the exact candidate manifest. Confirm source ownership and
third-party obligations; the no-open-source-license decision is already settled.
Choose whether to authorize a separately bounded real-provider test with secure
key setup; monetary budget and invocation limits must be explicit. A genuine
remote graph-agent trace remains the largest Track 1 demonstration gap.

Optional live internal approval belongs to the human operator. Record an authentic
demo video using [the prepared script](SUBMISSION_VIDEO_SCRIPT.md), then separately
authorize its upload and the reviewed GitHub publication. Fill actual accessible
URLs and receipt in [the checklist](PUBLICATION_CHECKLIST.md); no invented URLs.
Review [submission text](SUBMISSION_TEXT.md) and AI disclosure, and complete the
official submission before the organizer deadline. Public code/video/submission
and external-provider gates remain incomplete; this report is not finalist
acceptance or permission to proceed to Phase 5B.

Existing technical limits remain: localhost demo auth, one worker, external-writer
race, bounded payload/dataset, greedy material feasibility, synthetic prices and
no delivery guarantee. Cancellation is not a billing cancellation. Runtime resource
bounds are not a financial quota. Windows execution and Linux containers were
verified; no native macOS/Linux desktop browser run was performed. Clean install
used cached container layers where available, so it is not an offline or
empty-registry-cache proof. Retained clean stacks consume local resources; no
unauthorized volume cleanup was performed.

Official requirements checked against [organizer rules](https://www.wemakedevs.org/hackathons/falkordb/rules)
and [event/track page](https://www.wemakedevs.org/hackathons/falkordb). Public source,
setup/model, Cypher/algorithms, working video, local setup or deployment, named
track and AI disclosure are required. The stated deadline, 18 October 2026
23:59 IST, is 21:29 Europe/Istanbul. Recheck the official form before submission.
No open-source license requirement was found in those rules.

**STOP: Phase 5A only. No public or billable action is authorized by this report.**
