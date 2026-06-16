import asyncio
import io
import json
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError


class FakeFaceApiClient:
    def __init__(self, delete_error=None):
        self.registered = []
        self.deleted = []
        self.delete_error = delete_error
        self.login_response = {
            "authenticated": True,
            "match": {"user_id": 100001, "username": "GAOFEI"},
            "quality_metrics": {"det_score": 0.99},
            "elapsed_ms": 12.3,
        }

    def register_face(self, payload):
        self.registered.append(payload)
        return {
            "id": f"face-{len(self.registered)}",
            "user_id": payload["user_id"],
            "username": payload["username"],
            "message": "注册成功",
            "quality_metrics": {"det_score": 0.98},
        }

    def delete_face(self, face_id):
        if self.delete_error:
            raise self.delete_error
        self.deleted.append(face_id)
        return {"ok": True}

    def create_liveness_challenge(self, payload):
        return {"challenge_id": "challenge-1", "status": "pending", "action": "blink"}

    def submit_liveness_challenge(self, payload):
        return {"passed": True, "reason": "活体通过", "result_reason": "ok"}

    def face_login(self, payload):
        return self.login_response


class SimpleResponse:
    def __init__(self, status_code, body, headers=None):
        self.status_code = status_code
        self.text = body.decode("utf-8") if isinstance(body, bytes) else str(body)
        self.headers = headers or {}

    def json(self):
        return json.loads(self.text or "{}")


def request(app, method, path, json_body=None, params=None, headers=None):
    query_string = ""
    if params:
        from urllib.parse import urlencode

        query_string = urlencode(params)
    body = b""
    request_headers = []
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        request_headers.append((b"content-type", b"application/json"))
    for key, value in (headers or {}).items():
        request_headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": query_string.encode("ascii"),
        "headers": request_headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    messages = []

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        messages.append(message)

    asyncio.run(app(scope, receive, send))
    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    response_headers = {}
    for message in messages:
        if message["type"] == "http.response.start":
            response_headers = {
                key.decode("latin-1"): value.decode("latin-1")
                for key, value in message.get("headers", [])
            }
    response_body = b"".join(
        message.get("body", b"") for message in messages if message["type"] == "http.response.body"
    )
    return SimpleResponse(status, response_body, response_headers)


def make_test_app(db_path, fake_client=None, **settings_overrides):
    from business_demo.app import BusinessDemoSettings, create_app

    settings = BusinessDemoSettings(
        db_path=str(db_path),
        face_api_base_url="http://face-api.test",
        face_api_key="server-secret",
        token_secret="test-secret",
        **settings_overrides,
    )
    return create_app(settings=settings, face_api_client=fake_client or FakeFaceApiClient())


class BusinessDemoStorageTests(unittest.TestCase):
    def test_storage_seeds_users_and_enforces_single_active_binding(self):
        from business_demo.app import BusinessDemoError
        from business_demo.storage import BusinessDB

        with tempfile.TemporaryDirectory() as tmp:
            db = BusinessDB(Path(tmp) / "business.db")

            users = db.list_users()
            self.assertGreaterEqual(len(users), 3)
            self.assertTrue(any(user["user_id"] == "100001" for user in users))

            db.add_user("200001", "tester", display_name="Tester", department="QA")
            binding = db.create_binding("200001", "face-a", source="web_demo")
            self.assertEqual(binding["face_id"], "face-a")
            self.assertTrue(db.list_users(status="active")[-1]["face_bound"])

            with self.assertRaises(BusinessDemoError) as ctx:
                db.create_binding("200001", "face-b", source="web_demo")
            self.assertEqual(ctx.exception.code, "FACE_ALREADY_BOUND")

            removed = db.remove_binding("200001")
            self.assertEqual(removed["face_id"], "face-a")
            self.assertIsNone(db.get_active_binding("200001"))

    def test_storage_enforces_unique_active_binding_and_terminal_event_id(self):
        from business_demo.storage import BusinessDB, utc_now

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "business.db"
            db = BusinessDB(db_path)
            active = db.create_binding("100001", "face-a", source="web_demo")

            conn = sqlite3.connect(db_path)
            try:
                with self.assertRaises(sqlite3.IntegrityError):
                    conn.execute(
                        """
                        INSERT INTO face_bindings
                        (id, user_id, face_id, bind_status, bound_at, source, metadata_json)
                        VALUES (?, ?, ?, 'active', ?, ?, '{}')
                        """,
                        ("manual-active", active["user_id"], "face-b", utc_now(), "test"),
                    )
                conn.rollback()
            finally:
                conn.close()

            db.add_audit(
                terminal_event_id="event-unique-1",
                user_id="100001",
                terminal_id="gate-1",
                source="terminal",
                success=True,
            )
            with self.assertRaises(sqlite3.IntegrityError):
                db.add_audit(
                    terminal_event_id="event-unique-1",
                    user_id="100001",
                    terminal_id="gate-1",
                    source="terminal",
                    success=True,
                )

    def test_storage_migrates_old_audit_table_before_creating_event_index(self):
        from business_demo.storage import BusinessDB

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "business.db"
            conn = sqlite3.connect(db_path)
            try:
                conn.executescript(
                    """
                    CREATE TABLE business_users (
                        user_id TEXT PRIMARY KEY,
                        username TEXT NOT NULL,
                        display_name TEXT,
                        department TEXT,
                        status TEXT NOT NULL DEFAULT 'active',
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE face_bindings (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        face_id TEXT NOT NULL,
                        bind_status TEXT NOT NULL,
                        bound_at TEXT NOT NULL,
                        removed_at TEXT,
                        source TEXT NOT NULL,
                        metadata_json TEXT NOT NULL DEFAULT '{}'
                    );

                    CREATE TABLE business_login_audits (
                        id TEXT PRIMARY KEY,
                        user_id TEXT,
                        terminal_id TEXT,
                        source TEXT NOT NULL,
                        success INTEGER NOT NULL,
                        failure_reason TEXT,
                        face_similarity REAL,
                        face_liveness_status TEXT,
                        face_liveness_reason TEXT,
                        issued_token_id TEXT,
                        state TEXT,
                        created_at TEXT NOT NULL
                    );
                    """
                )
                conn.commit()
            finally:
                conn.close()

            db = BusinessDB(db_path)
            db.add_audit(
                terminal_event_id="migrated-event-1",
                user_id="100001",
                terminal_id="gate-1",
                source="terminal",
                success=True,
            )

            conn = sqlite3.connect(db_path)
            try:
                columns = {row[1] for row in conn.execute("PRAGMA table_info(business_login_audits)")}
                indexes = {row[1] for row in conn.execute("PRAGMA index_list(business_login_audits)")}
            finally:
                conn.close()

            self.assertIn("terminal_event_id", columns)
            self.assertIn("idx_business_login_audits_terminal_event", indexes)

    def test_storage_migrates_duplicate_rows_before_creating_unique_indexes(self):
        from business_demo.storage import BusinessDB

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "business.db"
            conn = sqlite3.connect(db_path)
            try:
                conn.executescript(
                    """
                    CREATE TABLE business_users (
                        user_id TEXT PRIMARY KEY,
                        username TEXT NOT NULL,
                        display_name TEXT,
                        department TEXT,
                        status TEXT NOT NULL DEFAULT 'active',
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE face_bindings (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        face_id TEXT NOT NULL,
                        bind_status TEXT NOT NULL,
                        bound_at TEXT NOT NULL,
                        removed_at TEXT,
                        source TEXT NOT NULL,
                        metadata_json TEXT NOT NULL DEFAULT '{}'
                    );

                    CREATE TABLE business_login_audits (
                        id TEXT PRIMARY KEY,
                        terminal_event_id TEXT,
                        user_id TEXT,
                        terminal_id TEXT,
                        source TEXT NOT NULL,
                        success INTEGER NOT NULL,
                        failure_reason TEXT,
                        face_similarity REAL,
                        face_liveness_status TEXT,
                        face_liveness_reason TEXT,
                        issued_token_id TEXT,
                        state TEXT,
                        created_at TEXT NOT NULL
                    );

                    INSERT INTO face_bindings
                    (id, user_id, face_id, bind_status, bound_at, source, metadata_json)
                    VALUES
                    ('binding-old', '100001', 'face-old', 'active', '2026-01-01 00:00:00', 'test', '{}'),
                    ('binding-new', '100001', 'face-new', 'active', '2026-01-02 00:00:00', 'test', '{}');

                    INSERT INTO business_login_audits
                    (id, terminal_event_id, user_id, terminal_id, source, success, created_at)
                    VALUES
                    ('audit-old', 'event-dup', '100001', 'gate-1', 'terminal', 1, '2026-01-01 00:00:00'),
                    ('audit-new', 'event-dup', '100001', 'gate-1', 'terminal', 1, '2026-01-02 00:00:00');
                    """
                )
                conn.commit()
            finally:
                conn.close()

            db = BusinessDB(db_path)
            active = db.get_active_binding("100001")
            event = db.get_audit_by_terminal_event_id("event-dup")

            conn = sqlite3.connect(db_path)
            try:
                active_count = conn.execute(
                    "SELECT COUNT(*) FROM face_bindings WHERE user_id = '100001' AND bind_status = 'active'"
                ).fetchone()[0]
                event_count = conn.execute(
                    "SELECT COUNT(*) FROM business_login_audits WHERE terminal_event_id = 'event-dup'"
                ).fetchone()[0]
            finally:
                conn.close()

            self.assertEqual(active["face_id"], "face-new")
            self.assertEqual(event["id"], "audit-new")
            self.assertEqual(active_count, 1)
            self.assertEqual(event_count, 1)

    def test_replace_binding_rolls_back_when_new_binding_cannot_be_created(self):
        from business_demo.storage import BusinessDB

        with tempfile.TemporaryDirectory() as tmp:
            db = BusinessDB(Path(tmp) / "business.db")
            db.create_binding("100001", "face-a", source="web_demo")

            with self.assertRaises(TypeError):
                db.replace_binding("100001", "face-b", source="web_demo", metadata={"bad": object()})

            active = db.get_active_binding("100001")
            self.assertEqual(active["face_id"], "face-a")

    def test_demo_token_round_trip_and_tamper_rejection(self):
        from business_demo.app import issue_demo_token, verify_demo_token

        token = issue_demo_token({"user_id": "100001", "username": "GAOFEI"}, "secret", ttl_seconds=60)
        payload = verify_demo_token(token, "secret")

        self.assertEqual(payload["user_id"], "100001")
        with self.assertRaises(Exception):
            verify_demo_token(token + "tamper", "secret")


class BusinessDemoSettingsTests(unittest.TestCase):
    def test_load_settings_rejects_default_token_secret_in_production(self):
        from business_demo.app import load_settings

        with mock.patch.dict(os.environ, {"BUSINESS_DEMO_ENV": "production"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "BUSINESS_DEMO_TOKEN_SECRET"):
                load_settings()

    def test_load_settings_rejects_empty_token_secret_in_production(self):
        from business_demo.app import load_settings

        with mock.patch.dict(
            os.environ,
            {"BUSINESS_DEMO_ENV": "production", "BUSINESS_DEMO_TOKEN_SECRET": "   "},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "BUSINESS_DEMO_TOKEN_SECRET"):
                load_settings()


class BusinessDemoFaceApiClientTests(unittest.TestCase):
    def test_face_api_client_maps_http_detail_reason(self):
        from business_demo.app import BusinessDemoError
        from business_demo.face_api_client import FaceApiClient, request as urllib_request

        body = json.dumps(
            {
                "detail": {
                    "code": "NO_FACE",
                    "message": "没有检测到人脸",
                    "reason": "图片中没有检测到可用于识别的人脸",
                }
            },
            ensure_ascii=False,
        ).encode("utf-8")
        http_error = HTTPError("http://face-api.test/search", 400, "Bad Request", {}, io.BytesIO(body))

        with mock.patch.object(urllib_request, "urlopen", side_effect=http_error):
            with self.assertRaises(BusinessDemoError) as ctx:
                FaceApiClient("http://face-api.test", "secret").face_login({"image": "x"})

        self.assertEqual(ctx.exception.code, "NO_FACE")
        self.assertEqual(ctx.exception.reason, "图片中没有检测到可用于识别的人脸")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_face_api_client_maps_auth_and_unavailable_errors(self):
        from business_demo.app import BusinessDemoError
        from business_demo.face_api_client import FaceApiClient, request as urllib_request

        auth_error = HTTPError("http://face-api.test/search", 401, "Unauthorized", {}, io.BytesIO(b"{}"))
        with mock.patch.object(urllib_request, "urlopen", side_effect=auth_error):
            with self.assertRaises(BusinessDemoError) as auth_ctx:
                FaceApiClient("http://face-api.test", "bad").face_login({"image": "x"})
        self.assertEqual(auth_ctx.exception.code, "FACE_API_AUTH_FAILED")

        with mock.patch.object(urllib_request, "urlopen", side_effect=OSError("connection refused")):
            with self.assertRaises(BusinessDemoError) as unavailable_ctx:
                FaceApiClient("http://face-api.test", "secret").face_login({"image": "x"})
        self.assertEqual(unavailable_ctx.exception.code, "FACE_API_UNAVAILABLE")

    def test_face_api_client_preserves_string_detail_http_errors(self):
        from business_demo.app import BusinessDemoError
        from business_demo.face_api_client import FaceApiClient, request as urllib_request

        body = json.dumps({"detail": "图片中没有检测到人脸"}, ensure_ascii=False).encode("utf-8")
        http_error = HTTPError("http://face-api.test/search", 400, "Bad Request", {}, io.BytesIO(body))

        with mock.patch.object(urllib_request, "urlopen", side_effect=http_error):
            with self.assertRaises(BusinessDemoError) as ctx:
                FaceApiClient("http://face-api.test", "secret").face_login({"image": "x"})

        self.assertEqual(ctx.exception.code, "FACE_API_REQUEST_FAILED")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("图片中没有检测到人脸", ctx.exception.reason)


class BusinessDemoApiTests(unittest.TestCase):
    def test_user_binding_unbinding_and_replace_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = FakeFaceApiClient()
            app = make_test_app(Path(tmp) / "business.db", fake)

            created = request(
                app,
                "POST",
                "/api/users",
                {"user_id": "200001", "username": "tester", "display_name": "Tester"},
            )
            self.assertEqual(created.status_code, 200, created.text)

            bound = request(
                app,
                "POST",
                "/api/users/200001/face-binding",
                {"image": "data:image/jpeg;base64,aaa", "terminal_id": "web-1"},
            )
            self.assertEqual(bound.status_code, 200, bound.text)
            self.assertEqual(bound.json()["binding"]["face_id"], "face-1")
            self.assertEqual(fake.registered[0]["metadata"]["source"], "business-demo")

            duplicate = request(
                app,
                "POST",
                "/api/users/200001/face-binding",
                {"image": "data:image/jpeg;base64,bbb", "terminal_id": "web-1"},
            )
            self.assertEqual(duplicate.status_code, 409)
            self.assertEqual(duplicate.json()["detail"]["code"], "FACE_ALREADY_BOUND")

            replaced = request(
                app,
                "POST",
                "/api/users/200001/face-binding/replace",
                {"image": "data:image/jpeg;base64,ccc", "terminal_id": "web-1"},
            )
            self.assertEqual(replaced.status_code, 200, replaced.text)
            self.assertEqual(replaced.json()["old_face_id"], "face-1")
            self.assertEqual(replaced.json()["binding"]["face_id"], "face-2")
            self.assertIn("face-1", fake.deleted)

            removed = request(app, "DELETE", "/api/users/200001/face-binding", params={"confirm": "true"})
            self.assertEqual(removed.status_code, 200, removed.text)
            self.assertEqual(removed.json()["removed_face_id"], "face-2")

    def test_unbind_and_replace_record_pending_cleanup_when_delete_fails(self):
        from business_demo.errors import BusinessDemoError

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "business.db"
            fake = FakeFaceApiClient(
                delete_error=BusinessDemoError(
                    "FACE_API_UNAVAILABLE",
                    "人脸识别服务不可用",
                    "人脸识别服务不可用，请检查 face_api 是否启动",
                    status_code=503,
                )
            )
            app = make_test_app(db_path, fake)
            request(
                app,
                "POST",
                "/api/users/100001/face-binding",
                {"image": "data:image/jpeg;base64,aaa", "terminal_id": "web-1"},
            )

            replaced = request(
                app,
                "POST",
                "/api/users/100001/face-binding/replace",
                {"image": "data:image/jpeg;base64,bbb", "terminal_id": "web-1"},
            )
            self.assertEqual(replaced.status_code, 200, replaced.text)
            self.assertEqual(replaced.json()["old_face_cleanup_status"], "pending_cleanup")

            removed = request(app, "DELETE", "/api/users/100001/face-binding", params={"confirm": "true"})
            self.assertEqual(removed.status_code, 200, removed.text)
            self.assertEqual(removed.json()["cleanup_status"], "pending_cleanup")

            conn = sqlite3.connect(db_path)
            try:
                rows = conn.execute(
                    "SELECT face_id, bind_status FROM face_bindings WHERE user_id = ? ORDER BY face_id",
                    ("100001",),
                ).fetchall()
            finally:
                conn.close()
            self.assertEqual(
                dict(rows),
                {
                    "face-1": "pending_cleanup",
                    "face-2": "pending_cleanup",
                },
            )

    def test_binding_liveness_configuration_requires_challenge(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_test_app(
                Path(tmp) / "business.db",
                FakeFaceApiClient(),
                binding_liveness_required=True,
            )

            response = request(
                app,
                "POST",
                "/api/users/100001/face-binding",
                {"image": "data:image/jpeg;base64,aaa", "terminal_id": "web-1"},
            )

            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["detail"]["code"], "LIVENESS_CHALLENGE_REQUIRED")

    def test_request_validation_errors_use_business_error_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_test_app(Path(tmp) / "business.db", FakeFaceApiClient())

            response = request(app, "POST", "/api/users", {"user_id": "200002"})

            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json()["detail"]["code"], "VALIDATION_ERROR")
            self.assertIn("请求参数", response.json()["detail"]["reason"])

    def test_terminal_event_requires_id_and_recognition_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_test_app(Path(tmp) / "business.db", FakeFaceApiClient())
            request(
                app,
                "POST",
                "/api/users/100001/face-binding",
                {"image": "data:image/jpeg;base64,aaa", "terminal_id": "web-1"},
            )

            missing_event_id = request(
                app,
                "POST",
                "/api/terminal/login-events",
                {
                    "terminal_id": "gate-1",
                    "matched_user_id": "100001",
                    "similarity": 0.91,
                    "recognized_at_epoch": time.time(),
                    "face_api_result": {"authenticated": True},
                },
            )
            self.assertEqual(missing_event_id.status_code, 422)
            self.assertEqual(missing_event_id.json()["detail"]["code"], "VALIDATION_ERROR")

            missing_recognized_at = request(
                app,
                "POST",
                "/api/terminal/login-events",
                {
                    "event_id": "terminal-event-missing-time",
                    "terminal_id": "gate-1",
                    "matched_user_id": "100001",
                    "similarity": 0.91,
                    "face_api_result": {"authenticated": True},
                },
            )
            self.assertEqual(missing_recognized_at.status_code, 422)
            self.assertEqual(missing_recognized_at.json()["detail"]["code"], "VALIDATION_ERROR")

    def test_web_login_issues_token_and_records_business_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = FakeFaceApiClient()
            app = make_test_app(Path(tmp) / "business.db", fake)
            request(
                app,
                "POST",
                "/api/users/100001/face-binding",
                {"image": "data:image/jpeg;base64,aaa", "terminal_id": "web-1"},
            )

            challenge = request(
                app,
                "POST",
                "/api/auth/liveness/challenge",
                {"purpose": "login", "terminal_id": "web-1"},
            )
            self.assertEqual(challenge.status_code, 200, challenge.text)
            submitted = request(
                app,
                "POST",
                "/api/auth/liveness/submit",
                {"challenge_id": "challenge-1", "terminal_id": "web-1", "frames": ["a", "b"]},
            )
            self.assertTrue(submitted.json()["passed"])

            login = request(
                app,
                "POST",
                "/api/auth/face-login",
                {
                    "image": "data:image/jpeg;base64,login",
                    "terminal_id": "web-1",
                    "challenge_id": "challenge-1",
                    "state": "trace-1",
                },
            )

            self.assertEqual(login.status_code, 200, login.text)
            body = login.json()
            self.assertTrue(body["authenticated"])
            self.assertEqual(body["user"]["user_id"], "100001")
            self.assertTrue(body["token"])

            me = request(app, "GET", "/api/auth/me", headers={"Authorization": f"Bearer {body['token']}"})
            self.assertEqual(me.status_code, 200, me.text)
            self.assertEqual(me.json()["user"]["user_id"], "100001")

            audit = request(app, "GET", "/api/audit/login", params={"terminal_id": "web-1"})
            self.assertEqual(audit.status_code, 200, audit.text)
            self.assertEqual(audit.json()["count"], 1)
            self.assertTrue(audit.json()["items"][0]["success"])
            token_signature_prefix = body["token"].split(".", 1)[1][:12]
            issued_token_id = audit.json()["items"][0]["issued_token_id"]
            self.assertNotEqual(issued_token_id, token_signature_prefix)
            self.assertEqual(len(issued_token_id), 32)

    def test_web_login_rejects_disabled_or_unbound_business_user(self):
        from business_demo.storage import BusinessDB

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "business.db"
            fake = FakeFaceApiClient()
            app = make_test_app(db_path, fake)

            disabled_db = BusinessDB(db_path)
            disabled_db.update_user_status("100001", "disabled")
            response = request(
                app,
                "POST",
                "/api/auth/face-login",
                {
                    "image": "data:image/jpeg;base64,login",
                    "terminal_id": "web-1",
                    "challenge_id": "challenge-1",
                },
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["detail"]["code"], "USER_DISABLED")

            disabled_db.update_user_status("100001", "active")
            response = request(
                app,
                "POST",
                "/api/auth/face-login",
                {
                    "image": "data:image/jpeg;base64,login",
                    "terminal_id": "web-1",
                    "challenge_id": "challenge-1",
                },
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["detail"]["code"], "FACE_NOT_BOUND")

    def test_web_login_rejects_unauthenticated_or_mismatched_face_api_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = FakeFaceApiClient()
            app = make_test_app(Path(tmp) / "business.db", fake)
            request(
                app,
                "POST",
                "/api/users/100001/face-binding",
                {"image": "data:image/jpeg;base64,aaa", "terminal_id": "web-1"},
            )

            fake.login_response = {
                "authenticated": False,
                "match": {"user_id": 100001, "username": "GAOFEI"},
                "similarity": 0.91,
            }
            rejected = request(
                app,
                "POST",
                "/api/auth/face-login",
                {
                    "image": "data:image/jpeg;base64,login",
                    "terminal_id": "web-1",
                    "challenge_id": "challenge-1",
                },
            )
            self.assertEqual(rejected.status_code, 403)
            self.assertEqual(rejected.json()["detail"]["code"], "FACE_API_LOGIN_REJECTED")

            fake.login_response = {
                "authenticated": True,
                "match": {"user_id": 100001, "username": "GAOFEI", "face_id": "other-face"},
                "similarity": 0.91,
            }
            mismatched = request(
                app,
                "POST",
                "/api/auth/face-login",
                {
                    "image": "data:image/jpeg;base64,login",
                    "terminal_id": "web-1",
                    "challenge_id": "challenge-1",
                },
            )
            self.assertEqual(mismatched.status_code, 403)
            self.assertEqual(mismatched.json()["detail"]["code"], "FACE_API_MATCH_MISMATCH")

    def test_terminal_event_reports_business_decision_and_audit(self):
        from business_demo.storage import BusinessDB

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "business.db"
            app = make_test_app(db_path, FakeFaceApiClient())
            request(
                app,
                "POST",
                "/api/users/100001/face-binding",
                {"image": "data:image/jpeg;base64,aaa", "terminal_id": "web-1"},
            )

            accepted = request(
                app,
                "POST",
                "/api/terminal/login-events",
                {
                    "event_id": "terminal-event-1",
                    "terminal_id": "gate-1",
                    "matched_user_id": "100001",
                    "similarity": 0.91,
                    "recognized_at_epoch": time.time(),
                    "state": "trace-terminal",
                    "face_api_result": {
                        "authenticated": True,
                        "match": {"user_id": 100001, "username": "GAOFEI"},
                    },
                },
            )
            self.assertEqual(accepted.status_code, 200, accepted.text)
            self.assertTrue(accepted.json()["accepted"])

            db = BusinessDB(db_path)
            db.update_user_status("100001", "disabled")
            rejected = request(
                app,
                "POST",
                "/api/terminal/login-events",
                {
                    "event_id": "terminal-event-2",
                    "terminal_id": "gate-1",
                    "matched_user_id": "100001",
                    "similarity": 0.88,
                    "recognized_at_epoch": time.time(),
                    "face_api_result": {
                        "authenticated": True,
                        "match": {"user_id": 100001, "username": "GAOFEI"},
                    },
                },
            )
            self.assertEqual(rejected.status_code, 200, rejected.text)
            self.assertFalse(rejected.json()["accepted"])
            self.assertEqual(rejected.json()["failure_reason"], "USER_DISABLED")

            audit = request(app, "GET", "/api/audit/login", params={"terminal_id": "gate-1"})
            self.assertEqual(audit.json()["count"], 2)

    def test_terminal_event_rejects_untrusted_face_api_result_and_future_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_test_app(Path(tmp) / "business.db", FakeFaceApiClient())
            request(
                app,
                "POST",
                "/api/users/100001/face-binding",
                {"image": "data:image/jpeg;base64,aaa", "terminal_id": "web-1"},
            )

            unauthenticated = request(
                app,
                "POST",
                "/api/terminal/login-events",
                {
                    "event_id": "terminal-event-unauthenticated",
                    "terminal_id": "gate-1",
                    "matched_user_id": "100001",
                    "similarity": 0.91,
                    "recognized_at_epoch": time.time(),
                    "face_api_result": {
                        "authenticated": False,
                        "match": {"user_id": 100001, "username": "GAOFEI"},
                    },
                },
            )
            self.assertEqual(unauthenticated.status_code, 200)
            self.assertFalse(unauthenticated.json()["accepted"])
            self.assertEqual(unauthenticated.json()["failure_reason"], "FACE_API_LOGIN_REJECTED")

            mismatched_user = request(
                app,
                "POST",
                "/api/terminal/login-events",
                {
                    "event_id": "terminal-event-mismatch",
                    "terminal_id": "gate-1",
                    "matched_user_id": "100001",
                    "similarity": 0.91,
                    "recognized_at_epoch": time.time(),
                    "face_api_result": {
                        "authenticated": True,
                        "match": {"user_id": 100002, "username": "DEMO_ADMIN"},
                    },
                },
            )
            self.assertFalse(mismatched_user.json()["accepted"])
            self.assertEqual(mismatched_user.json()["failure_reason"], "FACE_API_MATCH_MISMATCH")

            future = request(
                app,
                "POST",
                "/api/terminal/login-events",
                {
                    "event_id": "terminal-event-future",
                    "terminal_id": "gate-1",
                    "matched_user_id": "100001",
                    "similarity": 0.91,
                    "recognized_at_epoch": time.time() + 3600,
                    "face_api_result": {
                        "authenticated": True,
                        "match": {"user_id": 100001, "username": "GAOFEI"},
                    },
                },
            )
            self.assertFalse(future.json()["accepted"])
            self.assertEqual(future.json()["failure_reason"], "TERMINAL_EVENT_TIME_INVALID")

            invalid_result_with_future_time = request(
                app,
                "POST",
                "/api/terminal/login-events",
                {
                    "event_id": "terminal-event-invalid-result-future",
                    "terminal_id": "gate-1",
                    "matched_user_id": "100001",
                    "similarity": 0.91,
                    "recognized_at_epoch": time.time() + 3600,
                    "face_api_result": {},
                },
            )
            self.assertFalse(invalid_result_with_future_time.json()["accepted"])
            self.assertEqual(
                invalid_result_with_future_time.json()["failure_reason"],
                "FACE_API_LOGIN_REJECTED",
            )

    def test_terminal_event_rejects_unbound_expired_and_duplicate_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "business.db"
            app = make_test_app(db_path, FakeFaceApiClient())

            unbound = request(
                app,
                "POST",
                "/api/terminal/login-events",
                {
                    "event_id": "terminal-event-unbound",
                    "terminal_id": "gate-2",
                    "matched_user_id": "100001",
                    "similarity": 0.91,
                    "recognized_at_epoch": time.time(),
                    "face_api_result": {
                        "authenticated": True,
                        "match": {"user_id": 100001, "username": "GAOFEI"},
                    },
                },
            )
            self.assertEqual(unbound.status_code, 200, unbound.text)
            self.assertFalse(unbound.json()["accepted"])
            self.assertEqual(unbound.json()["failure_reason"], "FACE_NOT_BOUND")

            request(
                app,
                "POST",
                "/api/users/100001/face-binding",
                {"image": "data:image/jpeg;base64,aaa", "terminal_id": "web-1"},
            )
            expired = request(
                app,
                "POST",
                "/api/terminal/login-events",
                {
                    "event_id": "terminal-event-expired",
                    "terminal_id": "gate-2",
                    "matched_user_id": "100001",
                    "similarity": 0.91,
                    "recognized_at_epoch": time.time() - 999,
                    "face_api_result": {
                        "authenticated": True,
                        "match": {"user_id": 100001, "username": "GAOFEI"},
                    },
                },
            )
            self.assertFalse(expired.json()["accepted"])
            self.assertEqual(expired.json()["failure_reason"], "TERMINAL_EVENT_EXPIRED")

            accepted = request(
                app,
                "POST",
                "/api/terminal/login-events",
                {
                    "event_id": "terminal-event-ok",
                    "terminal_id": "gate-2",
                    "matched_user_id": "100001",
                    "similarity": 0.91,
                    "recognized_at_epoch": time.time(),
                    "face_api_result": {
                        "authenticated": True,
                        "match": {"user_id": 100001, "username": "GAOFEI"},
                    },
                },
            )
            self.assertTrue(accepted.json()["accepted"])
            duplicate = request(
                app,
                "POST",
                "/api/terminal/login-events",
                {
                    "event_id": "terminal-event-ok",
                    "terminal_id": "gate-2",
                    "matched_user_id": "100001",
                    "similarity": 0.91,
                    "recognized_at_epoch": time.time(),
                    "face_api_result": {
                        "authenticated": True,
                        "match": {"user_id": 100001, "username": "GAOFEI"},
                    },
                },
            )
            self.assertFalse(duplicate.json()["accepted"])
            self.assertTrue(duplicate.json()["duplicate"])
            self.assertEqual(duplicate.json()["audit_id"], accepted.json()["audit_id"])

            audit = request(app, "GET", "/api/audit/login", params={"terminal_id": "gate-2"})
            self.assertEqual(audit.json()["count"], 3)


if __name__ == "__main__":
    unittest.main()
