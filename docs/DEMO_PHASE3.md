# Phase 3 localhost walkthrough

Use PowerShell from the extracted repository root. Existing graph data and
volumes must be preserved. No base seed is needed for the verified installation.
These commands use no provider key and make no model API calls.

## Minute 1 — disruption, actual MCP and explanation

```powershell
docker compose up --build -d --wait
docker compose exec -T backend python -m rippleproof.mcp_smoke
$base = 'http://127.0.0.1:18000'
$scenario = @{
    supplier_id = 'S-04'; as_of = '2026-10-15'
    outage_start = '2026-10-16'; outage_end_exclusive = '2026-10-24'
    include_mitigation = $true
}
$guided = Invoke-RestMethod "$base/api/agent/run" -Method Post `
    -ContentType 'application/json' -Body (@{
        question = 'Which orders need help, why, and what internal plan restores them?'
        scenario = $scenario; mode = 'guided'
    } | ConvertTo-Json -Depth 8)
$guided | Select-Object mode, provider, response, model_requests, warnings | ConvertTo-Json
$guided.tool_trace | Format-Table name, status, started_at, finished_at
$guided.facts.paths | ConvertTo-Json -Depth 8
$guided.facts.plans | Format-Table id, restored_orders, estimated_additional_procurement_cost
```

This is an expressly labeled guided walkthrough using actual stdio MCP calls.
It is not an autonomous AI demonstration. With the unchanged reference data,
O-105/O-106 are newly at risk and restored by cost-first proposals costing
1364.00 synthetic units. Inspect S-09/P-22 certificate evidence and S-10's missing
C-02 rejection for P-22. S-10 remains qualified for P-12's C-01 requirement.
Paths are paged and source-backed; dependency reachability alone is not lateness.

## Minute 2 — review, then manual internal approval

Configure a fresh local token without printing it. This enables an approval
endpoint; it does not authorize the agent to use it. Retain the value privately
for retries, or store it securely in the ignored local `.env` for later sessions.
Provider credentials are separate and remain disabled.

```powershell
$env:RIPPLEPROOF_APPROVAL_SECRET = docker compose run --rm --no-deps -T backend `
    python -c "import secrets; print(secrets.token_urlsafe(32))"
docker compose up -d --wait backend
$preview = Invoke-RestMethod "$base/api/decisions/prepare" -Method Post `
    -ContentType 'application/json' -Body (@{
        scenario = $scenario; mitigation_plan_id = 'cost_first'
    } | ConvertTo-Json -Depth 8)
$preview | ConvertTo-Json -Depth 16
```

Read all quantities, dispatch/arrival dates, valid certificate evidence, cost,
assumptions and fingerprint in that preview. Preparation writes nothing. The
following step creates an **internal decision only**, never an actual purchase.
Only the human operator should enter the confirmation and possess the token.

```powershell
if ((Read-Host 'Type APPROVE INTERNAL after reviewing the preview') -ne 'APPROVE INTERNAL') {
    throw 'No approval submitted'
}
$approval = @{
    scenario = $preview.scenario
    mitigation_plan_id = $preview.mitigation_plan_id
    expected_scenario_id = $preview.scenario_id
    expected_operational_fingerprint = $preview.operational_fingerprint
    expected_plan_revision = $preview.plan_revision
    idempotency_key = [guid]::NewGuid().ToString('N')
    operator_id = 'demo-operator'
    rationale = 'Reviewed the computed synthetic recovery schedule and limitations.'
    confirm_internal_decision = $true
} | ConvertTo-Json -Depth 10
$headers = @{ Authorization = "Bearer $env:RIPPLEPROOF_APPROVAL_SECRET" }
$decision = Invoke-RestMethod "$base/api/decisions/approve" -Method Post `
    -Headers $headers -ContentType 'application/json' -Body $approval
$decision | Select-Object decision_id, status, created_at, evidence_ref | ConvertTo-Json
```

Wrong/missing token returns 401 when configured; approval is disabled with 503
when no token is configured. Missing/false confirmation and authoritative extra
fields (cost, quantity, supplier, evidence) return 422. Changed source facts or
plan revisions return 409, requiring a newly reviewed preview. The agent's MCP
registry contains no approval operation.

## Minute 3 — durable memory and unchanged material facts

```powershell
docker compose restart falkordb backend
docker compose up -d --wait
$retrieved = Invoke-RestMethod "$base/api/decisions/$($decision.decision_id)"
$replayed = Invoke-RestMethod "$base/api/decisions/approve" -Method Post `
    -Headers $headers -ContentType 'application/json' -Body $approval
$retrieved | Select-Object decision_id, status, created_at | ConvertTo-Json
$replayed.decision_id -eq $decision.decision_id
Invoke-RestMethod "$base/api/decisions?scenario_id=$($preview.scenario_id)" | ConvertTo-Json -Depth 8
$fresh = Invoke-RestMethod "$base/api/scenarios/simulate" -Method Post `
    -ContentType 'application/json' -Body ($scenario | ConvertTo-Json)
$fresh.snapshot_fingerprint -eq $preview.operational_fingerprint
$fresh.scenario_id -eq $preview.scenario_id
```

The same idempotency request returns its original decision, including timestamp.
It never reserves the proposed material a second time. A different request using
that same key returns 409. For a **new approval key**, an old preview must reject
after relevant source facts change.

Demonstrate stale rejection using the isolated acceptance harness, without editing
the live demo graph. A host Python environment with requirements-dev is needed;
the generated audit graph is retained for inspection. The harness's confirmation
input is explicitly synthetic test data and does not claim human approval.

```powershell
# Run 'before' once; keep its ignored .local audit state for replay.
.venv\Scripts\python scripts/verify_phase3.py --stage before
docker compose up -d --force-recreate --wait falkordb backend
.venv\Scripts\python scripts/verify_phase3.py --stage after
```

The after stage restarts its own API process, retrieves/replays the persisted
record, then temporarily changes stock **only in its isolated audit graph**.
A new-key stale request must return 409. Stock is restored in a finally block.
Never delete the live graph or Docker volume to run this demonstration.

## Real model demonstration: separate pending gate

Configure the operator-selected model, key and explicit paid-call opt-in described
in README, restart the backend, then submit the same agent request with
`mode = 'agent'`. Capture the returned tool_trace and verify provider `openai`,
nonzero model_requests, actual MCP graph evidence and grounded facts. Preserve
only the sanitized response, never the credential. This integration was tested
with a mock HTTP provider driving actual MCP calls; no real paid call was run.

Keep one backend worker and serialize external source edits against approval.
The demo token is not a production identity system, and stale-check/write is not
a server-side transaction excluding external writers. No Phase 4 UI is included.
