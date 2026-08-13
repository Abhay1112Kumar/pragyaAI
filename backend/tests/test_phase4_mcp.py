import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app.modules.graph.chat_graph import PragyaChatGraph
from app.modules.mcp.client import MCPClient, MCPError
from app.modules.mcp.service import MCPService
from app.modules.mcp.server import WorkspaceMCPServer


class Phase4MCPTests(unittest.TestCase):
    def test_parse_valid_tool_command(self) -> None:
        command = MCPService().parse_command(
            '/tool github.search_code {"query": "LangGraph"}'
        )

        self.assertEqual(command.server, "github")
        self.assertEqual(command.tool, "search_code")
        self.assertEqual(command.arguments, {"query": "LangGraph"})

    def test_invalid_arguments_are_rejected(self) -> None:
        with self.assertRaises(MCPError):
            MCPService().parse_command("/tool local.echo {invalid}")

    def test_client_sends_mcp_tools_call_request(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": "done"}]},
        }

        with patch("app.modules.mcp.client.httpx.post", return_value=response) as post:
            result = MCPClient("local", "http://localhost:9000/mcp").call_tool(
                "echo",
                {"message": "hello"},
            )

        self.assertEqual(result["content"][0]["text"], "done")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["method"], "tools/call")
        self.assertEqual(payload["params"]["name"], "echo")

    def test_configured_servers_are_exposed(self) -> None:
        with patch.dict(
            os.environ,
            {"MCP_SERVERS_JSON": json.dumps({"local": "http://localhost:9000/mcp"})},
        ):
            service = MCPService()
            self.assertIn("local", service.clients)

    def test_tool_command_uses_mcp_graph_route(self) -> None:
        graph = PragyaChatGraph()
        tool_result = {"content": [{"type": "text", "text": "42"}]}

        with patch(
            "app.modules.graph.chat_graph.mcp_service.execute_message",
            return_value=tool_result,
        ) as execute:
            result = graph.invoke(
                query='/tool local.calculate {"expression": "6 * 7"}',
                conversation_id="tool-thread",
            )

        self.assertEqual(result["route"], "mcp_tool")
        self.assertIn("42", result["answer"])
        self.assertEqual(result["sources"], [])
        execute.assert_called_once()

    def test_workspace_server_lists_and_reads_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "hello.txt").write_text("hello PragyaAI", encoding="utf-8")
            server = WorkspaceMCPServer(root)

            listed = server.call_tool("list_files", {})
            read = server.call_tool("read_file", {"file": "hello.txt"})

        self.assertIn("hello.txt", listed["content"][0]["text"])
        self.assertEqual(read["content"][0]["text"], "hello PragyaAI")

    def test_workspace_server_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            server = WorkspaceMCPServer(Path(directory))
            with self.assertRaises(ValueError):
                server.call_tool("read_file", {"file": "../secret.txt"})

    def test_workspace_server_exposes_mcp_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            server = WorkspaceMCPServer(Path(directory))
            response = server.handle_jsonrpc(
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
            )

        tool_names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            tool_names,
            {"list_files", "read_file", "search_code", "git_status"},
        )


if __name__ == "__main__":
    unittest.main()
