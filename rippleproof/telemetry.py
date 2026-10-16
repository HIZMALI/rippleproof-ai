"""Bounded run-local provider metadata. Never stores prompts, headers or bodies."""

import json
import re
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TokenUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_tokens: int | None = Field(default=None, ge=0, strict=True)
    output_tokens: int | None = Field(default=None, ge=0, strict=True)
    total_tokens: int | None = Field(default=None, ge=0, strict=True)


class ProviderRequestMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sequence: int = Field(ge=1, le=8)
    started_at: str
    duration_ms: float = Field(ge=0)
    transport: Literal["default", "injected"]
    http_status: int | None = Field(default=None, ge=100, le=599)
    request_id: str | None = None
    response_id: str | None = None
    model: str | None = None
    provider_status: (
        Literal["queued", "in_progress", "completed", "failed", "incomplete", "cancelled"] | None
    ) = None
    outcome: Literal[
        "completed",
        "rejected",
        "timeout",
        "network_error",
        "malformed_response",
        "response_too_large",
        "interrupted",
        "incomplete",
    ]
    # Local safe classification; no raw provider error string is retained.
    error_code: (
        Literal[
            "provider_authentication_failed",
            "provider_error",
            "model_timeout",
            "provider_unavailable",
            "invalid_model_output",
            "interrupted",
        ]
        | None
    ) = None
    usage: TokenUsage = Field(default_factory=TokenUsage)
    usage_consistent: bool | None = None
    redacted_fields: list[Literal["request_id", "response_id", "model"]] = Field(
        default_factory=list
    )


class ProviderTelemetry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requests: list[ProviderRequestMetadata] = Field(max_length=8)
    requests_recorded: int = Field(ge=0, le=8)
    usage_complete: bool
    # Complete totals are unavailable if any request has missing/invalid usage.
    usage: TokenUsage
    # Sums only values actually present, explicitly partial when incomplete.
    observed_usage: TokenUsage
    total_provider_duration_ms: float = Field(ge=0)


class TelemetryCollector:
    def __init__(self):
        self.requests: list[ProviderRequestMetadata] = []

    def record(self, **values):
        # Coordinator's existing eight-round hard maximum bounds this list.
        if len(self.requests) >= 8:
            raise RuntimeError("Provider telemetry exceeded the existing model-round bound")
        self.requests.append(ProviderRequestMetadata(sequence=len(self.requests) + 1, **values))

    def snapshot(self):
        complete = bool(self.requests) and all(r.usage_consistent is True for r in self.requests)
        observed = {}
        for field in TokenUsage.model_fields:
            values = [getattr(r.usage, field) for r in self.requests]
            present = [value for value in values if value is not None]
            observed[field] = sum(present) if present else None
        return ProviderTelemetry(
            requests=[r.model_copy(deep=True) for r in self.requests],
            requests_recorded=len(self.requests),
            usage_complete=complete,
            usage=TokenUsage(**observed) if complete else TokenUsage(),
            observed_usage=TokenUsage(**observed),
            total_provider_duration_ms=sum(r.duration_ms for r in self.requests),
        )


_CURRENT: ContextVar[TelemetryCollector | None] = ContextVar("provider_telemetry", default=None)


@contextmanager
def capture_telemetry(collector=None):
    collector = collector if collector is not None else TelemetryCollector()
    token = _CURRENT.set(collector)
    try:
        yield collector
    finally:
        _CURRENT.reset(token)


def current_collector():
    return _CURRENT.get()


def sensitive_values(messages, key):
    """Ephemeral comparison set; never added to records or public output."""
    values = {key} if key else set()

    def visit(value):
        if isinstance(value, str):
            if len(value) >= 6:
                values.add(value)
            if value[:1] in {"{", "["}:
                try:
                    visit(json.loads(value))
                except (ValueError, RecursionError):
                    pass
        elif isinstance(value, dict):
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(messages)
    return values


def safe_identifier(value, pattern, protected):
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        return None
    if re.search(r"bearer|sk-|ghp_|github_pat_|AKIA", value, re.IGNORECASE):
        return None
    if any(secret and secret in value for secret in protected):
        return None
    return value


def response_metadata(data, request_id, protected):
    """Allowlist exact fields only; unknown/invalid/redacted values stay null."""
    result, redacted = {}, []
    for field, value, pattern in [
        ("request_id", request_id, r"[A-Za-z0-9_-]{1,180}"),
        ("response_id", data.get("id"), r"resp_[A-Za-z0-9_-]{1,175}"),
        ("model", data.get("model"), r"[A-Za-z0-9][A-Za-z0-9._:-]{0,119}"),
    ]:
        result[field] = safe_identifier(value, pattern, protected)
        if value is not None and result[field] is None:
            redacted.append(field)
    result["redacted_fields"] = redacted
    status = data.get("status")
    result["provider_status"] = (
        status
        if status in {"queued", "in_progress", "completed", "failed", "incomplete", "cancelled"}
        else None
    )
    raw = data.get("usage")
    usage = {}
    for field in TokenUsage.model_fields:
        value = raw.get(field) if isinstance(raw, dict) else None
        usage[field] = value if type(value) is int and 0 <= value <= 10**12 else None
    result["usage"] = TokenUsage(**usage)
    result["usage_consistent"] = (
        usage["total_tokens"] == usage["input_tokens"] + usage["output_tokens"]
        if all(value is not None for value in usage.values())
        else None
    )
    return result
