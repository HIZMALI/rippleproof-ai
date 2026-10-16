"""Authenticated internal approvals. Never books inventory or places procurement."""

import hashlib
import hmac
import json
import threading
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StringConstraints, model_validator

from rippleproof.errors import EntityNotFound, OperationError
from rippleproof.simulation.engine import ENGINE_VERSION, simulate
from rippleproof.simulation.models import Receipt, ScenarioRequest
from rippleproof.tool_models import DecisionId, EvidenceRef, Fingerprint, ScenarioId, StrictInput
from rippleproof.tools import GraphTools

PolicyId = Annotated[
    str,
    StringConstraints(pattern=r"^(cost_first|lead_first|no_procurement|supplier:S-[0-9]{2,5})$"),
]


class PrepareRequest(StrictInput):
    scenario: ScenarioRequest
    mitigation_plan_id: PolicyId


class DecisionPreview(StrictInput):
    scenario_id: ScenarioId
    operational_fingerprint: Fingerprint
    scenario: ScenarioRequest
    mitigation_plan_id: PolicyId
    plan_revision: Fingerprint
    selected_suppliers: list[str]
    restored_orders: list[str]
    proposed_shipments: list[Receipt]
    estimated_additional_procurement_cost: str
    evidence_refs: list[str]
    limitations: list[str]
    engine_version: str
    action: Literal["internal_decision_only"] = "internal_decision_only"


class ApprovalRequest(PrepareRequest):
    expected_scenario_id: ScenarioId
    expected_operational_fingerprint: Fingerprint
    expected_plan_revision: Fingerprint
    idempotency_key: str = Field(pattern=r"^[A-Za-z0-9_-]{16,80}$")
    operator_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{2,39}$")
    rationale: str = Field(min_length=1, max_length=1000, pattern=r"\S")
    confirm_internal_decision: StrictBool

    @model_validator(mode="after")
    def explicit_confirmation(self):
        if self.confirm_internal_decision is not True:
            raise ValueError("Explicit human confirmation of an internal decision is required")
        return self


class DecisionRecord(StrictInput):
    decision_id: DecisionId
    status: Literal["APPROVED_INTERNAL"]
    created_at: str
    operator_id: str
    rationale: str
    evidence_ref: EvidenceRef
    preview: DecisionPreview


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def decode_record(props):
    return DecisionRecord(
        decision_id=props["id"],
        status=props["status"],
        created_at=props["created_at"],
        operator_id=props["operator_id"],
        rationale=props["rationale"],
        evidence_ref=props["evidence_id"],
        preview=DecisionPreview.model_validate_json(props["preview_json"]),
    )


# All API approval services share a lock in the single-worker localhost demo.
# This does NOT exclude external DB writers or other API processes; see architecture.
APPROVAL_LOCK = threading.RLock()


class DecisionService:
    def __init__(self, repository, settings):
        self.repository, self.settings = repository, settings

    def authenticate(self, authorization):
        secret = self.settings.approval_secret
        if secret is None:
            raise OperationError(
                503,
                "approval_not_configured",
                "Configure a local approval secret to enable manual approval",
            )
        expected = "Bearer " + secret.get_secret_value()
        if not authorization or not hmac.compare_digest(authorization.encode(), expected.encode()):
            raise OperationError(
                401, "approval_unauthorized", "A valid operator approval token is required"
            )

    def calculate(self, request, expected_fingerprint=None):
        if not request.scenario.include_mitigation:
            raise OperationError(
                422, "mitigation_required", "Enable mitigation before selecting an internal plan"
            )
        snapshot = GraphTools(self.repository).snapshot(request.scenario.supplier_id)
        if expected_fingerprint is not None and snapshot.fingerprint != expected_fingerprint:
            raise OperationError(
                409, "stale_preview", "Operational facts changed; prepare and review again"
            )
        policies = {"cost_first", "lead_first", "no_procurement"} | {
            f"supplier:{o.supplier_id}" for o in snapshot.offers if o.is_primary is False
        }
        if request.mitigation_plan_id not in policies:
            raise OperationError(422, "unknown_plan", "Selected mitigation policy does not exist")
        result = simulate(snapshot, request.scenario, policy_id=request.mitigation_plan_id)
        if result.incomplete_data:
            raise OperationError(
                422,
                "incomplete_source_data",
                "Resolve incomplete source facts before approving a plan",
            )
        refs = {ref for p in result.proposed_shipments for ref in p.evidence_refs}
        # Archive all coherent operational facts, not only favorable certificates.
        fields = {
            "scenario_id": result.scenario_id,
            "operational_fingerprint": snapshot.fingerprint,
            "scenario": request.scenario.model_dump(mode="json"),
            "mitigation_plan_id": request.mitigation_plan_id,
            "selected_suppliers": sorted({p.supplier_id for p in result.proposed_shipments}),
            "restored_orders": result.restored_orders,
            "proposed_shipments": [p.model_dump(mode="json") for p in result.proposed_shipments],
            "estimated_additional_procurement_cost": str(
                result.estimated_additional_procurement_cost
            ),
            "evidence_refs": sorted(refs),
            "limitations": result.assumptions,
            "engine_version": ENGINE_VERSION,
        }
        return DecisionPreview(**fields, plan_revision=digest(fields)), snapshot

    def prepare(self, request):
        return self.calculate(request)[0]

    def get(self, identity):
        props = self.repository.memory_node(identity)
        if props is None:
            raise EntityNotFound("Decision", identity)
        return decode_record(props)

    def approve(self, request, authorization):
        self.authenticate(authorization)
        request_digest = digest(request.model_dump(mode="json"))
        identity = (
            "D-"
            + digest({"graph": self.repository.settings.graph, "key": request.idempotency_key})[:24]
        )
        with APPROVAL_LOCK:
            existing = self.repository.memory_node(identity)
            if existing:
                if existing.get("request_digest") != request_digest:
                    raise OperationError(
                        409,
                        "idempotency_conflict",
                        "Idempotency key already belongs to a different request",
                    )
                return decode_record(existing)
            preview, snapshot = self.calculate(request, request.expected_operational_fingerprint)
            if (
                preview.scenario_id != request.expected_scenario_id
                or preview.operational_fingerprint != request.expected_operational_fingerprint
                or preview.plan_revision != request.expected_plan_revision
            ):
                raise OperationError(
                    409,
                    "stale_preview",
                    "Operational facts or selected plan changed; prepare and review again",
                )
            created = datetime.now(UTC).isoformat()
            evidence_id = "E-" + identity[2:]
            props = {
                "id": identity,
                "status": "APPROVED_INTERNAL",
                "created_at": created,
                "scenario_id": preview.scenario_id,
                "operational_fingerprint": snapshot.fingerprint,
                "plan_revision": preview.plan_revision,
                "operator_id": request.operator_id,
                "rationale": request.rationale,
                "request_digest": request_digest,
                "evidence_id": evidence_id,
                "preview_json": preview.model_dump_json(),
            }
            evidence = {
                "id": evidence_id,
                "kind": "operational_snapshot",
                "observed_at": created,
                "operational_fingerprint": snapshot.fingerprint,
                "snapshot_json": canonical(
                    {
                        "nodes": {k: v.model_dump(mode="json") for k, v in snapshot.nodes.items()},
                        "relationships": {
                            k: v.model_dump(mode="json") for k, v in snapshot.relationships.items()
                        },
                    }
                ),
            }
            saved = self.repository.save_decision(
                {
                    "decision_id": identity,
                    "decision": props,
                    "request_digest": request_digest,
                    "evidence_id": evidence_id,
                    "evidence": evidence,
                    "source_ids": sorted(snapshot.nodes),
                    "source_count": len(snapshot.nodes),
                    "supplier_ids": preview.selected_suppliers,
                    "order_ids": preview.restored_orders,
                }
            )
            return decode_record(saved)
