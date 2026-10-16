"""Read-only graph tools. Shared by the actual MCP server, never a write gateway."""

import json
from collections import Counter

from pydantic import ValidationError

from rippleproof.errors import DatabaseUnavailable, EntityNotFound, GraphQueryError, OperationError
from rippleproof.simulation.engine import certificate_checks, simulate
from rippleproof.simulation.models import ScenarioRequest
from rippleproof.simulation.snapshot import dependencies, normalize
from rippleproof.tool_models import (
    AlternativesInput,
    EmptyInput,
    HistoryInput,
    ImpactInput,
    ResolveInput,
    ToolReply,
)

MAX_TOOL_BYTES = 32768
MAX_SNAPSHOT_BYTES = 2_000_000
REGISTRY = {
    "graph_summary": (EmptyInput, "Graph readiness and scoped operational/memory counts."),
    "trace_supplier_impact": (
        ImpactInput,
        "Read multi-hop primary-supply dependency paths; paginate.",
    ),
    "evaluate_part_alternatives": (
        AlternativesInput,
        "Read offers and check every required certificate on the specified arrival date.",
    ),
    "simulate_supply_disruption": (
        ScenarioRequest,
        "Calculate baseline, disruption and optional mitigation; compact, no writes.",
    ),
    "get_decision_history": (
        HistoryInput,
        "Read approved internal decisions and evidence IDs; paginate.",
    ),
    "resolve_evidence": (
        ResolveInput,
        "Resolve graph evidence guarded by operational fingerprint; paginate archives.",
    ),
}


def page(items, query):
    end = query.offset + query.limit
    return {
        "total": len(items),
        "offset": query.offset,
        "truncated": query.offset > 0 or end < len(items),
        "next_offset": end if end < len(items) else None,
        "items": items[query.offset : end],
    }


def path_summary(path):
    return {
        "nodes": [n.id for n in path.nodes],
        "relationships": [r.id for r in path.relationships],
        "path": path.human_readable,
    }


def compact_scenario(result):
    paths = [path_summary(p) for p in result.dependency_paths]
    return {
        "scenario_id": result.scenario_id,
        "operational_fingerprint": result.snapshot_fingerprint,
        "request": result.request.model_dump(mode="json"),
        "dependent_orders": result.dependent_orders,
        "baseline_at_risk_orders": result.baseline_at_risk_orders,
        "disrupted_at_risk_orders": result.disrupted_at_risk_orders,
        "newly_at_risk_orders": result.newly_at_risk_orders,
        "restored_orders": result.restored_orders,
        "remaining_at_risk_orders": result.mitigated.at_risk_orders if result.mitigated else None,
        "incomplete_data": result.incomplete_data,
        "data_issue_count": len(result.data_issues),
        "data_issues": [i.model_dump() for i in result.data_issues[:5]],
        "data_issues_truncated": len(result.data_issues) > 5,
        "details_endpoint": "/api/scenarios/simulate",
        "estimated_additional_procurement_cost": str(result.estimated_additional_procurement_cost),
        "selected_plan_id": next((p.id for p in result.mitigation_plans if p.selected), None),
        "plans": [p.model_dump(mode="json") for p in result.mitigation_plans],
        "proposed_shipments": [p.model_dump(mode="json") for p in result.proposed_shipments],
        "paths": paths[:5],
        "path_count": len(paths),
        "paths_truncated": len(paths) > 5,
        "path_next_offset": 5 if len(paths) > 5 else None,
        "path_tool": "trace_supplier_impact",
        "candidates": [c.model_dump(mode="json") for c in result.candidate_evaluations],
        "assumptions": result.assumptions,
        "action": "internal_proposal_only; manual authenticated approval required",
    }


def history_item(props):
    preview = json.loads(props["preview_json"])
    return {
        "decision_id": props["id"],
        "scenario_id": props["scenario_id"],
        "status": props["status"],
        "created_at": props["created_at"],
        "plan_id": preview["mitigation_plan_id"],
        "evidence_ref": props["evidence_id"],
        "operational_fingerprint": props["operational_fingerprint"],
        "estimated_additional_procurement_cost": preview["estimated_additional_procurement_cost"],
        "detail_endpoint": "/api/decisions/" + props["id"],
    }


class GraphTools:
    def __init__(self, repository):
        self.repository = repository

    def snapshot(self, supplier_id=None):
        raw = (
            self.repository.snapshot_facts(supplier_id)
            if supplier_id
            else self.repository.operational_facts()
        )
        snapshot = normalize(*raw)
        if len(snapshot.model_dump_json().encode()) > MAX_SNAPSHOT_BYTES:
            raise OperationError(
                413, "graph_budget_exceeded", "Snapshot exceeds the demo byte budget"
            )
        return snapshot

    def dispatch(self, name, arguments):
        try:
            if name not in REGISTRY:
                raise OperationError(422, "unknown_tool", "Tool is not in the read-only registry")
            query = REGISTRY[name][0].model_validate(arguments)
            data = self.execute(name, query)
            reply = ToolReply(status="ok", data=data)
            if len(reply.model_dump_json().encode()) > MAX_TOOL_BYTES:
                raise OperationError(
                    413,
                    "result_budget_exceeded",
                    "Result exceeds 32 KiB; use smaller pages or the HTTP detail endpoint",
                )
            return reply
        except ValidationError:
            return ToolReply(
                status="error", error_code="invalid_arguments", message="Invalid typed tool input"
            )
        except DatabaseUnavailable:
            return ToolReply(
                status="error", error_code="database_unavailable", message="FalkorDB is unavailable"
            )
        except EntityNotFound as exc:
            return ToolReply(status="error", error_code="entity_not_found", message=str(exc))
        except OperationError as exc:
            return ToolReply(status="error", error_code=exc.code, message=exc.message)
        except (GraphQueryError, ValueError, KeyError, TypeError):
            return ToolReply(
                status="error",
                error_code="graph_data_error",
                message="Graph facts could not be verified",
            )

    def execute(self, name, query):
        if name == "get_decision_history":
            total, props = self.repository.decision_history(
                query.scenario_id, query.offset, query.limit
            )
            return {
                "total": total,
                "offset": query.offset,
                "truncated": query.offset > 0 or query.offset + len(props) < total,
                "next_offset": query.offset + len(props)
                if query.offset + len(props) < total
                else None,
                "items": [history_item(p) for p in props],
            }
        snapshot = self.snapshot(getattr(query, "supplier_id", None))
        fingerprint = snapshot.fingerprint
        if name == "graph_summary":
            return {
                "ready": True,
                "graph_exists": self.repository.ready(),
                "operational_fingerprint": fingerprint,
                "operational_node_count": len(snapshot.nodes),
                "operational_relationship_count": len(snapshot.relationships),
                "nodes_by_label": dict(Counter(n.label for n in snapshot.nodes.values())),
                "relationships_by_type": dict(
                    Counter(r.type for r in snapshot.relationships.values())
                ),
                "physical_graph": self.repository.summary().model_dump(),
            }
        if name == "trace_supplier_impact":
            paths = dependencies(snapshot, query.supplier_id)
            return {
                "operational_fingerprint": fingerprint,
                "supplier_id": query.supplier_id,
                "interpretation": "dependency_only; reachability does not predict lateness",
                "order_ids": sorted({p.nodes[-1].id for p in paths}),
                **page([path_summary(p) for p in paths], query),
            }
        if name == "evaluate_part_alternatives":
            if query.part_id not in snapshot.parts:
                raise EntityNotFound("Part", query.part_id)
            offers = [
                o for o in snapshot.offers if o.part_id == query.part_id and o.is_primary is False
            ]
            items = []
            for offer in offers:
                checks = certificate_checks(snapshot, offer, query.arrival_date)
                items.append(
                    {
                        **offer.model_dump(mode="json"),
                        "certificate_checks": [c.model_dump(mode="json") for c in checks],
                        "certifications_valid": not snapshot.parts[query.part_id].issues
                        and all(c.status == "valid" for c in checks),
                        "supplier_status": snapshot.nodes[offer.supplier_id].properties.get(
                            "status"
                        ),
                    }
                )
            return {
                "operational_fingerprint": fingerprint,
                "part_id": query.part_id,
                "arrival_date": query.arrival_date.isoformat(),
                "interpretation": "certification on requested date; capacity is not reserved",
                **page(items, query),
            }
        if name == "simulate_supply_disruption":
            return compact_scenario(simulate(snapshot, query))
        if query.expected_fingerprint != fingerprint:
            raise OperationError(
                409, "stale_evidence", "Operational data changed; refresh before resolving evidence"
            )
        fact = snapshot.nodes.get(query.ref) or snapshot.relationships.get(query.ref)
        if fact:
            return {
                "operational_fingerprint": fingerprint,
                "untrusted_graph_data": True,
                "fact": fact.model_dump(mode="json"),
            }
        archived = self.repository.memory_node(query.ref, evidence=True)
        if not archived:
            raise EntityNotFound("Evidence", query.ref)
        facts = json.loads(archived["snapshot_json"])
        return {
            "operational_fingerprint": fingerprint,
            "archived_operational_fingerprint": archived["operational_fingerprint"],
            "untrusted_graph_data": True,
            "kind": "archived_snapshot",
            **page(list(facts["nodes"].values()) + list(facts["relationships"].values()), query),
        }
