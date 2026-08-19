import json
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

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


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post(
    "/chat/stream",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
)
def stream_chat(request: ChatRequest) -> StreamingResponse:
    def event_stream() -> Iterator[str]:
        try:
            for event, data in chat_service.stream_response(
                message=request.message,
                conversation_id=request.conversation_id,
                document_id=request.document_id,
            ):
                yield _format_sse(event, data)
        except Exception as error:
            yield _format_sse(
                "error",
                {"detail": f"Unable to generate response: {error}"},
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
