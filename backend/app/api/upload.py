"""File upload endpoint."""
from fastapi import APIRouter, UploadFile, File

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/file")
async def upload_file(file: UploadFile = File(...)) -> dict[str, str]:
    """Upload a file for processing."""
    return {"filename": file.filename, "status": "uploaded", "size": file.size}
