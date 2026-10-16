"""Fixed local stdio MCP client, used by the agent and smoke command."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import MCPError

from rippleproof.config import Settings
from rippleproof.errors import OperationError
from rippleproof.simulation.engine import scenario_identity
from rippleproof.tool_models import ScenarioToolData, ToolReply
from rippleproof.tools import MAX_TOOL_BYTES, REGISTRY

TRANSPORT_ERRORS = (
    MCPError,
    OSError,
    anyio.EndOfStream,
    anyio.BrokenResourceError,
    anyio.ClosedResourceError,
)


class GraphMCPClient:
    def __init__(self, session):
        self.session = session

    async def inventory(self):
        result = await self.session.list_tools()
        if {t.name for t in result.tools} != set(REGISTRY):
            raise OperationError(502, "invalid_mcp_registry", "Unexpected MCP tool inventory")
        return result.tools

    async def call(self, name, arguments):
        if name not in REGISTRY:
            raise OperationError(422, "unknown_tool", "Only graph read tools are allowed")
        arguments = REGISTRY[name][0].model_validate(arguments).model_dump(mode="json")
        result = await self.session.call_tool(name, arguments, read_timeout_seconds=12)
        data = result.structured_content
        if data is None:
            raise OperationError(
                502, "invalid_tool_output", "MCP response omitted structured output"
            )
        reply = ToolReply.model_validate(data)
        if len(reply.model_dump_json().encode()) > MAX_TOOL_BYTES:
            raise OperationError(502, "invalid_tool_output", "MCP output exceeded byte budget")
        if name == "simulate_supply_disruption" and reply.status == "ok":
            parsed = ScenarioToolData.model_validate(reply.data)
            if (
                parsed.request.model_dump(mode="json") != arguments
                or scenario_identity(parsed.operational_fingerprint, parsed.request)
                != parsed.scenario_id
            ):
                raise OperationError(
                    502, "invalid_tool_output", "MCP scenario does not match inputs"
                )
        return reply


@asynccontextmanager
async def connect_graph_tools(settings: Settings):
    # No shell, caller-supplied executable, approval token or model credential.
    env = {"FALKORDB_" + key.upper(): str(value) for key, value in settings.model_dump().items()}
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "rippleproof.mcp_server"],
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
    )
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=12) as session:
                await session.initialize()
                yield GraphMCPClient(session)
    except BaseExceptionGroup as exc:
        # AnyIO session/transport task groups wrap exceptions raised by the
        # consumer too. Preserve a single original failure (including cancellation)
        # so bounded coordinator errors and asyncio.timeout retain their meaning.
        leaf = exc
        while isinstance(leaf, BaseExceptionGroup) and len(leaf.exceptions) == 1:
            leaf = leaf.exceptions[0]
        if isinstance(leaf, TRANSPORT_ERRORS):
            raise OperationError(502, "mcp_transport_failed", "MCP transport failed") from None
        if not isinstance(leaf, BaseExceptionGroup):
            raise leaf from None
        raise OperationError(502, "mcp_transport_failed", "MCP transport failed") from None
    except TRANSPORT_ERRORS:
        raise OperationError(502, "mcp_transport_failed", "MCP transport failed") from None
