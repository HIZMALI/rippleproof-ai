"""Only in-memory transports; no provider network or real credentials."""

import asyncio
import json

import anyio
import httpx2 as httpx
import pytest
from jsonschema import Draft202012Validator

from rippleproof.errors import OperationError
from rippleproof.provider import OpenAIProvider, final_selection_schema
from rippleproof.telemetry import TelemetryCollector, capture_telemetry, current_collector
from tests.test_agent_provider import authorized_settings


def body(**overrides):
    return {
        "id": "resp_mock_fixture_1",
        "model": "gpt-6-luna",
        "status": "completed",
        "usage": {"input_tokens": 17, "output_tokens": 5, "total_tokens": 22},
        "output": [],
        **overrides,
    }


def test_payload_gpt6_luna_and_documented_strict_schema_without_network():
    captured = []

    async def handler(req):
        payload = json.loads(req.content)
        captured.append(payload)
        assert payload["model"] == "gpt-6-luna"
        assert payload["include"] == ["reasoning.encrypted_content"]
        assert payload["parallel_tool_calls"] is False
        assert payload["max_output_tokens"] == 1200 and payload["store"] is False
        assert payload["text"]["format"]["strict"] is True
        schema = payload["text"]["format"]["schema"]
        Draft202012Validator.check_schema(schema)
        assert set(schema["required"]) == set(schema["properties"])
        assert schema["additionalProperties"] is False
        assert schema["properties"]["answer_kind"]["enum"] == ["scenario_summary"]
        assert "const" not in json.dumps(schema)
        return httpx.Response(200, json=body(), headers={"x-request-id": "req_mock_1"})

    async def check():
        provider = OpenAIProvider(
            authorized_settings().model_copy(update={"openai_model": "gpt-6-luna"}),
            transport=httpx.MockTransport(handler),
        )
        with capture_telemetry() as collector:
            assert await provider.complete([], []) == []
        result = collector.snapshot()
        assert result.usage_complete
        assert result.usage.model_dump() == body()["usage"]
        request = result.requests[0]
        assert request.response_id == "resp_mock_fixture_1"
        assert request.request_id == "req_mock_1" and request.model == "gpt-6-luna"
        assert request.outcome == "completed" and request.http_status == 200
        assert request.duration_ms >= 0 and request.transport == "injected"
        assert current_collector() is None

    anyio.run(check)
    assert len(captured) == 1


@pytest.mark.parametrize(
    "usage",
    [
        None,
        {},
        {"input_tokens": 17},
        {"input_tokens": True},
        {"input_tokens": -1},
        {"output_tokens": "5"},
        {"input_tokens": 17, "output_tokens": 5, "total_tokens": 99},
    ],
)
def test_missing_invalid_or_inconsistent_usage_is_not_fabricated(usage):
    async def check():
        provider = OpenAIProvider(
            authorized_settings(),
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body(usage=usage))),
        )
        with capture_telemetry() as collector:
            await provider.complete([], [])
        result = collector.snapshot()
        assert not result.usage_complete
        assert result.usage.total_tokens is None
        assert result.requests[0].usage.input_tokens == (
            usage.get("input_tokens")
            if isinstance(usage, dict)
            and type(usage.get("input_tokens")) is int
            and usage["input_tokens"] >= 0
            else None
        )

    anyio.run(check)


@pytest.mark.parametrize(
    "failure",
    [
        "401",
        "403",
        "429",
        "network",
        "timeout",
        "json",
        "array",
        "oversized",
        "incomplete",
        "cancel",
    ],
)
def test_failure_metadata_is_finalized_and_sanitized(failure):
    async def handler(req):
        if failure == "network":
            raise httpx.ConnectError("Bearer do-not-publish raw exception", request=req)
        if failure == "timeout":
            raise httpx.ReadTimeout("private timeout body", request=req)
        if failure == "cancel":
            raise asyncio.CancelledError()
        if failure.isdecimal():
            return httpx.Response(
                int(failure),
                json={"error": {"message": "private raw body"}},
                headers={"x-request-id": "req_rejected_fixture"},
            )
        if failure == "oversized":
            return httpx.Response(200, content=b"x" * 65537)
        if failure == "json":
            return httpx.Response(200, content=b"not json private raw body")
        return httpx.Response(200, json=[] if failure == "array" else body(status="incomplete"))

    async def check():
        provider = OpenAIProvider(authorized_settings(), transport=httpx.MockTransport(handler))
        with capture_telemetry() as collector:
            with pytest.raises(asyncio.CancelledError if failure == "cancel" else OperationError):
                await provider.complete([], [])
        record = collector.snapshot().requests[0]
        expected = {
            "network": "network_error",
            "timeout": "timeout",
            "json": "malformed_response",
            "array": "malformed_response",
            "oversized": "response_too_large",
            "incomplete": "incomplete",
            "cancel": "interrupted",
        }.get(failure, "rejected")
        assert record.outcome == expected
        assert record.error_code is not None
        encoded = collector.snapshot().model_dump_json()
        assert "private" not in encoded and "Bearer" not in encoded
        if failure.isdecimal():
            assert record.http_status == int(failure)
            assert record.request_id == "req_rejected_fixture"
            assert record.usage.total_tokens is None

    anyio.run(check)


def test_sensitive_ids_model_error_body_and_request_contents_are_never_exported():
    secret = "test-transport-not-a-real-key"
    request_secret = "private_fixture_password"

    async def check():
        provider = OpenAIProvider(
            authorized_settings(),
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    json=body(
                        id="resp_" + secret,
                        model=request_secret,
                        error={"message": "Bearer " + secret},
                        extra_private=request_secret,
                    ),
                    headers={"x-request-id": "req_" + request_secret, "authorization": secret},
                )
            ),
        )
        messages = [{"role": "user", "content": json.dumps({"password": request_secret})}]
        with capture_telemetry() as collector:
            await provider.complete(messages, [])
        encoded = collector.snapshot().model_dump_json()
        assert secret not in encoded and request_secret not in encoded and "Bearer" not in encoded
        assert collector.requests[0].model is None
        assert set(collector.requests[0].redacted_fields) == {"request_id", "response_id", "model"}

    anyio.run(check)


def test_aggregation_partial_failure_and_context_concurrency_are_run_local():
    async def run_one(label, fail):
        count = 0

        async def handler(req):
            nonlocal count
            count += 1
            await asyncio.sleep(0)
            if fail and count == 2:
                raise httpx.ReadTimeout("never logged", request=req)
            return httpx.Response(200, json=body(id="resp_" + label))

        provider = OpenAIProvider(authorized_settings(), transport=httpx.MockTransport(handler))
        with capture_telemetry() as collector:
            await provider.complete([], [])
            try:
                await provider.complete([], [])
            except OperationError:
                assert fail
        return collector.snapshot()

    async def check():
        good, partial = await asyncio.gather(
            run_one("fixture_A", False), run_one("fixture_B", True)
        )
        assert good.usage.input_tokens == 34 and good.usage.total_tokens == 44
        assert good.usage_complete and good.requests_recorded == 2
        assert not partial.usage_complete and partial.usage.total_tokens is None
        assert partial.observed_usage.total_tokens == 22
        assert all(r.response_id == "resp_fixture_A" for r in good.requests)
        assert partial.requests[0].response_id == "resp_fixture_B"

    anyio.run(check)


def test_schema_rejects_extra_facts_and_collector_snapshot_is_a_copy():
    schema = final_selection_schema()
    assert schema["properties"]["evidence_refs"]["maxItems"] == 12
    assert TelemetryCollector().snapshot().observed_usage.total_tokens is None
    validator = Draft202012Validator(schema)
    example = {
        "answer_kind": "scenario_summary",
        "scenario_id": "SC-" + "0" * 20,
        "evidence_refs": ["SCHEMA_TEST_ONLY"],
    }
    validator.validate(example)
    assert not validator.is_valid({**example, "cost": "fabricated"})

    async def check():
        provider = OpenAIProvider(
            authorized_settings(),
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body())),
        )
        with capture_telemetry() as collector:
            await provider.complete([], [])
        snapshot = collector.snapshot()
        snapshot.requests[0].model = "modified-copy"
        assert collector.snapshot().requests[0].model == "gpt-6-luna"

    anyio.run(check)


@pytest.mark.parametrize("interrupt", [False, True])
def test_interrupted_body_preserves_only_observed_headers(interrupt):
    class InterruptedStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'{"id":"untrusted_partial_body"'
            if interrupt:
                raise asyncio.CancelledError()
            raise httpx.ReadError("private network contents")

    async def check():
        provider = OpenAIProvider(
            authorized_settings(),
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    200, stream=InterruptedStream(), headers={"x-request-id": "req_partial_fixture"}
                )
            ),
        )
        with capture_telemetry() as collector:
            with pytest.raises(asyncio.CancelledError if interrupt else OperationError):
                await provider.complete([], [])
        record = collector.snapshot().requests[0]
        assert record.http_status == 200 and record.request_id == "req_partial_fixture"
        assert record.response_id is None and record.usage.total_tokens is None
        assert "private" not in collector.snapshot().model_dump_json()

    anyio.run(check)
