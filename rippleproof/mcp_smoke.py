"""Real SDK client/server smoke test. No provider requests or writes."""

import json
from datetime import UTC, datetime

import anyio

from rippleproof.config import Settings
from rippleproof.mcp_client import connect_graph_tools


async def main():
    async with connect_graph_tools(Settings()) as client:
        inventory = await client.inventory()
        print(json.dumps({"transport": "stdio", "tools": [t.name for t in inventory]}))
        calls = [
            ("graph_summary", {}),
            ("trace_supplier_impact", {"supplier_id": "S-04", "limit": 2}),
            ("evaluate_part_alternatives", {"part_id": "P-22", "arrival_date": "2026-10-18"}),
            (
                "simulate_supply_disruption",
                {
                    "supplier_id": "S-04",
                    "as_of": "2026-10-15",
                    "outage_start": "2026-10-16",
                    "outage_end_exclusive": "2026-10-24",
                },
            ),
            ("get_decision_history", {}),
        ]
        fingerprint = None
        for name, arguments in calls:
            result = await client.call(name, arguments)
            assert result.status == "ok", result.model_dump_json()
            fingerprint = result.data.get("operational_fingerprint", fingerprint)
            print(
                json.dumps(
                    {
                        "at": datetime.now(UTC).isoformat(),
                        "tool": name,
                        "arguments": arguments,
                        "result": result.model_dump(mode="json"),
                    }
                )
            )
        args = {"ref": "SUPPLIES:S-04:P-22", "expected_fingerprint": fingerprint}
        result = await client.call("resolve_evidence", args)
        assert result.status == "ok", result.model_dump_json()
        print(
            json.dumps(
                {
                    "tool": "resolve_evidence",
                    "arguments": args,
                    "result": result.model_dump(mode="json"),
                }
            )
        )


if __name__ == "__main__":
    anyio.run(main)
