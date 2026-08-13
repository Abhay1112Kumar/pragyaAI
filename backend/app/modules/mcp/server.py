import subprocess
from pathlib import Path
from typing import Any, Callable


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
MAX_READ_CHARACTERS = 100_000
MAX_SEARCH_RESULTS = 100


class WorkspaceToolError(ValueError):
    pass


class WorkspaceMCPServer:
    def __init__(self, workspace_root: Path = WORKSPACE_ROOT) -> None:
        self.workspace_root = workspace_root.resolve()
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "list_files": self._list_files,
            "read_file": self._read_file,
            "search_code": self._search_code,
            "git_status": self._git_status,
        }

    def tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "list_files",
                "description": "List files and folders inside the PragyaAI workspace.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"directory": {"type": "string", "default": "."}},
                    "additionalProperties": False,
                },
            },
            {
                "name": "read_file",
                "description": "Read a UTF-8 text file inside the PragyaAI workspace.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"file": {"type": "string"}},
                    "required": ["file"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "search_code",
                "description": "Search text in repository files.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "git_status",
                "description": "Show the PragyaAI repository git status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            },
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        handler = self._handlers.get(name)
        if handler is None:
            raise WorkspaceToolError(f"Unknown workspace tool: {name}")

        result = handler(arguments)
        return {
            "content": [{"type": "text", "text": self._to_text(result)}],
            "structuredContent": {"result": result},
            "isError": False,
        }

    def handle_jsonrpc(self, request: dict[str, Any]) -> dict[str, Any] | None:
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "notifications/initialized":
            return None

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "pragyaai-workspace", "version": "0.4.0"},
                }
            elif method == "tools/list":
                result = {"tools": self.tool_definitions()}
            elif method == "tools/call":
                result = self.call_tool(
                    str(params.get("name", "")),
                    params.get("arguments", {}),
                )
            else:
                return self._error(request_id, -32601, f"Method not found: {method}")
        except (WorkspaceToolError, OSError) as error:
            return self._error(request_id, -32602, str(error))

        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self.workspace_root / relative_path).resolve()
        try:
            candidate.relative_to(self.workspace_root)
        except ValueError as error:
            raise WorkspaceToolError("Path must stay inside the PragyaAI workspace") from error
        return candidate

    def _list_files(self, arguments: dict[str, Any]) -> list[dict[str, str]]:
        directory = self._resolve(str(arguments.get("directory", ".")))
        if not directory.is_dir():
            raise WorkspaceToolError(f"Directory not found: {arguments.get('directory')}")

        return [
            {"name": path.name, "type": "directory" if path.is_dir() else "file"}
            for path in sorted(directory.iterdir(), key=lambda item: item.name.lower())
            if path.name not in {".git", "venv", "node_modules", "__pycache__"}
        ]

    def _read_file(self, arguments: dict[str, Any]) -> str:
        relative_path = arguments.get("file")
        if not isinstance(relative_path, str) or not relative_path:
            raise WorkspaceToolError("'file' is required")

        path = self._resolve(relative_path)
        if not path.is_file():
            raise WorkspaceToolError(f"File not found: {relative_path}")

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise WorkspaceToolError("Only UTF-8 text files can be read") from error

        if len(content) > MAX_READ_CHARACTERS:
            return content[:MAX_READ_CHARACTERS] + "\n[output truncated]"
        return content

    def _search_code(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        query = arguments.get("query")
        if not isinstance(query, str) or not query:
            raise WorkspaceToolError("'query' is required")

        results = []
        ignored = {".git", "venv", "node_modules", "__pycache__"}
        for path in self.workspace_root.rglob("*"):
            if not path.is_file() or any(part in ignored for part in path.parts):
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for line_number, line in enumerate(lines, start=1):
                if query.lower() in line.lower():
                    results.append(
                        {
                            "file": str(path.relative_to(self.workspace_root)),
                            "line": line_number,
                            "text": line.strip(),
                        }
                    )
                    if len(results) >= MAX_SEARCH_RESULTS:
                        return results
        return results

    def _git_status(self, arguments: dict[str, Any]) -> str:
        completed = subprocess.run(
            ["git", "status", "--short"],
            cwd=self.workspace_root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if completed.returncode != 0:
            raise WorkspaceToolError(completed.stderr.strip() or "git status failed")
        return completed.stdout.strip() or "Working tree clean."

    def _to_text(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        import json
        return json.dumps(value, indent=2, ensure_ascii=False)

    def _error(self, request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }


workspace_mcp_server = WorkspaceMCPServer()
