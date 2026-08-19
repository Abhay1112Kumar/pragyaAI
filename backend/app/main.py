from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.middleware import ProductionHeadersMiddleware
from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.document_routes import router as document_router
from app.api.health import router as health_router
from app.api.mcp import router as mcp_router
from app.shared.config import settings


configured_origins = [
    origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()
]


app = FastAPI(
    title="PragyaAI API",
    description="Enterprise AI assistant backend",
    version="1.2.0",
)

app.add_middleware(ProductionHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins or [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"^http://(localhost|127\\.0\\.0\\.1):517[3-9]$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, int | str]:
    return {
        "name": "PragyaAI",
        "status": "running",
        "version": "1.2.0",
        "phase": 12,
    }


app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(document_router)
app.include_router(chat_router)
app.include_router(health_router)
if settings.enable_mcp:
    app.include_router(mcp_router)
