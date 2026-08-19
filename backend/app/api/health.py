import sqlite3

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import AUTH_DATABASE_PATH
from app.shared.config import settings


router = APIRouter(
    prefix="/api/v1",
    tags=["Health"],
)


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "running",
        "application": settings.app_name,
        "version": settings.app_version,
        "provider": settings.llm_provider,
        "model": settings.active_model,
        "phase": "Phase 10",
    }


@router.get("/ready")
def readiness():
    checks = {
        "database": False,
        "provider_configured": settings.llm_provider.lower() in {"ollama", "gemini"},
        "production_secrets": (
            settings.auth_secret_key != "change-this-secret-before-production"
            and settings.mcp_internal_key != "pragyaai-local-mcp-key"
        ),
    }
    try:
        connection = sqlite3.connect(AUTH_DATABASE_PATH)
        connection.execute("SELECT 1")
        connection.close()
        checks["database"] = True
    except sqlite3.Error:
        pass

    ready = checks["database"] and checks["provider_configured"]
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready", "checks": checks},
    )
