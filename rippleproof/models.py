"""Request contracts and typed, graph-backed response contracts."""

import re
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, JsonValue, StringConstraints

SupplierId = Annotated[str, StringConstraints(pattern=r"^S-[0-9]{2,5}$", max_length=7)]
PartId = Annotated[str, StringConstraints(pattern=r"^P-[0-9]{2,5}$", max_length=7)]


def strict_iso_date(value: object) -> date:
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Use an ISO calendar date in YYYY-MM-DD format")
    return date.fromisoformat(value)


ISODate = Annotated[date, BeforeValidator(strict_iso_date)]


class ImpactQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supplier_id: SupplierId


class AlternativesQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    part_id: PartId
    as_of: ISODate


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: Literal["ready", "unavailable"]
    database: Literal["ready", "unavailable"]
    graph: str
    graph_exists: bool | None


class GraphSummary(BaseModel):
    graph: str
    node_count: int = Field(ge=0)
    relationship_count: int = Field(ge=0)
    nodes_by_label: dict[str, int]
    relationships_by_type: dict[str, int]


class EvidenceNode(BaseModel):
    id: str
    label: str
    properties: dict[str, JsonValue]


class EvidenceRelationship(BaseModel):
    id: str
    type: str
    source_id: str
    target_id: str
    properties: dict[str, JsonValue]


class EvidencePath(BaseModel):
    nodes: list[EvidenceNode]
    relationships: list[EvidenceRelationship]
    human_readable: str


class ImpactPath(BaseModel):
    supplier_id: str
    part_id: str
    product_id: str
    order_id: str
    order_deadline: date
    order_quantity: int = Field(gt=0)
    units_per_product: int = Field(gt=0)
    part_units_required: int = Field(gt=0)
    evidence: EvidencePath


class ImpactResponse(BaseModel):
    supplier_id: str
    analysis_type: Literal["dependency_only"] = "dependency_only"
    interpretation: str = (
        "Open orders connected to this primary supplier. Dependency reachability does not "
        "predict lateness; stock allocation, outage duration and arrival dates are not evaluated."
    )
    order_ids: list[str]
    paths: list[ImpactPath]


class CertificateRequirement(BaseModel):
    certificate_id: str
    name: str
    certificate: EvidenceNode
    relationship: EvidenceRelationship


class CertificateCheck(BaseModel):
    certificate_id: str
    name: str
    status: Literal["valid", "expired", "missing"]
    valid_until: date | None
    requirement: EvidenceRelationship
    holding: EvidenceRelationship | None


class SupplyTerms(BaseModel):
    unit_cost: float = Field(ge=0)
    lead_days: int = Field(ge=0)
    daily_capacity: int = Field(ge=0)
    is_primary: bool


class AlternativeSupplier(BaseModel):
    supplier: EvidenceNode
    supply_terms: SupplyTerms
    supplies_relationship: EvidenceRelationship
    certifications_valid: bool
    certificate_checks: list[CertificateCheck]


class AlternativesResponse(BaseModel):
    part: EvidenceNode
    as_of: date
    interpretation: str = (
        "Non-primary suppliers offering this part, with modeled certificate checks only. "
        "This is not a purchase recommendation or a capacity/arrival feasibility assessment. "
        "Certificates are valid through valid_until, inclusive. Costs are synthetic units."
    )
    required_certificates: list[CertificateRequirement]
    candidates: list[AlternativeSupplier]
