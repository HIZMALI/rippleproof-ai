# Phase 5B staged execution runbook — PREPARED, NOT EXECUTED

16 October 2026, Europe/Istanbul. This file grants no permission to spend, publish,
upload, submit or approve a live decision. Phase 5A is accepted. Preserve its
reviewed source ZIP and original evidence. Work on main; any publication checkout
is a separate new folder, never a checkout/reset of the working project.

Reviewed ZIP: `rippleproof-ai-phase5a-candidate.zip`, 481 files, SHA-256
`cb5867ca577631aae334e0723e06c2eeec2c19468dd54a2673c0d4bce9de78f7`.
Manifest and ZIP are retained under `.local/releases/20261015T223038256807Z/`.

## Prerequisite: resolve offline-preflight findings

Preflight evidence (historical local artifact; excluded from public candidate) validates local
JSON Schema syntax and the strict final object shape. It does not prove that
the current Responses API accepts every keyword or that an account can use a
particular model. No OpenAI documentation/API request was made in the explicitly
offline preflight. The task names `gpt-6-luna` as a candidate, not a verified
available model. Do not silently substitute another ID.

Before spending, inspect current official function-calling/structured-output
contracts and the exact model's official page with the operator. Check
`text.format` strict JSON schema, `const`, `pattern`, `minItems`/`maxItems`,
function `strict:false`, optional/default tool inputs, `parallel_tool_calls:false`,
reasoning/output-item replay, 1,200-token output budget and model/account support.
These are compatibility questions, not reproduced provider errors.

There is one confirmed evidence limitation: `provider.py` returns only
`data["output"]`, discarding response ID, reported model, usage and request ID.
The current UI cannot produce the required provider-side proof by itself.
`model_requests` counts attempted coordinator rounds, not successful paid calls.

Proposed smallest change, **not applied**: add a bounded run-local metadata sink
to `OpenAIProvider.complete`, keeping the current output return contract. Retain
only HTTP status, `x-request-id`, response `id`, actual `model`, response status,
validated token-usage counters and timings; retain safe error type/code/parameter
for diagnosis. Exclude Authorization, API keys, raw requests, raw error messages,
full response bodies and graph text. Make no automatic retry. A small acceptance
driver can write this allowlist to an ignored local file; do not add a telemetry
service or change graph math/API contracts. An independently reviewed transport
collector is another option; it needs its own bounded-body/redaction tests.

Verify the collector with controlled HTTP transport: successful metadata,
multiple model rounds, 401/429/schema rejection, timeout, truncated/oversized
body, redaction and unchanged output parsing. If a contract issue is confirmed,
patch only that issue and add its regression. Rerun applicable host/Docker,
frontend and browser checks before claiming the replacement release is verified.
Export a **new** candidate and obtain its review; never reuse the old hash.

## Gate A — exactly one isolated real-provider acceptance attempt

Human statement must identify provider, exact model ID, currency/spending ceiling,
maximum **agent invocations** (suggested first attempt: one), approved isolated
graph/dataset, local key setup by the operator, and explicit billable permission.
Account-side spend controls must be checked; application limits are not a hard
currency cap. Record this statement without a key. A suggested authorization
template is: “I authorize [provider/model], up to [currency/amount], at most
[count] agent invocation(s), reading [isolated graph], with the key configured
locally by me.” Unfilled placeholders are not approval.

After that gate and candidate/collector review only:

1. Extract the exact approved candidate into a new ignored folder. Choose a new
   `phase5b_...` Compose project, its own volume, an `acceptance_...` graph and
   unused localhost ports. Scrub inherited `COMPOSE_*`, graph and provider values.
   Default provider stays disabled and approval secret stays empty.
2. With that project's verified Compose context, start services with
   `docker compose -p <unique-project> up --build -d --wait`. Inspect the mounted
   named volume, health and graph name. Require absent/empty graph before the
   explicit `seed` then `migrate` commands **on this new graph only**. Never target
   `rippleproof`, the live volume or the existing retained clean-room stacks.
3. Check the deterministic scenario, revision, graph counts and read-only preview
   without a model. Record these as before evidence. Verify the six-tool registry
   contains no approval/write/Cypher/shell tool.
4. Operator sets the key privately in ignored server-side configuration, outside
   publication checkout. Do not display `.env`, resolved Compose environment,
   shell history or credentials. Enable provider only in the isolated stack.
   Do not alter live configuration or grant a model an approval secret.
5. Verify actual enforced bounds before invocation. Defaults are six model rounds,
   eight tools, 20 seconds/model request, 90 seconds/run. A proposed conservative
   first attempt is four model rounds/four tools; choose limits explicitly.
   Compose currently passes only provider/key/model and approval settings into
   backend. Merely placing turn-limit variables in a host `.env` does **not**
   configure the container. Pass those variables explicitly in the isolated
   override/acceptance process, then verify `/api/agent/capabilities`. Do not
   silently treat unpropagated settings as enforced.
6. Start authentic recording if this attempt will appear in the video. Send the
   following body **once** to that isolated API, using a non-retrying client or
   the explicit UI control. No auto retry, page-driven rerun or provider switch.

   ```json
   {
     "mode": "agent",
     "question": "Trace the supplied outage, simulate its material effect, inspect the relevant alternative certificates, and cite the source graph.",
     "scenario": {
       "supplier_id": "S-04",
       "as_of": "2026-10-15",
       "outage_start": "2026-10-16",
       "outage_end_exclusive": "2026-10-24",
       "include_mitigation": true
     }
   }
   ```

   Target: `POST /api/agent/run`. One invocation may contain several billable
   model requests. A client timeout does not prove the backend stopped or that
   no charge occurred. Wait/check the original attempt and account evidence;
   request permission before any additional invocation.

7. Collect actual `mode:agent`, `provider:openai`, status, model_requests, selected
   tool arguments/status/timestamps/byte counts/hashes, graph fingerprint,
   scenario ID, citations and computed facts. Require actual impact traversal
   and successful simulation. Record collector request/response IDs, returned
   model, usage per round and any failed attempt; keep raw secrets outside logs.
   Configuration names or a positive counter alone are insufficient proof.
8. Accept only observed completed, grounded results matching the isolated graph.
   Authentication/schema errors, refusal, timeout, missing actual tools, invalid
   citations, or `safe_fallback` are not a successful remote acceptance. Capture
   the failure truthfully; no silent retry. Compare the full graph/counts/revision
   afterward, re-disable provider, and verify capability disabled. Do not delete
   containers/volumes/backups as cleanup. Re-scan sanitized evidence before sharing.

No decision approval belongs to this attempt. A live internal record needs a
separate human choice; it remains optional. No purchase is possible through MCP.

## Gate B — publication from an exact reviewed candidate

Human confirms legal source owner, GitHub account/organization, exact repository
name and **public** visibility, exact candidate hash, and permission to publish.
All Rights Reserved is already chosen; do not request/select an open-source
license or invent an owner. Preserve all 269 dependency notice files and SSPL
server/MIT client distinction. Do not copy a Docker volume or container layer.

The following are **future commands**, not executed by preparation. Run in a new
folder only after authorization; placeholders require actual confirmed values.

```powershell
$reviewedZip = (Resolve-Path '.local/releases/20261015T223038256807Z/rippleproof-ai-phase5a-candidate.zip').Path
Get-FileHash -LiteralPath $reviewedZip -Algorithm SHA256
# Compare with the exact approved digest; use the replacement path/hash if patched.
# Create a NEW empty directory below this workspace; do not overwrite an old one.
$publicationRoot = '<confirmed-new-absolute-directory-under-this-workspace>'
New-Item -ItemType Directory -Path $publicationRoot -ErrorAction Stop
Expand-Archive -LiteralPath $reviewedZip -DestinationPath $publicationRoot
Set-Location (Join-Path $publicationRoot 'rippleproof-ai')
git init -b main
git config --local user.name '<confirmed-actual-identity>'
git config --local user.email '<confirmed-author-email>'
git status --short
git add --all
git diff --cached --name-only
git diff --cached --stat
git diff --cached --check
git diff --cached -- README.md RIGHTS.md THIRD_PARTY_NOTICES.md
```

Before commit: compare the entire staged path set and SHA-256 of every staged blob
(`git ls-files --stage -z` then `git cat-file blob <object>`) with the **external
trusted manifest** for the approved ZIP. Require stage zero, exact membership,
no missing/additional file and every byte hash equal. Reject `.env`, `.local`,
`.git`, `.venv`, node_modules, browser artifacts and backups even if force-added.
Run the existing `scripts/release_candidate.py` source/history/pattern scanner
with development Python; it creates another ignored audit copy, never publishes.
Retain its result outside staged source. Inspect content and ownership manually.
Exact staged-byte equality ties the new index to the previously audited source;
pattern scanning alone does not guarantee absence of every secret format.

Document provenance: original source produced during the event under participant
direction, AI assistance disclosed, original working Git has zero commits; local
Codex snapshot trees are not participant commits. No retroactive date or author.
If edits are required, stop and review/export a replacement candidate first.

```powershell
# Only after staged-byte/secret/provenance review and actual identity confirmation:
git commit -m 'Initial RippleProof AI hackathon source release'
git show --stat --format=fuller HEAD
git status --short
# Operator-approved empty public repository must actually exist before this step.
git remote add origin '<actual-approved-GitHub-repository-URL>'
git remote -v
git push -u origin main
```

Do not create/add a remote or execute these commands in preparation. After the
authorized push, open the actual URL signed out; verify source, README, setup,
schema/Cypher, notices and AI disclosure are accessible. Record actual commit ID
and URL, not a proposed URL. No public deployment is needed for the local demo.

## Gate C — authentic video and actual form

Use [the recording plan](PHASE5B_RECORDING_PLAN.md). Human approves the final
cut, upload account/service and visibility. Publish only after that authorization,
then verify the actual video URL signed out/on a second device. The original
recording should be retained; a script is not a video.

Use [verified requirements and unresolved form fields](PHASE5B_SUBMISSION_FIELDS.md).
The operator must inspect their real signed-in WeMakeDevs panel, confirm actual
field labels/limits/required consent, and provide real public source/video URLs.
Do not invent panel routes, guessed field limits or a submission receipt. Review
all values, choose Track 1, verify AI disclosure and participant understanding,
then obtain explicit permission for the final submission. Capture its actual
receipt/time and confirm accepted links.

Minimize deadline risk: resolve model/telemetry questions first while preparing
the publication identity and video rehearsal in parallel as human planning.
If no model run is authorized/successful, use the truthful guided branch and
disclose the agent demonstration gap. Freeze reviewed source, publish once
authorized, record/upload the actual demo, check access, then submit early.
Official close is 18 October 2026 21:29 Europe/Istanbul. An internal target of
17 October 18:00 Europe/Istanbul gives margin; it is not an organizer deadline
or a scheduled automation.
