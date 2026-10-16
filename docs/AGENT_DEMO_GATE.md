# Agent demonstration and authorization gate

Phase 5A performs **no remote or paid LLM calls**. Guided MCP is usable without a
key. Real-provider acceptance remains blocked pending separate human approval.
Presence of a key or enabled environment variable is configuration, not consent.

## Three evidence categories

| Category | Actual behavior | What can be claimed |
| --- | --- | --- |
| Guided MCP | Fixed sequence over genuine SDK stdio tools, real FalkorDB, model_requests 0 | Deterministic graph walkthrough |
| Controlled provider | Test-only injected scripted model chooses actual MCP calls | Tested orchestration with a model simulator; no external LLM |
| Remote provider | Separately authorized external model selects tools and returns grounded selection | Only after observed provider metadata, model_requests > 0, real MCP trace and source validation |

`GET /api/agent/capabilities` reads validated backend configuration only. It does
not construct a provider, probe a key or contact a model. No secret is returned.
It reports mode, provider/model names and actual enforced resource bounds.
The existing `POST /api/agent/run` contract remains unchanged. Disabled or partial
configuration leaves the real-agent control disabled. Capability failure also
fails closed; guided mode remains an explicit separate action.

The workbench's existing guided panel now includes this capability gate. It
fetches current capability and health before an agent attempt. An authorized
operator must acknowledge a separate run permission and click **Run real agent**.
There is no background model call, automatic agent retry, or automatic switch
from agent failure to guided mode. Duplicate clicks are blocked synchronously;
one agent attempt is allowed per open review. This is a UI guard, not server
rate limiting. Closing/reopening does not enforce a financial quota.

Successful agent responses must identify agent mode, positive bounded model
request count, a successful simulation tool, the exact operator scenario and
matching scenario references. Unknown source revisions disable current evidence
links. Controlled providers are explicitly marked as simulators. Their injection
is only possible in the Python test factory, never by a public request field.

## Existing enforced bounds

Defaults: six model requests, eight tools, 20 seconds per model request, 90 seconds
per run; settings restrict them to at most eight requests/twelve tools/30s/120s.
Provider output is capped at 1,200 tokens and 64 KiB per response; accumulated
input is capped at 128 KiB. Tool schemas/arguments, graph revisions, evidence and
final selection are validated. No raw Cypher or approval tool is exposed.
Provider transport disables retries and environment proxies. Model text never
authors authoritative costs, quantities or compliance status.

These resource bounds **do not enforce a currency spend cap**. The backend is
one local worker with no production authenticated agent gateway or global spend
ledger. Cancellation stops browser waiting; it cannot guarantee cancellation of
an already submitted provider charge. The application cannot approve purchases.

## Mandatory human gate before Phase 5B

Record, without secrets: explicit provider/model, maximum currency spend and
maximum number of invocations, whether the operator will configure the key
themselves, and which isolated or live read-only dataset is approved. Keep
provider credentials server-side only. Do not enable or invoke a remote provider
until these decisions and explicit authorization are recorded. Prefer one bounded
attempt with account-side budget controls and conservative model/tool limits.

After authorization, capture the actual configured model/provider, provider-side
response/request or billing metadata, observed model_requests, ordered selected
MCP tools, sanitized source references and final fact-grounded result. Check the
recording against the source graph, strip credentials/raw sensitive requests,
and disclose any failed/timeout calls and charges. Configuration metadata or a
controlled test is not proof of an external run. If this gate is not passed,
record only guided MCP, clearly labeled; disclose that this is a Track 1 gap.
