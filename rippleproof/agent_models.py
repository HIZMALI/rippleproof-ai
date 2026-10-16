"""Public agent contracts; no model chain-of-thought or unrestricted narratives."""

from typing import Literal

from pydantic import Field

from rippleproof.simulation.models import ScenarioRequest
from rippleproof.telemetry import ProviderTelemetry
from rippleproof.tool_models import EvidenceRef, ScenarioId, StrictInput


class AgentRequest(StrictInput):
    question: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    scenario: ScenarioRequest | None = None
    mode: Literal["guided", "agent"] = "guided"


class AgentLimits(StrictInput):
    max_model_requests: int = Field(ge=1, le=8)
    max_tool_calls: int = Field(ge=1, le=12)
    model_timeout_seconds: float = Field(gt=0, le=30)
    run_timeout_seconds: float = Field(ge=1, le=120)
    max_output_tokens_per_request: Literal[1200] = 1200
    max_accumulated_input_bytes: Literal[131072] = 131072


class AgentCapabilities(StrictInput):
    guided_available: Literal[True] = True
    agent_available: bool
    execution_kind: Literal["disabled", "controlled", "remote_provider"]
    provider: str | None = None
    model: str | None = None
    reason_code: Literal["provider_not_authorized", "provider_not_configured"] | None = None
    limits: AgentLimits


def capabilities(settings, *, controlled_provider=False):
    """Configuration only. Never constructs a provider or makes a network call.

    Controlled providers can only be injected by the Python application factory,
    never by an HTTP field, frontend flag or environment provider name.
    """
    authorized = settings.provider == "openai" and settings.allow_paid_calls
    configured = bool(settings.openai_api_key and settings.openai_model)
    available = controlled_provider or (authorized and configured)
    return AgentCapabilities(
        agent_available=available,
        execution_kind=(
            "controlled" if controlled_provider else "remote_provider" if available else "disabled"
        ),
        provider="controlled" if controlled_provider else "openai" if available else None,
        model=settings.openai_model if available and not controlled_provider else None,
        reason_code=(
            None
            if available
            else "provider_not_configured"
            if authorized
            else "provider_not_authorized"
        ),
        limits=AgentLimits(
            max_model_requests=settings.max_turns,
            max_tool_calls=settings.max_tool_calls,
            model_timeout_seconds=settings.model_timeout_s,
            run_timeout_seconds=settings.run_timeout_s,
        ),
    )


class FinalSelection(StrictInput):
    answer_kind: Literal["scenario_summary"]
    scenario_id: ScenarioId
    evidence_refs: list[EvidenceRef] = Field(min_length=1, max_length=12)


class ToolTrace(StrictInput):
    name: str
    arguments: dict
    started_at: str
    finished_at: str
    status: Literal["ok", "error"]
    evidence_refs: list[str]
    output_bytes: int
    output_sha256: str


class AgentResponse(StrictInput):
    mode: Literal["guided_walkthrough", "agent"]
    provider: str
    status: Literal["completed", "needs_input", "safe_fallback", "error"]
    response: str
    scenario_id: str | None = None
    facts: dict | None = None
    tool_trace: list[ToolTrace] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error_code: str | None = None
    model_requests: int = 0
    provider_telemetry: ProviderTelemetry | None = None
    http_status: int = Field(default=200, exclude=True)
