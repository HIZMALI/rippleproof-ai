# API and MCP reference

The running [OpenAPI explorer](http://127.0.0.1:18000/docs) and
[`app.py`](../rippleproof/app.py) define the actual HTTP contracts. All examples
use synthetic local data. Start services and seed only an empty graph as in
[README](../README.md); existing installations need no reseed.

## HTTP routes

| Method | Route | Behavior |
| --- | --- | --- |
| GET | `/health` | FalkorDB readiness and graph existence; an absent graph is reported without creating it |
| GET | `/api/graph/summary` | Actual physical counts by label/type, including memory |
| GET | `/api/impact-paths?supplier_id=S-04` | Primary-supplier dependencies with actual three-hop paths |
| GET | `/api/alternatives?part_id=P-22&as_of=2026-10-15` | Non-primary offers and certifications evaluated at the requested as-of date |
| POST | `/api/scenarios/simulate` | Read-only baseline, disruption and mitigation comparison |
| GET | `/api/agent/capabilities` | No-store configuration/limits read; no key probe or model call |
| POST | `/api/agent/run` | Explicit guided or capability-gated agent execution |
| POST | `/api/decisions/prepare` | Fresh read-only selected-policy preview |
| POST | `/api/decisions/approve` | Human-confirmed, token-protected internal decision persistence |
| GET | `/api/decisions?offset=0&limit=5` | Paged history; optional exact `scenario_id` filter |
| GET | `/api/decisions/{decision_id}` | Durable internal record and authoritative stored preview |

Malformed/unknown input fields return 422; valid nonexistent entities 404;
approval rejection 401; stale source or conflicting replay 409; unavailable
database/configuration 503. Graph/evidence errors return sanitized 500 responses.
Empty graph/results remain honest empty results. No seed/raw-query HTTP route exists.

IDs/dates are strictly validated. Supplier IDs are `S-` plus 2–5 digits, part IDs
`P-` plus 2–5 digits; dates are exact ISO calendar dates. Monetary outputs are
Decimal strings. A certificate's `valid_until` is inclusive.

## Read-only examples

```sh
curl http://127.0.0.1:18000/health
curl http://127.0.0.1:18000/api/graph/summary
curl "http://127.0.0.1:18000/api/impact-paths?supplier_id=S-04"
curl "http://127.0.0.1:18000/api/alternatives?part_id=P-22&as_of=2026-10-15"
```

Use `curl.exe` in Windows PowerShell if necessary. A portable PowerShell simulation:

```powershell
$scenario = @{
    supplier_id = 'S-04'
    as_of = '2026-10-15'
    outage_start = '2026-10-16'
    outage_end_exclusive = '2026-10-24'
    include_mitigation = $true
}
$json = $scenario | ConvertTo-Json
$result = Invoke-RestMethod 'http://127.0.0.1:18000/api/scenarios/simulate' -Method Post -ContentType 'application/json' -Body $json
$result | Select-Object scenario_id, newly_at_risk_orders, restored_orders, estimated_additional_procurement_cost
```

Reference projection, derived from FalkorDB:

```json
{
  "scenario_id": "SC-4990e7e493adea7efa18",
  "newly_at_risk_orders": ["O-105", "O-106"],
  "restored_orders": ["O-105", "O-106"],
  "estimated_additional_procurement_cost": "1364.00"
}
```

Of 21 open orders, 19/18/20 are materially covered in the three plans.
The full response includes order demands, lot allocations/balances, affected
receipts, rejected suppliers, proposed shipments, compared plans and real graph
paths. As-of alternatives and arrival-date simulation checks intentionally differ.

To run the deterministic guided tools with that same explicit scenario:

```powershell
$body = @{question='Explain the supplier outage'; scenario=$scenario; mode='guided'} | ConvertTo-Json -Depth 8
Invoke-RestMethod 'http://127.0.0.1:18000/api/agent/run' -Method Post -ContentType 'application/json' -Body $body
```

Actual sequence: graph summary, supplier impact, supply-disruption simulation,
decision history. Results identify `guided_walkthrough`, zero model requests
and null provider telemetry. `mode:agent` is a distinct opt-in path; a missing
explicit scenario yields `needs_input`. [Security/evidence categories](SECURITY.md).

Prepare a read-only alternative-policy preview:

```powershell
$previewBody = @{scenario=$scenario; mitigation_plan_id='cost_first'} | ConvertTo-Json -Depth 8
Invoke-RestMethod 'http://127.0.0.1:18000/api/decisions/prepare' -Method Post -ContentType 'application/json' -Body $previewBody
```

The preview returns the current operational fingerprint, plan revision, full
schedule/certificate evidence and Decimal cost. It writes nothing. Approval is
a separate human-controlled action; authoritative quantities/prices are never
accepted from the caller. Same key/intent replays the stored record; changed
intent/source conflicts. An internal record is not a real procurement operation.

## Genuine MCP transport

```sh
docker compose exec -T backend python -m rippleproof.mcp_smoke
docker compose exec -T backend python -m rippleproof.mcp_server
```

The first command is an independent real SDK client/server smoke check. The
second exposes stdio JSON-RPC for an MCP client to spawn; it is not an HTTP URL.
The six tools are `graph_summary`, `trace_supplier_impact`,
`evaluate_part_alternatives`, `simulate_supply_disruption`,
`get_decision_history`, `resolve_evidence`. Strict schemas and implementations
are in [tool_models.py](../rippleproof/tool_models.py),
[mcp_server.py](../rippleproof/mcp_server.py) and [tools.py](../rippleproof/tools.py).
No arbitrary server URL, executable, Cypher, purchase or approval tool is exposed.

For complete source semantics, see [graph schema](GRAPH_MODEL.md),
[queries/algorithms](CYPHER_AND_EVIDENCE.md), [architecture](ARCHITECTURE.md) and
[testing](TESTING.md). No public hosting or remote LLM acceptance is claimed.
