from fastapi import APIRouter

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
        "phase": "Phase 3",
    }
