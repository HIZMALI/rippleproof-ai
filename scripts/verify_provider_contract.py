"""Offline documented-contract check and clearly labeled mocked metadata example.

No key lookup, default HTTP transport, graph connection or acceptance run.
Writes new artifacts exclusively. See docs/SECURITY.md for provider evidence categories.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import anyio  # noqa: E402
import httpx2 as httpx  # noqa: E402
from jsonschema import Draft202012Validator  # noqa: E402

from rippleproof.config import Phase3Settings  # noqa: E402
from rippleproof.provider import OpenAIProvider, final_selection_schema  # noqa: E402
from rippleproof.telemetry import capture_telemetry  # noqa: E402
from rippleproof.tools import REGISTRY  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    blocked = []

    def guard(event, values):
        if event == "socket.getaddrinfo":
            host = values[0]
        elif event == "socket.connect":
            host = values[1][0] if isinstance(values[1], tuple) else "non-network-socket"
        else:
            return
        # Windows event-loop plumbing may use loopback sockets; no remote socket allowed.
        if host not in {"127.0.0.1", "localhost", "::1", "non-network-socket"}:
            blocked.append(event)
            raise RuntimeError("Remote network is forbidden during offline contract verification")

    sys.addaudithook(guard)
    schemas = {name: model.model_json_schema() for name, (model, _) in REGISTRY.items()}
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
    final = final_selection_schema()
    Draft202012Validator.check_schema(final)
    assert final["additionalProperties"] is False
    assert set(final["required"]) == set(final["properties"])
    assert final["properties"]["answer_kind"]["enum"] == ["scenario_summary"]
    calls = []

    async def check():
        async def handler(request):
            payload = json.loads(request.content)
            assert payload["model"] == "gpt-6-luna"
            assert payload["include"] == ["reasoning.encrypted_content"]
            assert payload["store"] is False and payload["max_output_tokens"] == 1200
            assert payload["parallel_tool_calls"] is False
            assert payload["text"]["format"]["schema"] == final
            assert all(tool["strict"] is False for tool in payload["tools"])
            calls.append(len(calls) + 1)
            data = {
                "id": f"resp_controlled_fixture_{len(calls)}",
                "model": "gpt-6-luna",
                "status": "completed",
                "output": [],
            }
            if len(calls) == 1:
                data["usage"] = {"input_tokens": 17, "output_tokens": 5, "total_tokens": 22}
            return httpx.Response(
                200, json=data, headers={"x-request-id": f"req_controlled_fixture_{len(calls)}"}
            )

        settings = Phase3Settings(
            _env_file=None,
            provider="openai",
            allow_paid_calls=True,
            openai_api_key="fixture-only-not-a-real-key",
            openai_model="gpt-6-luna",
        )
        provider = OpenAIProvider(settings, transport=httpx.MockTransport(handler))
        tools = [
            {
                "type": "function",
                "name": name,
                "description": "Offline schema check",
                "parameters": schema,
                "strict": False,
            }
            for name, schema in schemas.items()
        ]
        with capture_telemetry() as collector:
            await provider.complete([], tools)
            await provider.complete([], tools)
        return collector.snapshot().model_dump(mode="json")

    example = anyio.run(check)
    report = {
        "evidence_kind": "MOCKED HTTP TRANSPORT ONLY; NOT A REMOTE PROVIDER TRACE",
        "remote_provider_requests": 0,
        "blocked_remote_network_attempts": len(blocked),
        "documented_request_shape_checks_passed": True,
        "exact_model_checked": "gpt-6-luna",
        "account_access_or_remote_acceptance_verified": False,
        "tool_schemas_checked": list(schemas),
        "strict_final_wire_schema": final,
        "sanitized_mocked_metadata_example": example,
        "note": "Missing usage in request two intentionally leaves complete totals null.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2)
        output.write("\n")
    print(
        json.dumps(
            {
                key: value
                for key, value in report.items()
                if key not in {"strict_final_wire_schema", "sanitized_mocked_metadata_example"}
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
