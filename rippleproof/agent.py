"""Bounded model coordinator. Every graph action traverses a real MCP session."""

import asyncio
import hashlib
import json
import re
from datetime import UTC, datetime

from pydantic import ValidationError

from rippleproof.agent_models import AgentResponse, FinalSelection, ToolTrace
from rippleproof.errors import OperationError
from rippleproof.mcp_client import connect_graph_tools
from rippleproof.provider import OpenAIProvider
from rippleproof.telemetry import capture_telemetry
from rippleproof.tools import REGISTRY


def evidence_refs(data):
    refs = set()
    items = data.get("items", []) + data.get("candidates", [])
    paths = data.get("paths", []) + [
        item for item in items if "nodes" in item and "relationships" in item
    ]
    for path in paths:
        refs.update(path["nodes"] + path["relationships"])
    for shipment in data.get("proposed_shipments", []):
        refs.update(shipment["evidence_refs"])
    for fact in items + ([data["fact"]] if "fact" in data else []):
        for field in ("id", "offer_ref", "evidence_ref", "source_id", "target_id"):
            if fact.get(field):
                refs.add(fact[field])
        for check in fact.get("certificate_checks", []):
            refs.add(check["requirement_ref"])
            if check.get("holding_ref"):
                refs.add(check["holding_ref"])
    return sorted(refs)


def grounded_answer(facts):
    request = facts["request"]
    return (
        f"Internal material scenario for {request['supplier_id']}, as of {request['as_of']}; "
        f"outage [{request['outage_start']}, {request['outage_end_exclusive']}). "
        f"Baseline at risk: {', '.join(facts['baseline_at_risk_orders']) or 'none'}. "
        f"Disrupted at risk: {', '.join(facts['disrupted_at_risk_orders']) or 'none'}. "
        f"Newly at risk: {', '.join(facts['newly_at_risk_orders']) or 'none'}. "
        f"Restored: {', '.join(facts['restored_orders']) or 'none'}. "
        f"Gross additional procurement cost: {facts['estimated_additional_procurement_cost']} "
        "synthetic cost units. See the calculated shipment schedule and graph paths below. "
        "Materials-only feasibility; greedy heuristic, no delivery guarantee. "
        "This is a proposal; manual authenticated internal approval is required."
    )


class AgentCoordinator:
    def __init__(self, graph_settings, settings, provider=None):
        self.graph_settings, self.settings, self.provider = graph_settings, settings, provider

    async def run(self, request, *, telemetry=None):
        with capture_telemetry(telemetry) as collector:
            result = await self._run(request)
            if collector.requests:
                result.provider_telemetry = collector.snapshot()
            return result

    async def _run(self, request):
        mode = "guided_walkthrough" if request.mode == "guided" else "agent"
        provider_name = (
            "none" if request.mode == "guided" else getattr(self.provider, "name", "openai")
        )
        trace, facts, model_requests = [], None, 0
        if request.scenario is None:
            return AgentResponse(
                mode=mode,
                provider="none",
                status="needs_input",
                response=(
                    "Provide scenario.supplier_id, as_of, outage_start and "
                    "outage_end_exclusive explicitly. Dates are required; no defaults are invented."
                ),
            )
        scenario = request.scenario.model_dump(mode="json")
        fingerprint = None

        async def call(client, name, arguments):
            nonlocal fingerprint, facts
            if len(trace) >= self.settings.max_tool_calls:
                raise OperationError(422, "tool_budget_exceeded", "Maximum tool calls reached")
            if name not in REGISTRY:
                raise OperationError(422, "unknown_tool", "The model requested a forbidden tool")
            if name == "simulate_supply_disruption":
                validated = REGISTRY[name][0].model_validate(arguments).model_dump(mode="json")
                if validated != scenario:
                    raise OperationError(
                        422, "scenario_mismatch", "Model changed the operator's scenario"
                    )
            if (
                name == "trace_supplier_impact"
                and arguments.get("supplier_id") != scenario["supplier_id"]
            ):
                raise OperationError(
                    422, "scenario_mismatch", "Model changed the operator's supplier"
                )
            started = datetime.now(UTC).isoformat()
            result = await client.call(name, arguments)
            encoded = result.model_dump_json().encode()
            trace.append(
                ToolTrace(
                    name=name,
                    arguments=arguments,
                    started_at=started,
                    finished_at=datetime.now(UTC).isoformat(),
                    status=result.status,
                    evidence_refs=evidence_refs(result.data)[:12],
                    output_bytes=len(encoded),
                    output_sha256=hashlib.sha256(encoded).hexdigest(),
                )
            )
            if result.status == "error":
                code = result.error_code
                status = (
                    503
                    if code == "database_unavailable"
                    else 404
                    if code == "entity_not_found"
                    else 422
                )
                raise OperationError(
                    status, code or "tool_failed", result.message or "MCP tool failed"
                )
            observed = result.data.get("operational_fingerprint")
            if observed and fingerprint and observed != fingerprint:
                raise OperationError(
                    409, "source_changed", "Graph changed between tools; rerun the analysis"
                )
            fingerprint = observed or fingerprint
            if name == "simulate_supply_disruption":
                facts = result.data
            return result

        try:
            provider = (
                None if request.mode == "guided" else self.provider or OpenAIProvider(self.settings)
            )
            async with asyncio.timeout(self.settings.run_timeout_s):
                async with connect_graph_tools(self.graph_settings) as client:
                    inventory = await client.inventory()
                    if request.mode == "guided":
                        await call(client, "graph_summary", {})
                        await call(
                            client,
                            "trace_supplier_impact",
                            {"supplier_id": scenario["supplier_id"]},
                        )
                        await call(client, "simulate_supply_disruption", scenario)
                        await call(
                            client, "get_decision_history", {"scenario_id": facts["scenario_id"]}
                        )
                        warnings = [
                            "Guided walkthrough: deterministic tool sequence; no LLM was invoked."
                        ]
                        status = "completed"
                    else:
                        tools = [
                            {
                                "type": "function",
                                "name": t.name,
                                "description": t.description,
                                "parameters": t.input_schema,
                                "strict": False,
                            }
                            for t in inventory
                        ]
                        messages = [
                            {
                                "role": "user",
                                "content": json.dumps(
                                    {"question": request.question, "operator_scenario": scenario}
                                ),
                            }
                        ]
                        warnings, status = [], "completed"
                        for _ in range(self.settings.max_turns):
                            if len(json.dumps(messages).encode()) > 131072:
                                raise OperationError(
                                    422, "context_budget_exceeded", "Agent context budget exceeded"
                                )
                            model_requests += 1
                            output = await provider.complete(messages, tools)
                            if not isinstance(output, list) or not 1 <= len(output) <= 8:
                                raise OperationError(
                                    502, "invalid_model_output", "Invalid model output items"
                                )
                            calls = [item for item in output if item.get("type") == "function_call"]
                            if calls:
                                if len(calls) + len(trace) > self.settings.max_tool_calls:
                                    raise OperationError(
                                        422, "tool_budget_exceeded", "Maximum tool calls reached"
                                    )
                                messages.extend(output)
                                for item in calls:
                                    if not re.fullmatch(
                                        r"[A-Za-z0-9_-]{1,128}", item.get("call_id", "")
                                    ):
                                        raise OperationError(
                                            502,
                                            "invalid_model_output",
                                            "Invalid tool call identity",
                                        )
                                    raw_args = item.get("arguments", "")
                                    if len(raw_args) > 4096:
                                        raise OperationError(
                                            422, "invalid_arguments", "Tool arguments exceed budget"
                                        )
                                    result = await call(
                                        client, item.get("name"), json.loads(raw_args)
                                    )
                                    messages.append(
                                        {
                                            "type": "function_call_output",
                                            "call_id": item["call_id"],
                                            "output": result.model_dump_json(),
                                        }
                                    )
                                continue
                            if facts is None:
                                raise OperationError(
                                    502,
                                    "unverified_answer",
                                    "The model did not obtain a scenario result",
                                )
                            try:
                                texts = [
                                    c["text"]
                                    for item in output
                                    if item.get("type") == "message"
                                    for c in item.get("content", [])
                                    if c.get("type") == "output_text"
                                ]
                                selection = FinalSelection.model_validate_json("".join(texts))
                                if selection.scenario_id != facts["scenario_id"] or not set(
                                    selection.evidence_refs
                                ) <= set(evidence_refs(facts)):
                                    raise ValueError("Unverified citation or scenario")
                            except (ValidationError, ValueError):
                                status = "safe_fallback"
                                warnings.append(
                                    "Model final claims/citations rejected; response rendered "
                                    "only from verified simulation facts."
                                )
                            break
                        else:
                            raise OperationError(
                                422, "turn_budget_exceeded", "Maximum model turns reached"
                            )
                    return AgentResponse(
                        mode=mode,
                        provider=provider_name,
                        status=status,
                        response=grounded_answer(facts),
                        scenario_id=facts["scenario_id"],
                        facts=facts,
                        tool_trace=trace,
                        assumptions=facts["assumptions"],
                        warnings=warnings,
                        model_requests=model_requests,
                    )
        except OperationError as exc:
            return AgentResponse(
                mode=mode,
                provider=provider_name,
                status="error",
                response=exc.message,
                tool_trace=trace,
                error_code=exc.code,
                http_status=exc.status,
                model_requests=model_requests,
            )
        except TimeoutError:
            return AgentResponse(
                mode=mode,
                provider=provider_name,
                status="error",
                response="Agent run timed out",
                tool_trace=trace,
                error_code="agent_timeout",
                http_status=504,
                model_requests=model_requests,
            )
        except (ValueError, KeyError, TypeError, AttributeError):
            return AgentResponse(
                mode=mode,
                provider=provider_name,
                status="error",
                response="Malformed model or MCP output rejected",
                tool_trace=trace,
                error_code="invalid_output",
                http_status=502,
                model_requests=model_requests,
            )
