"""Explicit test double for a model, not an application fallback/provider."""

import json


class ScriptedProvider:
    name = "mock-provider"

    def __init__(self, final_override=None, first_tool="trace_supplier_impact"):
        self.calls = 0
        self.final_override = final_override
        self.first_tool = first_tool
        self.observed = []

    async def complete(self, messages, tools):
        initial = json.loads(messages[0]["content"])
        scenario = initial["operator_scenario"]
        assert "approve" not in str([t["name"] for t in tools])
        results = [
            json.loads(m["output"]) for m in messages if m.get("type") == "function_call_output"
        ]
        self.observed = results
        self.calls += 1
        if self.calls == 1:
            return self.tool(self.first_tool, {"supplier_id": scenario["supplier_id"]})
        if self.calls == 2:
            assert results[-1]["data"]["total"] > 0
            return self.tool("simulate_supply_disruption", scenario)
        facts = next(r["data"] for r in results if "scenario_id" in r["data"])
        if self.calls == 3:
            receipt = facts["proposed_shipments"][0]
            return self.tool(
                "evaluate_part_alternatives",
                {
                    "part_id": receipt["part_id"],
                    "arrival_date": receipt["arrival_date"].split("T")[0],
                },
            )
        final = {
            "answer_kind": "scenario_summary",
            "scenario_id": facts["scenario_id"],
            "evidence_refs": [facts["proposed_shipments"][0]["evidence_refs"][0]],
        }
        if self.final_override:
            final.update(self.final_override)
        return [
            {"type": "message", "content": [{"type": "output_text", "text": json.dumps(final)}]}
        ]

    def tool(self, name, args):
        return [
            {
                "type": "function_call",
                "call_id": f"test_call_{self.calls}",
                "name": name,
                "arguments": json.dumps(args),
            }
        ]
