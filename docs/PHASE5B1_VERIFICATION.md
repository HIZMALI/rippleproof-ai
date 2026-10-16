# Phase 5B-1 — minimal provider telemetry verification

16 October 2026, Europe/Istanbul. Scope: provider telemetry, documented contract
compatibility and regression verification only. No real/paid model request,
credential probe, provider enablement, Git commit/push/publication, video upload,
submission or live approval was performed. The real-provider acceptance run has
**not started**. Stop for review of a separate replacement candidate.

## Implementation and exact changed files

| File | Change |
| --- | --- |
| `rippleproof/telemetry.py` | Three typed metadata/usage contracts, bounded context-local collector, identifier redaction, missing-data/consistency handling and aggregate snapshots |
| `rippleproof/provider.py` | Observe request/response metadata in finally; preserve list return contract and errors/bounds; equivalent final enum and encrypted reasoning inclusion for stateless replay |
| `rippleproof/agent.py` | Wrap each invocation in its own collector and attach telemetry after execution; optional Python collector for externally cancelled calls |
| `rippleproof/agent_models.py` | Optional nullable `provider_telemetry` field on AgentResponse |
| `frontend/src/api/contracts.ts` | Regenerated 46 validators from actual running OpenAPI; no presentation change |
| `tests/test_provider_telemetry.py` | 23 mocked-transport cases, including redaction, aggregation, concurrent contexts and interrupted bodies |
| `tests/integration/test_mcp_agent.py` | Existing four-round OpenAI-protocol mock now verifies metadata through real MCP/FalkorDB; two new cancellation/timeout regressions; controlled providers remain null |
| `tests/integration/conftest.py` | Optional retain-test-graphs flag for this non-destructive full-suite verification; existing default cleanup behavior remains |
| `frontend/e2e/agent.spec.ts` | Respect evidence directory override for controlled-provider captures; avoid overwriting accepted Phase 5A artifacts |
| `scripts/verify_provider_contract.py` | Socket-guarded offline request/schema check and clearly labeled mocked metadata example; no real key lookup |
| `scripts/release_candidate.py` | Explicit phase5b1 archive name/manifest; include new sanitized evidence/helper; preserve phase5a default |
| `README.md`, `docs/ARCHITECTURE.md` | Current verification/disclosure and metadata semantics |
| `docs/PHASE5B1_VERIFICATION.md`, `docs/verification/phase5b1/` | This execution report and fresh evidence |

No graph schema, mathematical formula, supplier data, purchase/approval protocol,
MCP registry, endpoint, provider selection, dependency or container image pin was
changed. All Rights Reserved and third-party notices remain intact. Work remains
on main; no commit or branch creation occurred.

`OpenAIProvider.complete(messages, tools)` still returns the same output-item
list. It adds no metadata to model context or MCP. The coordinator's optional
response field leaves existing fields untouched. Guided and scripted providers
have `provider_telemetry:null`; zero remote usage is never fabricated for them.
The current frontend parses the additive field without UI redesign. Existing
six/eight default model/tool bounds, maximum eight/twelve, per-request/run
timeouts, 1,200 output tokens, 64 KiB response and 128 KiB context budgets remain.

## Metadata semantics and redaction

Each actually attempted provider request can record UTC start, monotonic elapsed
milliseconds, HTTP status, `x-request-id`, response `id`, returned `model`, known
response status, execution outcome and safe error classification. IDs/model come
only from received headers/body; the configured model is never used as a fallback.
Missing/invalid/redacted fields remain null. Timing and local outcome are measured
locally; they are not represented as provider-reported timing/error text.

Input/output/total tokens come only from the response `usage` object. Booleans,
strings, negative/implausible counts are rejected. Reported counters must agree
before complete totals are available. `usage_complete` is false if any request
is missing valid consistent counters. In that case aggregate `usage` stays null
per field and `observed_usage` sums only counters actually present. Missing values
are never filled with zero, estimated, inferred from other counters or treated
as a billing receipt. Counts can include unsuccessful/incomplete responses if
the provider actually reports them.

Only allowlisted identifier shapes, counters and statuses survive. The current
key and sensitive input values are rejected if reflected in identifier fields;
credential markers, malformed identifiers and overlong values are dropped and
named in `redacted_fields`. No arbitrary headers, prompts, tool/request contents,
raw bodies, provider error messages, exception strings or credentials are stored.
Error information is a fixed local classification plus observed HTTP/provider
status, not copied provider text. Rejected HTTP requests retain observed headers
but do not read/archive error bodies. This preserves prior rejection behavior.

A context variable isolates concurrent invocations; snapshots copy metadata.
The finally block records timeouts, transport errors, malformed/oversized bodies
and cancellation. A total run timeout returns partial telemetry with the existing
504 response. External cancellation is re-raised; an explicitly supplied Python
collector remains inspectable. A disconnected caller may not receive a response.
There is no durable log/database write: process termination/crash can lose the
in-memory record. Interrupted calls may have unknown usage and possible charges.
No automatic retry, currency cap or production billing ledger was introduced.

## Official API/model compatibility, without a provider request

Current official pages were searched and opened read-only before changes:

- [Responses create/reference](https://developers.openai.com/api/reference/python/resources/responses/methods/create)
  describes returned IDs/model/status and optional usage counters. The generic
  reference URLs intermittently failed in the documentation tool; the Python
  reference opened successfully. No request was sent to `api.openai.com`.
- [API request debugging](https://developers.openai.com/api/reference/overview)
  documents the response request-ID header and notes it may be unavailable.
- [Function calling](https://developers.openai.com/api/docs/guides/function-calling)
  documents Responses function definitions, explicit non-strict mode and replay
  of returned reasoning/tool items with outputs. Existing replay is preserved.
- [Stateless reasoning](https://developers.openai.com/api/docs/guides/reasoning)
  and the Responses reference document `include: reasoning.encrypted_content`
  for multi-turn requests with `store:false`. That request flag is now supplied;
  opaque reasoning is replayed in memory and is never part of public telemetry.
  A mocked-transport/real-MCP test verifies replay and absence from the API result.
- [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
  documents closed/required object properties, enum, patterns and array bounds.
  The final Literal uses an equivalent single-value enum on the wire, avoiding
  dependence on an undocumented const keyword; local Pydantic validation is
  unchanged. This is not a claim that a remote const rejection was reproduced.
- [gpt-6-luna](https://developers.openai.com/api/docs/models/gpt-6-luna) documents
  Responses, function calling and structured outputs. The current request has
  no unsupported sampling parameter; model default reasoning is retained.

The offline driver validates all six real tool schemas and the actual strict
wire schema, then inspects the payload through in-memory MockTransport using
exact model ID `gpt-6-luna`. It checks `text.format`, strict final schema, explicit
non-strict tools, no parallel calls, no storage and the existing token bound.
[Actual offline output](verification/phase5b1/provider-contract-final.json) reports zero
remote network attempts/provider requests and documents fixture origin.

Result: documented request/schema compatibility and controlled protocol behavior
verified. **Account access, credentials, live service acceptance, latency, actual
token cost and real gpt-6-luna tool choice remain unverified.** A 1,200-token
budget can still yield an incomplete response, especially with reasoning; this
is handled as failure rather than silently raising limits or claiming success.

## Sanitized example, explicitly mocked

The reproducible example is generated from two actual **mock HTTP responses**,
not a real LLM trace. First response reports ID `resp_controlled_fixture_1`, model
`gpt-6-luna`, request ID `req_controlled_fixture_1`, usage 17 input / 5 output /
22 total. The second response intentionally omits usage. The resulting summary
has two records, `usage_complete:false`, complete aggregate counters null and
observed totals 17/5/22. Durations are measured by the actual local execution.
The complete typed example is in provider-contract-final.json. No fixture counter,
identifier or provider label is presented as observed remote activity.

The real-FalkorDB integration case uses four in-memory provider responses and
actual SDK stdio tools: impact traversal, simulation and alternative evaluation,
followed by final source selection. The test asserts four request IDs and totals
400/80/480 from those explicit response fixtures, while material facts/cost come
from FalkorDB. The tests never substitute graph data or claim a remote model run.

## Actual verification and errors

| Executed check | Result |
| --- | --- |
| Initial focused provider/new telemetry/real MCP checks | 35 passed, 4.87s |
| Focused total timeout/external cancellation with real MCP | 2 passed, 6.84s |
| Complete host suite, final sequential run | **209 passed, 63.26s** after stateless-replay flag; prior sequential run passed in 63.89s |
| Complete Docker suite | **209 passed, 46.34s** after stateless-replay flag; earlier runs passed in 47.62s and 76.98s |
| Collection split | 79 real-FalkorDB integration / 130 other tests |
| Vitest | **51 passed**, four files, 21.52s under concurrent verification load |
| Actual browser regression | **17 passed, 131.60s**, including desktop/tablet/mobile, disabled gate, controlled tools, approval safety and restart |
| TypeScript, ESLint, Prettier, production build | PASS |
| Ruff / format | PASS, 54 Python files |
| Host/container pip check, Compose config | PASS; no broken requirements |
| Offline documented-contract driver | PASS; zero remote API/network attempts |

The previous 184 backend tests remain included, with 25 added cases. There were
no silent skips or fabricated provider results. All full-suite test graphs are
unique and retained with `RIPPLEPROOF_RETAIN_TEST_GRAPHS=1`; tests never target
the live graph. An initial focused run used the existing fixture's standard
cleanup for its newly created temporary graph before retention was enabled.
No existing database, live graph, volume or backup was deleted/reset. The legacy
empty-graph test deletes its own single probe node in its newly created graph.

First host run under overlapping builds/tests: **208 passed / 1 failed**, 131.83s.
An existing adversarial scenario case received 502 rather than expected 422.
All four related cases passed on focused rerun (6.34s); the full sequential host
run then passed. Resource contention is a possible cause, not a proven diagnosis.
Added response text to that assertion for future diagnostics; no assertion,
timeout, tool or turn limit was weakened. Initial Ruff line-length/import issues
were corrected before final checks. Generic official-doc retrieval failures were
handled using the successfully opened primary references above.

## Exact commands executed

Root PowerShell; repeat full-suite invocations are included above with outcomes:

```powershell
.venv\Scripts\python -m pytest -q tests/test_agent_provider.py
.venv\Scripts\python -m pytest -q tests/test_provider_telemetry.py tests/test_agent_provider.py tests/integration/test_mcp_agent.py::test_openai_protocol_mock_transport_with_real_mcp_end_to_end
$env:RIPPLEPROOF_RETAIN_TEST_GRAPHS='1'; .venv\Scripts\python -m pytest -q tests/integration/test_mcp_agent.py -k 'metadata_survives or external_cancellation'
$env:RIPPLEPROOF_RETAIN_TEST_GRAPHS='1'; .venv\Scripts\python -m pytest -q tests/integration/test_mcp_agent.py -k 'adversarial_or_failed_model'
$env:RIPPLEPROOF_RETAIN_TEST_GRAPHS='1'; .venv\Scripts\python -m pytest -q
.venv\Scripts\python -m pytest --collect-only -q -m integration | Select-Object -Last 2
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m pip check
.venv\Scripts\python scripts/verify_provider_contract.py --output docs/verification/phase5b1/provider-contract.json
.venv\Scripts\python scripts/verify_provider_contract.py --output docs/verification/phase5b1/provider-contract-final.json
docker compose up -d --no-deps --build backend
docker compose up -d --no-deps --build frontend
docker compose --profile test build tests
docker compose --profile test run --rm --no-deps -e RIPPLEPROOF_RETAIN_TEST_GRAPHS=1 tests
docker compose exec -T backend python -m pip check
docker compose config --quiet
docker compose ps
```

Frontend working directory:

```powershell
npm run contracts
npx prettier --write e2e/agent.spec.ts
npm run typecheck
npm run lint
npm run format:check
npm test
npm run build
npm audit --audit-level=low
```

Browser command: `.local\phase5b1_browser.ps1`, a private wrapper setting
`EVIDENCE_DIRECTORY=../docs/verification/phase5b1/browser` before `npm run test:e2e`
and restoring backed-up private harness control files in a finally block.
The new harness state is retained privately too. [Browser results](verification/phase5b1/browser-results.json)
record the actual run; traces/HAR/video stay disabled. Archive/export and final
preservation results are recorded below. No future real-provider acceptance
command was run. Only isolated browser tests may write synthetic internal test
records; no live approval or operational write is authorized by this report.

## Preservation, release and limitations

The immutable accepted 481-member archive remains SHA-256
`cb5867ca577631aae334e0723e06c2eeec2c19468dd54a2673c0d4bce9de78f7`.
Its manifest/tree, prior evidence and backups are checked against private
before-run hashes. A new archive uses the phase5b1 name in a new exclusive
directory, with an external per-file manifest and SHA-256; it never overwrites
or re-labels the accepted file. External metadata avoids a self-referential ZIP
hash. Final export excludes secrets, Git metadata, local state, dependencies,
browser raw artifacts and backups, scans selected content/history, and audits
every ZIP member. Actual final counts/hash are in its external manifest and
the handoff response.

Live graph baseline: 145 nodes, 291 relationships, 82 receipts and zero
Decision/Evidence nodes; fingerprint
`d3c35628f3c00ce059907dfbe57a6acfa639d5b95f931b650a7faeb55abee19e`.
Final proof compares the full typed snapshot and reference simulation, not
counts alone. Backend/frontend were rebuilt with --no-deps; database container,
volume, settings and existing graph are not upgraded, seeded or migrated.

[Actual preservation proof](verification/phase5b1/preservation.json) verifies
591 original artifact/backup/candidate files byte-for-byte, the full operational
snapshot and complete reference response. Live guided mode was also called
read-only: four genuine MCP tools, zero model requests and null telemetry.
The provider remains disabled and live Decision/Evidence counts remain zero.
The private harness credential/control state was restored; the new test state
is separately retained. `npm audit --audit-level=low` reported zero vulnerabilities.

The final protocol check added the documented stateless-reasoning include flag;
24 focused provider/real-MCP cases passed afterward in 2.00s. The complete host
and Docker suites were then rerun on that exact runtime source. Browser coverage exercised
the unchanged guided/controlled UI paths; the real provider is disabled, and
its wire-only flag is covered by the offline and real-MCP mocked HTTP checks.

Final local commands:

```powershell
.local\phase5b1_browser.ps1
.venv\Scripts\python .local/phase5b1_final.py
.venv\Scripts\python scripts/release_candidate.py --phase phase5b1
```

The exporter writes an exclusive new folder and `rippleproof-ai-phase5b1-candidate.zip`.
Its external manifest records phase, every file hash, ZIP hash/size, history scan,
known-value/pattern scan and sanitized-document list. A separate verification
companion rechecks every archive hash/path, source equality, all 269 unchanged
dependency notices, and the accepted archive's unchanged checksum. The final ZIP
hash is returned to the operator for review; no publication step follows.

No production identity, cross-writer transaction, financial quota, durable
telemetry service, procurement integration or UI redesign is added. All model
metadata examples remain mocked until a separately authorized genuine run.
Presence of telemetry or a compatible documented payload does not authorize
spending. Legal ownership/publication, provider/model budget and credentials,
video and final submission remain separate human gates. **STOP after Phase 5B-1.**
