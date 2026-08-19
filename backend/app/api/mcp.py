from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.dependencies import (
    require_roles,
    verify_internal_mcp_key,
)
from app.modules.mcp.client import MCPError
from app.modules.mcp.service import mcp_service
from app.modules.mcp.server import workspace_mcp_server


router = APIRouter(prefix="/api/v1/mcp", tags=["MCP"])


@router.post("/protocol")
def mcp_protocol(
    request: dict[str, Any],
    _verified: None = Depends(verify_internal_mcp_key),
) -> dict[str, Any] | None:
    return workspace_mcp_server.handle_jsonrpc(request)


@router.get("/tools")
def list_mcp_tools(
    _admin: dict = Depends(require_roles("admin")),
) -> dict[str, list[dict[str, Any]]]:
    try:
        return {"tools": mcp_service.list_tools()}
    except MCPError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
