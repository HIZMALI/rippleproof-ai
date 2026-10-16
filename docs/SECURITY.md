# MCP, provider and approval boundaries

This is a synthetic, one-worker localhost demonstration. Do not expose the
unauthenticated graph/API or internal approval service publicly. All Compose
host ports bind to 127.0.0.1. No enterprise identity, multi-writer transaction
guard, production rate limiting or spending ledger is implemented.

## Three evidence categories

| Mode | Actual execution | Evidence meaning |
| --- | --- | --- |
| Guided MCP | Fixed sequence over genuine SDK stdio tools and FalkorDB; zero model calls | Deterministic graph walkthrough |
| Controlled provider | Injected scripted provider / mocked HTTP transport with actual graph tools | Orchestration/protocol test; not a remote LLM |
| Remote provider | Explicitly configured Responses provider with bounded tool selection | Implemented, **real remote acceptance unverified** |

The public [demo](https://youtu.be/ttOWMdWxIPU) uses Guided MCP. There is no
fabricated autonomous run, silent switch to guided mode or fixture fallback when
the graph is down. Keys/settings alone do not authorize spending.

## Reviewed graph tools

`graph_summary`, `trace_supplier_impact`, `evaluate_part_alternatives`,
`simulate_supply_disruption`, `get_decision_history`, `resolve_evidence`.

There is no raw Cypher, approval, purchase, shell, filesystem or arbitrary
network-fetch tool. User values are validated parameters to fixed templates.
The MCP child receives graph settings only. Results are bounded to 32 KiB,
paged/truncated explicitly where supported; oversized critical facts fail.
Current citations require the matching operational fingerprint. Stored graph
text is untrusted data and never becomes instructions or executable content.

## Enforced limits

| Resource | Default / enforced cap |
| --- | --- |
| Model requests per run | 6 default, at most 8 |
| Tool calls per run | 8 default, at most 12 |
| Model request timeout | 20s default, at most 30s |
| Complete run timeout | 90s default, at most 120s |
| Output tokens per provider request | 1,200 |
| Provider response / accumulated input | 64 KiB / 128 KiB |
| MCP call timeout | 12s |
| Operational snapshot | 2,000 nodes / 4,000 relationships, 2 MB normalized |

Responses transport uses a fixed endpoint, no retries/environment proxies and
`store:false`. Tool/final schemas, operator scenario, source revisions and evidence
are validated. A model cannot author authoritative numeric or compliance claims.
These bounds do **not** enforce a currency quota. Browser cancellation cannot
guarantee cancellation of an already submitted provider charge.

## Provider configuration and credentials

Default provider is disabled and paid calls are false. Capabilities read only
configuration, never probe credentials or call a provider. Agent execution needs
all of `RIPPLEPROOF_PROVIDER=openai`, `RIPPLEPROOF_ALLOW_PAID_CALLS=true`, an
operator-selected model and `RIPPLEPROOF_OPENAI_API_KEY`. Before enabling them,
obtain explicit human authorization for provider/model, invocations, currency
budget and dataset. Prefer account-side budget controls. No remote acceptance
has been performed in this release.

Keep secrets in server-side process environment or ignored `.env`. Never put
them in frontend build variables, prompts, URLs, source control or public logs.
Telemetry keeps only allowlisted response IDs/model/request IDs, HTTP/status,
duration and reported usage. Missing fields remain unknown; error classifications
are fixed safe codes. Raw provider contents, credentials and reasoning are omitted.

## Human internal-plan approval

`POST /api/decisions/prepare` is read-only. It recalculates full quantities,
arrivals, certification evidence, costs and source/plan revisions. Approval
requires a separate 32+ character `RIPPLEPROOF_APPROVAL_SECRET`, Bearer comparison,
explicit boolean confirmation, pseudonym, rationale and idempotency key. The
model has no approval tool. The UI additionally requires schedule review and
typed `APPROVE INTERNAL`; it disables approval off loopback.

The token is transient, cleared after use and omitted from browser storage,
query caches, URLs and test traces/HAR/videos. Never paste a real token into
screenshots or public evidence. Approval records an internal plan only: no
purchase, stock reservation, supplier contact or real capacity booking occurs.

Source changes or conflicting replays return 409; same intent/key returns the
persisted record. The process lock covers one backend worker only. Serialize
external graph writers: the read/check and write do not provide cross-writer
transaction isolation. Human token possession is not production authentication.

See [architecture](ARCHITECTURE.md), [actual queries](CYPHER_AND_EVIDENCE.md),
[API contracts](REFERENCE_API.md) and [isolated test instructions](TESTING.md).
