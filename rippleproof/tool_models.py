"""Strict MCP inputs and bounded structured output envelopes."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints

from rippleproof.models import ISODate, PartId, SupplierId
from rippleproof.simulation.models import (
    CandidateEvaluation,
    MitigationPlanSummary,
    Money,
    Receipt,
    ScenarioRequest,
)


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmptyInput(StrictInput):
    pass


class Page(StrictInput):
    offset: int = Field(default=0, ge=0, le=10000, strict=True)
    limit: int = Field(default=5, ge=1, le=10, strict=True)


class ImpactInput(Page):
    supplier_id: SupplierId


class AlternativesInput(Page):
    part_id: PartId
    arrival_date: ISODate


ScenarioId = Annotated[str, StringConstraints(pattern=r"^SC-[a-f0-9]{20}$")]
DecisionId = Annotated[str, StringConstraints(pattern=r"^D-[a-f0-9]{24}$")]
Fingerprint = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
EvidenceRef = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9:_-]{1,180}$")]


class HistoryInput(Page):
    scenario_id: ScenarioId | None = None


class ResolveInput(Page):
    ref: EvidenceRef
    expected_fingerprint: Fingerprint


class ToolReply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ok", "error"]
    data: dict[str, JsonValue] = Field(default_factory=dict)
    error_code: str | None = None
    message: str | None = None


class CompactPath(StrictInput):
    nodes: list[EvidenceRef] = Field(min_length=1, max_length=8)
    relationships: list[EvidenceRef] = Field(max_length=7)
    path: str = Field(max_length=2000)


class ScenarioToolData(BaseModel):
    # Additional descriptive fields remain bounded by the envelope byte limit.
    model_config = ConfigDict(extra="allow")
    scenario_id: ScenarioId
    operational_fingerprint: Fingerprint
    request: ScenarioRequest
    dependent_orders: list[EvidenceRef]
    baseline_at_risk_orders: list[EvidenceRef]
    disrupted_at_risk_orders: list[EvidenceRef]
    newly_at_risk_orders: list[EvidenceRef]
    restored_orders: list[EvidenceRef]
    estimated_additional_procurement_cost: Money
    incomplete_data: bool
    proposed_shipments: list[Receipt]
    plans: list[MitigationPlanSummary]
    candidates: list[CandidateEvaluation]
    paths: list[CompactPath]
    assumptions: list[str]
