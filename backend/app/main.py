from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.document_routes import router as document_router
from app.api.health import router as health_router


app = FastAPI(
    title="PragyaAI API",
    description="Enterprise AI assistant backend",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, int | str]:
    return {
        "name": "PragyaAI",
        "status": "running",
        "version": "0.3.0",
        "phase": 3,
    }


app.include_router(document_router)
app.include_router(chat_router)
app.include_router(health_router)
