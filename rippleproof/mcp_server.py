"""Executable official MCP SDK server. stdout is reserved for JSON-RPC only."""

import anyio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool, ToolAnnotations

from rippleproof import __version__
from rippleproof.config import Settings
from rippleproof.repository import GraphRepository
from rippleproof.tool_models import ToolReply
from rippleproof.tools import REGISTRY, GraphTools


def build_server(settings=None):
    tools = GraphTools(GraphRepository(settings or Settings()))

    async def list_tools(context, params):
        return ListToolsResult(
            tools=[
                Tool(
                    name=name,
                    description=description,
                    input_schema=model.model_json_schema(),
                    output_schema=ToolReply.model_json_schema(),
                    annotations=ToolAnnotations(
                        read_only_hint=True,
                        destructive_hint=False,
                        idempotent_hint=True,
                        open_world_hint=False,
                    ),
                )
                for name, (model, description) in REGISTRY.items()
            ]
        )

    async def call_tool(context, params):
        reply = await anyio.to_thread.run_sync(tools.dispatch, params.name, params.arguments or {})
        return CallToolResult(
            content=[TextContent(type="text", text=reply.model_dump_json())],
            structured_content=reply.model_dump(mode="json"),
            is_error=reply.status == "error",
        )

    return Server(
        "rippleproof-graph", version=__version__, on_list_tools=list_tools, on_call_tool=call_tool
    )


async def main():
    server = build_server()
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    anyio.run(main)
