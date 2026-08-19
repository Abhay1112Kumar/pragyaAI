import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.dependencies import get_current_user
from app.modules.chat.service import ChatService
from app.modules.chat.streaming import emit_token


class Phase6StreamingTests(unittest.TestCase):
    def test_service_forwards_tokens_then_metadata_and_done(self) -> None:
        service = ChatService()

        def fake_generate_response(**_kwargs):
            emit_token("Hello")
            emit_token(" world")
            return {
                "response": "Hello world",
                "provider": "fake",
                "model": "fake-model",
                "conversation_id": "stream-thread",
                "route": "general",
                "sources": [],
            }

        with patch.object(
            service,
            "generate_response",
            side_effect=fake_generate_response,
        ):
            events = list(
                service.stream_response(
                    message="Hello",
                    conversation_id="stream-thread",
                )
            )

        self.assertEqual(
            [event for event, _data in events],
            ["token", "token", "metadata", "done"],
        )
        self.assertEqual(events[0][1]["content"], "Hello")
        self.assertEqual(events[1][1]["content"], " world")
        self.assertEqual(events[2][1]["route"], "general")
        self.assertNotIn("response", events[2][1])

    def test_service_falls_back_to_one_token_for_non_streaming_route(self) -> None:
        service = ChatService()
        result = {
            "response": "MCP result",
            "provider": "fake",
            "model": "fake-model",
            "conversation_id": "mcp-thread",
            "route": "mcp_tool",
            "sources": [],
        }

        with patch.object(
            service,
            "generate_response",
            return_value=result,
        ):
            events = list(
                service.stream_response(
                    message="/tool workspace.git_status {}",
                    conversation_id="mcp-thread",
                )
            )

        self.assertEqual(events[0], ("token", {"content": "MCP result"}))
        self.assertEqual(events[-1], ("done", {"status": "complete"}))

    def test_stream_endpoint_uses_sse_event_contract(self) -> None:
        client = TestClient(app)
        service_events = iter(
            [
                ("token", {"content": "Namaste "}),
                ("token", {"content": "Abhay"}),
                (
                    "metadata",
                    {
                        "provider": "fake",
                        "model": "fake-model",
                        "conversation_id": "api-thread",
                        "route": "general",
                        "sources": [],
                    },
                ),
                ("done", {"status": "complete"}),
            ]
        )

        app.dependency_overrides[get_current_user] = lambda: {
            "id": "test-user",
            "username": "tester",
            "role": "user",
            "is_active": True,
        }
        try:
            with patch(
                "app.api.chat.chat_service.stream_response",
                return_value=service_events,
            ):
                response = client.post(
                    "/api/v1/chat/stream",
                    json={
                        "message": "Hello",
                        "conversation_id": "api-thread",
                    },
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.headers["content-type"].startswith("text/event-stream")
        )
        self.assertIn("event: token", response.text)
        self.assertIn("event: metadata", response.text)
        self.assertIn("event: done", response.text)

        token_data = next(
            line.removeprefix("data: ")
            for line in response.text.splitlines()
            if line.startswith("data: ")
        )
        self.assertEqual(json.loads(token_data)["content"], "Namaste ")


if __name__ == "__main__":
    unittest.main()
