import itertools
from typing import Any

import httpx


class MCPError(RuntimeError):
    pass


class MCPClient:
    def __init__(self, name: str, url: str, timeout: float = 15.0) -> None:
        self.name = name
        self.url = url
        self.timeout = timeout
        self._request_ids = itertools.count(1)

    def list_tools(self) -> list[dict[str, Any]]:
        result = self._request("tools/list")
        return list(result.get("tools", []))

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
        )

    def _request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": next(self._request_ids),
            "method": method,
            "params": params or {},
        }

        try:
            response = httpx.post(
                self.url,
                json=payload,
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise MCPError(
                f"MCP server '{self.name}' is unavailable: {error}"
            ) from error

        if "error" in body:
            error = body["error"]
            message = error.get("message", "Unknown MCP error")
            raise MCPError(f"MCP server '{self.name}' returned: {message}")

        result = body.get("result")
        if not isinstance(result, dict):
            raise MCPError(f"MCP server '{self.name}' returned an invalid result")

        return result
