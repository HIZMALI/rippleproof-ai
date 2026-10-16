import json
import secrets
import socket

import anyio
import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient
from mcp.types import CallToolResult

from rippleproof.app import create_app
from rippleproof.config import Phase3Settings, Settings
from rippleproof.errors import OperationError
from rippleproof.mcp_client import GraphMCPClient
from rippleproof.provider import OpenAIProvider
from tests.integration.test_decisions import approve_body, prepare_body
from tests.simulation_helpers import request


def authorized_settings(**overrides):
    return Phase3Settings(
        _env_file=None,
        provider="openai",
        allow_paid_calls=True,
        openai_api_key="test-transport-not-a-real-key",
        openai_model="operator-configured-model",
        **overrides,
    )


@pytest.mark.parametrize(
    "configuration,code",
    [
        ({}, "provider_not_authorized"),
        (
            {"provider": "openai", "openai_api_key": "present", "openai_model": "model"},
            "provider_not_authorized",
        ),
        ({"provider": "openai", "allow_paid_calls": True}, "provider_not_configured"),
    ],
)
def test_remote_provider_requires_both_operator_opt_in_and_credentials(configuration, code):
    with TestClient(
        create_app(
            Settings(_env_file=None, port=1), Phase3Settings(_env_file=None, **configuration)
        )
    ) as client:
        response = client.post(
            "/api/agent/run",
            json={
                "mode": "agent",
                "question": "Explain the disruption",
                "scenario": request().model_dump(mode="json"),
            },
        )
    assert response.status_code == 503
    assert response.json()["error_code"] == code
    assert response.json()["model_requests"] == 0 and response.json()["tool_trace"] == []


def test_missing_scenario_and_long_question_rejected_without_invention():
    with TestClient(
        create_app(Settings(_env_file=None, port=1), Phase3Settings(_env_file=None))
    ) as client:
        response = client.post(
            "/api/agent/run", json={"question": "What if a supplier shuts down?"}
        )
        assert response.status_code == 200 and response.json()["status"] == "needs_input"
        assert response.json()["scenario_id"] is None and not response.json()["tool_trace"]
        for question in ("x" * 2001, "   ", ""):
            assert client.post("/api/agent/run", json={"question": question}).status_code == 422


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "provider_authentication_failed"),
        (403, "provider_authentication_failed"),
        (429, "provider_error"),
    ],
)
def test_real_provider_protocol_with_controlled_http_transport_errors(status, code):
    async def handler(req):
        assert str(req.url) == "https://api.openai.com/v1/responses"
        return httpx.Response(status, json={"error": "secret provider details must not leak"})

    async def check():
        provider = OpenAIProvider(authorized_settings(), transport=httpx.MockTransport(handler))
        with pytest.raises(OperationError) as error:
            await provider.complete([], [])
        assert error.value.code == code
        assert "secret" not in error.value.message

    anyio.run(check)


def test_real_provider_protocol_payload_and_function_call_parsing():
    async def handler(req):
        body = json.loads(req.content)
        assert body["store"] is False and body["max_output_tokens"] == 1200
        assert body["text"]["format"]["strict"] is True
        assert body["model"] == "operator-configured-model"
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "function_call",
                        "name": "graph_summary",
                        "arguments": "{}",
                        "call_id": "call_1",
                    }
                ],
            },
        )

    async def check():
        provider = OpenAIProvider(authorized_settings(), transport=httpx.MockTransport(handler))
        result = await provider.complete([{"role": "user", "content": "question"}], [])
        assert result[0]["name"] == "graph_summary"

    anyio.run(check)


@pytest.mark.parametrize(
    "failure,code",
    [
        ("timeout", "model_timeout"),
        ("malformed", "invalid_model_output"),
        ("large", "invalid_model_output"),
    ],
)
def test_model_timeouts_and_invalid_output_fail_safely(failure, code):
    async def handler(req):
        if failure == "timeout":
            raise httpx.ReadTimeout("test timeout", request=req)
        return httpx.Response(200, content=b"not JSON" if failure == "malformed" else b"x" * 65537)

    async def check():
        provider = OpenAIProvider(authorized_settings(), transport=httpx.MockTransport(handler))
        with pytest.raises(OperationError) as error:
            await provider.complete([], [])
        assert error.value.code == code

    anyio.run(check)


def test_new_flows_return_503_on_actual_refused_database_connection():
    token = secrets.token_urlsafe(32)
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        graph = Settings(
            _env_file=None,
            host="127.0.0.1",
            port=reserved.getsockname()[1],
            connect_timeout_s=0.1,
            socket_timeout_s=0.1,
        )
        phase3 = Phase3Settings(_env_file=None, approval_secret=token)
        with TestClient(create_app(graph, phase3)) as client:
            preview_stub = {
                "scenario": request().model_dump(mode="json"),
                "mitigation_plan_id": "cost_first",
                "scenario_id": "SC-" + "0" * 20,
                "operational_fingerprint": "0" * 64,
                "plan_revision": "0" * 64,
            }
            for path, body, headers in [
                ("/api/decisions/prepare", prepare_body(), {}),
                (
                    "/api/decisions/approve",
                    approve_body(preview_stub),
                    {"Authorization": "Bearer " + token},
                ),
                (
                    "/api/agent/run",
                    {
                        "question": "Assess this outage",
                        "mode": "guided",
                        "scenario": request().model_dump(mode="json"),
                    },
                    {},
                ),
            ]:
                response = client.post(path, json=body, headers=headers)
                assert response.status_code == 503, response.text
            assert client.get("/api/decisions/D-" + "0" * 24).status_code == 503
            assert client.get("/api/decisions").status_code == 503


def test_malformed_mcp_structured_result_rejected_by_client():
    class BadSession:
        async def call_tool(self, *args, **kwargs):
            return CallToolResult(
                content=[], structured_content={"status": "ok", "data": {"cost": "invented"}}
            )

    async def check():
        with pytest.raises(ValueError):
            await GraphMCPClient(BadSession()).call(
                "simulate_supply_disruption", request().model_dump(mode="json")
            )

    anyio.run(check)
