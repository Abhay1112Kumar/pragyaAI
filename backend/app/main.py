from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.document_routes import router as document_router


app = FastAPI(
    title="PragyaAI API",
    description="Enterprise AI assistant backend",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(document_router)


@app.get("/")
async def root() -> dict:
    return {
        "name": "PragyaAI",
        "status": "running",
        "phase": 2,
    }


@app.get("/health")
async def health_check() -> dict:
    return {
        "status": "healthy",
    }