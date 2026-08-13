from fastapi import APIRouter, HTTPException, status

from app.modules.chat.schemas import ChatRequest, ChatResponse
from app.modules.chat.service import chat_service


router = APIRouter(
    prefix="/api/v1",
    tags=["Chat"],
)


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        result = chat_service.generate_response(
            message=request.message,
            conversation_id=request.conversation_id,
            document_id=request.document_id,
        )
        return ChatResponse(**result)

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to generate response: {error}",
        ) from error
