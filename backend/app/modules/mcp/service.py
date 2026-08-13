import json
import re
from dataclasses import dataclass
from typing import Any

from app.modules.mcp.client import MCPClient, MCPError
from app.shared.config import settings


TOOL_COMMAND_PATTERN = re.compile(
    r"^/tool\s+(?P<server>[A-Za-z0-9_-]+)\.(?P<tool>[A-Za-z0-9_-]+)"
    r"(?:\s+(?P<arguments>\{.*\}))?\s*$",
    re.DOTALL,
)


@dataclass(frozen=True)
class MCPToolCommand:
    server: str
    tool: str
    arguments: dict[str, Any]


class MCPService:
    def __init__(self) -> None:
        self._clients: dict[str, MCPClient] | None = None

    @property
    def clients(self) -> dict[str, MCPClient]:
        if self._clients is None:
            self._clients = {
                name: MCPClient(name=name, url=url)
                for name, url in settings.mcp_servers.items()
            }
        return self._clients

    def reset(self) -> None:
        self._clients = None

    def is_tool_command(self, message: str) -> bool:
        return message.lstrip().startswith("/tool")

    def parse_command(self, message: str) -> MCPToolCommand:
        match = TOOL_COMMAND_PATTERN.fullmatch(message.strip())
        if not match:
            raise MCPError(
                "Invalid tool command. Use: /tool server.tool {\"argument\": \"value\"}"
            )

        raw_arguments = match.group("arguments")
        try:
            arguments = json.loads(raw_arguments) if raw_arguments else {}
        except json.JSONDecodeError as error:
            raise MCPError(f"Tool arguments must be valid JSON: {error.msg}") from error

        if not isinstance(arguments, dict):
            raise MCPError("Tool arguments must be a JSON object")

        return MCPToolCommand(
            server=match.group("server"),
            tool=match.group("tool"),
            arguments=arguments,
        )

    def list_tools(self) -> list[dict[str, Any]]:
        tools = []
        for server_name, client in self.clients.items():
            for tool in client.list_tools():
                tools.append(
                    {
                        "server": server_name,
                        "name": tool.get("name"),
                        "description": tool.get("description"),
                        "input_schema": tool.get("inputSchema", {}),
                    }
                )
        return tools

    def execute(self, command: MCPToolCommand) -> dict[str, Any]:
        client = self.clients.get(command.server)
        if client is None:
            available = ", ".join(sorted(self.clients)) or "none configured"
            raise MCPError(
                f"Unknown MCP server '{command.server}'. Available servers: {available}"
            )
        return client.call_tool(command.tool, command.arguments)

    def execute_message(self, message: str) -> dict[str, Any]:
        return self.execute(self.parse_command(message))


mcp_service = MCPService()
