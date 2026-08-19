import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.store import UserStore
from app.modules.auth.tokens import TokenError, create_access_token, decode_access_token


class Phase8AuthenticationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = UserStore(":memory:")
        self.client = TestClient(app)
        self.store_patches = [
            patch("app.api.auth.user_store", self.store),
            patch("app.modules.auth.dependencies.user_store", self.store),
        ]
        for store_patch in self.store_patches:
            store_patch.start()
            self.addCleanup(store_patch.stop)
        self.addCleanup(self.store.close)

    def _register(self, username: str, password: str = "password123"):
        return self.client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": password},
        )

    def test_first_registration_is_admin_and_later_registration_is_user(self):
        first = self._register("first-admin")
        second = self._register("normal-user")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["user"]["role"], "admin")
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.json()["user"]["role"], "user")

    def test_local_password_reset_replaces_the_old_password(self):
        self.store.create_user("karn", "forgotten-password")

        user = self.store.reset_password("KARN", "new-password123")

        self.assertIsNone(self.store.authenticate("karn", "forgotten-password"))
        self.assertIsNotNone(self.store.authenticate("karn", "new-password123"))
        self.assertEqual(user["username"], "karn")
        with self.assertRaisesRegex(ValueError, "not found"):
            self.store.reset_password("missing-user", "new-password123")

    def test_local_vite_fallback_port_is_allowed_by_cors(self):
        response = self.client.options(
            "/api/v1/auth/register",
            headers={
                "Origin": "http://localhost:5174",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://localhost:5174",
        )

    def test_login_and_me_require_valid_bearer_token(self):
        self._register("abhay-user")
        login = self.client.post(
            "/api/v1/auth/login",
            json={"username": "abhay-user", "password": "password123"},
        )
        token = login.json()["access_token"]

        unauthenticated = self.client.get("/api/v1/auth/me")
        authenticated = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(authenticated.status_code, 200)
        self.assertEqual(authenticated.json()["username"], "abhay-user")

    def test_user_cannot_execute_mcp_tool_or_create_admin(self):
        self._register("admin-user")
        user = self._register("regular-user").json()
        user_headers = {"Authorization": f"Bearer {user['access_token']}"}

        tool_response = self.client.post(
            "/api/v1/chat",
            headers=user_headers,
            json={
                "message": "/tool workspace.git_status {}",
                "conversation_id": "rbac-thread",
            },
        )
        create_admin = self.client.post(
            "/api/v1/auth/users",
            headers=user_headers,
            json={
                "username": "forbidden-admin",
                "password": "password123",
                "role": "admin",
            },
        )

        self.assertEqual(tool_response.status_code, 403)
        self.assertEqual(create_admin.status_code, 403)

    def test_admin_can_create_another_admin(self):
        admin = self._register("bootstrap-admin").json()
        response = self.client.post(
            "/api/v1/auth/users",
            headers={"Authorization": f"Bearer {admin['access_token']}"},
            json={
                "username": "second-admin",
                "password": "password123",
                "role": "admin",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["role"], "admin")

    def test_document_search_is_scoped_to_authenticated_user(self):
        registered = self._register("document-user").json()
        user = registered["user"]

        with patch(
            "app.api.document_routes.vector_store_service.search",
            return_value=[],
        ) as search:
            response = self.client.post(
                "/api/v1/documents/search",
                headers={
                    "Authorization": f"Bearer {registered['access_token']}",
                },
                json={
                    "query": "secure document",
                    "document_id": "document-1",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(search.call_args.kwargs["owner_id"], user["id"])

    def test_tampered_token_is_rejected(self):
        user = self.store.create_user(
            username="token-user",
            password="password123",
        )
        token = create_access_token(user)
        payload = decode_access_token(token)

        self.assertEqual(payload["sub"], user["id"])
        header, payload_segment, signature = token.split(".")
        replacement = "A" if signature[0] != "A" else "B"
        tampered = (
            f"{header}.{payload_segment}.{replacement}{signature[1:]}"
        )
        with self.assertRaises(TokenError):
            decode_access_token(tampered)


if __name__ == "__main__":
    unittest.main()
