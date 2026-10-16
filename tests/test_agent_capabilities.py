"""Configuration/transport tests only: no remote network and no billable calls."""

import json

import pytest
from fastapi.testclient import TestClient

from rippleproof.agent_models import capabilities
from rippleproof.app import create_app
from rippleproof.config import Phase3Settings, Settings


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({}, "provider_not_authorized"),
        ({"provider": "openai"}, "provider_not_authorized"),
        ({"provider": "openai", "allow_paid_calls": True}, "provider_not_configured"),
    ],
)
def test_capability_is_closed_without_full_configuration(overrides, reason):
    result = capabilities(Phase3Settings(_env_file=None, **overrides))
    assert not result.agent_available
    assert result.reason_code == reason
    assert result.execution_kind == "disabled"
    assert result.guided_available


def test_capability_reports_bounds_without_constructing_provider(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Capability inspection must not construct/call a provider")

    monkeypatch.setattr("rippleproof.provider.OpenAIProvider.__init__", forbidden)
    settings = Phase3Settings(
        _env_file=None,
        provider="openai",
        allow_paid_calls=True,
        openai_api_key="synthetic-test-credential-not-real",
        openai_model="test-model",
        max_turns=2,
        max_tool_calls=3,
        run_timeout_s=30,
        model_timeout_s=5,
    )
    with TestClient(create_app(Settings(_env_file=None, port=1), settings)) as client:
        response = client.get("/api/agent/capabilities")
    assert response.status_code == 200  # Configuration works with no DB/network call.
    assert response.headers["Cache-Control"] == "no-store"
    data = response.json()
    assert data["agent_available"] and data["execution_kind"] == "remote_provider"
    assert data["limits"]["max_model_requests"] == 2
    assert data["limits"]["max_output_tokens_per_request"] == 1200
    assert "synthetic-test-credential-not-real" not in json.dumps(data)


def test_injected_provider_is_unambiguously_controlled():
    result = capabilities(Phase3Settings(_env_file=None), controlled_provider=True)
    assert result.agent_available
    assert result.execution_kind == "controlled" and result.provider == "controlled"
    assert result.model is None
