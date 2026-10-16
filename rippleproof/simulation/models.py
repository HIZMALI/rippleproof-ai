"""Typed domain snapshot and API results. Monetary values serialize as strings."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from rippleproof.models import EvidenceNode, EvidencePath, EvidenceRelationship, ISODate, SupplierId

Money = Annotated[Decimal, Field(ge=0, allow_inf_nan=False)]


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supplier_id: SupplierId
    as_of: ISODate
    outage_start: ISODate
    outage_end_exclusive: ISODate
    include_mitigation: StrictBool = True

    @model_validator(mode="after")
    def window(self):
        if self.as_of > date.max - timedelta(days=366):
            raise ValueError("as_of must allow a 366-day planning horizon")
        if self.outage_end_exclusive <= self.outage_start:
            raise ValueError("outage_end_exclusive must be later than outage_start")
        if (
            max(abs((d - self.as_of).days) for d in (self.outage_start, self.outage_end_exclusive))
            > 366
        ):
            raise ValueError("Outage boundaries must be within 366 days of as_of")
        return self


class DataIssue(BaseModel):
    entity_id: str
    code: str
    detail: str


class PartFact(BaseModel):
    id: str
    stock_on_hand: int | None
    requirement_edges: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class MaterialLine(BaseModel):
    product_id: str
    product_quantity: int
    units_per_product: int
    quantity: int
    evidence: EvidencePath


class PartDemand(BaseModel):
    part_id: str
    quantity: int
    lines: list[MaterialLine]


class OrderDemand(BaseModel):
    order_id: str
    deadline: date | None
    priority: int | None
    parts: list[PartDemand]
    issues: list[str] = Field(default_factory=list)


class OfferFact(BaseModel):
    id: str
    supplier_id: str
    part_id: str
    unit_cost: Money | None
    lead_days: int | None
    daily_capacity: int | None
    is_primary: bool | None
    issues: list[str] = Field(default_factory=list)


class ShipmentFact(BaseModel):
    id: str
    supplier_id: str
    part_id: str
    quantity: int
    dispatch_date: date
    expected_arrival_date: date
    status: Literal["PLANNED", "DISPATCHED", "CANCELLED"]
    evidence_refs: list[str]


class GraphSnapshot(BaseModel):
    fingerprint: str
    nodes: dict[str, EvidenceNode]
    relationships: dict[str, EvidenceRelationship]
    parts: dict[str, PartFact]
    orders: list[OrderDemand]
    offers: list[OfferFact]
    shipments: list[ShipmentFact]
    issues: list[DataIssue]
    global_supply_unknown: bool = False


class ArrivalCertificateCheck(BaseModel):
    certificate_id: str
    arrival_date: date
    status: Literal["valid", "expired", "missing", "unknown"]
    valid_until: date | None
    requirement_ref: str
    holding_ref: str | None


class Receipt(BaseModel):
    id: str
    supplier_id: str | None = None
    part_id: str
    quantity: int
    dispatch_date: date | None = None
    arrival_date: date
    original_arrival_date: date | None = None
    kind: Literal["initial_stock", "planned", "proposed"]
    reason_codes: list[str] = Field(default_factory=list)
    evidence_refs: list[str]
    unit_cost: Money | None = None
    estimated_additional_procurement_cost: Money = Decimal("0.00")
    certificate_checks: list[ArrivalCertificateCheck] = Field(default_factory=list)


class Allocation(BaseModel):
    receipt_id: str
    quantity: int
    arrival_date: date
    evidence_refs: list[str]


class PendingReceipt(BaseModel):
    receipt_id: str
    quantity: int
    arrival_date: date
    evidence_refs: list[str]


class MaterialResult(BaseModel):
    part_id: str
    required_quantity: int
    available_by_deadline: int | None
    allocated_quantity: int
    shortfall_quantity: int | None
    allocations: list[Allocation]
    late_receipts: list[PendingReceipt]
    reason_codes: list[str]


class OrderResult(BaseModel):
    order_id: str
    deadline: date | None
    priority: int | None
    status: Literal["on_time", "at_risk", "insufficient_data"]
    materials: list[MaterialResult]
    latest_arriving_input: date | None
    reason_codes: list[str]


class LotBalance(BaseModel):
    receipt_id: str
    part_id: str
    arrival_date: date
    received_quantity: int
    allocated_quantity: int
    remaining_quantity: int


class PlanResult(BaseModel):
    name: str
    on_time_orders: list[str]
    at_risk_orders: list[str]
    unresolved_orders: list[str]
    orders: list[OrderResult]
    receipts: list[Receipt]
    ledger: list[LotBalance]
    estimated_additional_procurement_cost: Money


class CandidateEvaluation(BaseModel):
    supplier_id: str
    part_id: str
    offer_ref: str
    status: Literal["eligible", "rejected", "insufficient_data"]
    unit_cost: Money | None
    lead_days: int | None
    daily_capacity: int | None
    earliest_dispatch_date: date | None
    earliest_arrival_date: date | None
    booked_dispatches: list[dict[str, str | int]]
    certificate_checks: list[ArrivalCertificateCheck]
    reason_codes: list[str]


class ShipmentTiming(BaseModel):
    shipment_id: str
    supplier_id: str
    part_id: str
    quantity: int
    status: Literal["PLANNED", "DISPATCHED", "CANCELLED"]
    original_dispatch_date: date
    original_arrival_date: date
    dispatch_date: date
    arrival_date: date
    included: bool
    reason_code: str


class MitigationPlanSummary(BaseModel):
    id: str
    restored_orders: list[str]
    additional_units: int
    unused_additional_units: int
    estimated_additional_procurement_cost: Money
    selected: bool = False
    reason_codes: list[str]


class ScenarioResponse(BaseModel):
    scenario_id: str
    snapshot_fingerprint: str
    request: ScenarioRequest
    assumptions: list[str]
    shipment_timing: list[ShipmentTiming]
    incomplete_data: bool
    data_issues: list[DataIssue]
    dependent_orders: list[str]
    dependency_paths: list[EvidencePath]
    order_demands: list[OrderDemand]
    baseline: PlanResult
    disrupted: PlanResult
    mitigated: PlanResult | None
    baseline_at_risk_orders: list[str]
    disrupted_at_risk_orders: list[str]
    newly_at_risk_orders: list[str]
    restored_orders: list[str]
    candidate_evaluations: list[CandidateEvaluation]
    mitigation_plans: list[MitigationPlanSummary]
    proposed_shipments: list[Receipt]
    estimated_additional_procurement_cost: Money
    evidence_nodes: dict[str, EvidenceNode]
    evidence_relationships: dict[str, EvidenceRelationship]
