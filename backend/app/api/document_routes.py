from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.modules.auth.dependencies import get_current_user
from app.schemas.document_schema import (
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentUploadResponse,
    RetrievedChunk,
)
from app.services.document_service import document_service
from app.services.knowledge_graph_service import knowledge_graph_service
from app.services.vector_store_service import vector_store_service


router = APIRouter(
    prefix="/api/v1/documents",
    tags=["Documents"],
)


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=201,
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> DocumentUploadResponse:
    result = await document_service.save_and_extract_pdf(
        file,
        owner_id=current_user["id"],
    )

    try:
        chunk_count = vector_store_service.index_documents(
            result["documents"]
        )
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "The PDF was extracted, but embeddings could not be created. "
                "Make sure Ollama is running and the embedding model is installed. "
                f"Error: {error}"
            ),
        ) from error

    knowledge_graph_service.index_documents(result["documents"])
    return DocumentUploadResponse(
        message="Document uploaded, processed and indexed successfully",
        document_id=result["document_id"],
        filename=result["filename"],
        file_size=result["file_size"],
        page_count=result["page_count"],
        character_count=result["character_count"],
        chunk_count=chunk_count,
    )


@router.post(
    "/search",
    response_model=DocumentSearchResponse,
)
async def search_documents(
    request: DocumentSearchRequest,
    current_user: dict = Depends(get_current_user),
) -> DocumentSearchResponse:
    try:
        results = vector_store_service.search(
            query=request.query,
            limit=request.limit,
            document_id=request.document_id,
            owner_id=current_user["id"],
        )
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to search the vector database. "
                "Make sure Ollama is running. "
                f"Error: {error}"
            ),
        ) from error

    return DocumentSearchResponse(
        query=request.query,
        results=[
            RetrievedChunk(
                content=result["content"],
                metadata=result["metadata"],
                score=result["score"],
                retrieval_methods=result.get("retrieval_methods", []),
            )
            for result in results
        ],
    )


@router.get("/graph")
def query_document_graph(
    query: str,
    document_id: str | None = None,
    current_user: dict = Depends(get_current_user),
) -> dict:
    if not query.strip():
        raise HTTPException(status_code=400, detail="Graph query cannot be empty.")
    return knowledge_graph_service.query(
        query=query,
        document_id=document_id,
        owner_id=current_user["id"],
    )
