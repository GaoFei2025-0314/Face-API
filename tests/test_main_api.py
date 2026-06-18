import importlib
import hashlib
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from fastapi import HTTPException


EMBEDDING = [0.1] * 512


class FakeFaceEngine:
    instances = []

    def __init__(self, force_cpu=False, use_gpu=False):
        self.force_cpu = force_cpu
        self.use_gpu = use_gpu
        self.device = "CPU"
        self.__class__.instances.append(self)

    def analyze(self, image):
        return []

    @staticmethod
    def cosine_similarity(left, right):
        dot = sum(float(a) * float(b) for a, b in zip(left, right))
        left_norm = sum(float(a) * float(a) for a in left) ** 0.5
        right_norm = sum(float(b) * float(b) for b in right) ** 0.5
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)


class FakeFaceDB:
    def __init__(self):
        self.audit_entries = []
        self.challenges = {}
        self.risk_retry_tokens = []

    def count(self):
        return 0

    def search(self, *args, **kwargs):
        return []

    def add(self, *args, **kwargs):
        return "face-id"

    def remove(self, *args, **kwargs):
        return False

    def list_all(self):
        return []

    def list_by_user_id(self, user_id):
        return []

    def remove_by_user_id(self, user_id):
        return 0

    def add_login_audit(self, **entry):
        stored = {"id": f"audit-{len(self.audit_entries) + 1}", **entry}
        self.audit_entries.append(stored)
        return stored["id"]

    def list_login_audits(self, limit=20, success=None, terminal_id=None):
        entries = self.audit_entries
        if success is not None:
            entries = [entry for entry in entries if bool(entry.get("success")) == success]
        if terminal_id is not None:
            entries = [entry for entry in entries if entry.get("terminal_id") == terminal_id]
        return entries[:limit]

    def get_login_audit_summary(self, limit=100, terminal_id=None):
        entries = self.list_login_audits(limit=limit, terminal_id=terminal_id)
        total = len(entries)
        success_count = sum(1 for entry in entries if entry.get("success"))
        failure_count = total - success_count
        return {
            "total": total,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": success_count / total if total else 0,
        }

    def get_search_cache_status(self):
        return {
            "ready": True,
            "dirty": False,
            "record_count": 0,
            "mode": "exact",
            "target_record_count": 50000,
            "target_latency_ms": 1000,
        }

    def get_search_cache_summary(self):
        return self.get_search_cache_status()

    def get_search_benchmark_summary(self):
        return {
            "mode": "exact",
            "record_count": 0,
            "target_record_count": 50000,
            "target_latency_ms": 1000,
            "approximate_search_enabled": False,
            "metrics": ["avg_ms", "p95_ms", "failure_count", "failure_reasons"],
            "report_format": {"version": "1.0"},
            "index_decision": self.get_search_index_status(),
            "recommendation": "当前使用精确搜索",
        }

    def get_search_index_status(self):
        return {
            "enabled": False,
            "mode": "exact",
            "record_count": 0,
            "fresh": True,
            "rebuild_required": False,
            "fallback": {"enabled": True, "mode": "exact"},
            "enter_conditions": ["5 万人脸 benchmark 的 search 或 login P95 连续超过 1000ms"],
            "candidate_backends": ["faiss-cpu", "faiss-gpu"],
        }

    def add_liveness_challenge(self, *, purpose, terminal_id, action, expires_at, action_window_seconds):
        challenge_id = f"challenge-{len(self.challenges) + 1}"
        self.challenges[challenge_id] = {
            "id": challenge_id,
            "purpose": purpose,
            "terminal_id": terminal_id,
            "action": action,
            "status": "pending",
            "result_reason": None,
            "face_embedding": None,
            "anti_spoof_risk": None,
            "expires_at": expires_at,
            "used_at": None,
            "action_window_seconds": action_window_seconds,
            "created_at_epoch": __import__("time").time(),
        }
        return challenge_id

    def get_liveness_challenge(self, challenge_id):
        return self.challenges.get(challenge_id)

    def mark_liveness_challenge_result(
        self,
        challenge_id,
        *,
        passed,
        result_reason,
        face_embedding=None,
        anti_spoof_risk=None,
    ):
        challenge = self.challenges.get(challenge_id)
        if not challenge or challenge["status"] != "pending":
            return False
        challenge["status"] = "passed" if passed else "failed"
        challenge["result_reason"] = result_reason
        challenge["face_embedding"] = face_embedding
        challenge["anti_spoof_risk"] = anti_spoof_risk
        return True

    def consume_liveness_challenge(self, *, challenge_id, purpose, terminal_id, now):
        challenge = self.challenges.get(challenge_id)
        if not challenge:
            return False, "not_found", None
        if challenge.get("used_at") is not None or challenge["status"] == "used":
            return False, "already_used", challenge
        if now > challenge["expires_at"]:
            challenge["status"] = "expired"
            return False, "expired", challenge
        if challenge["purpose"] != purpose:
            return False, "purpose_mismatch", challenge
        if challenge["terminal_id"] != terminal_id:
            return False, "terminal_mismatch", challenge
        if challenge["status"] != "passed":
            return False, "not_passed", challenge
        challenge["status"] = "used"
        challenge["used_at"] = now
        return True, "ok", challenge

    def add_risk_retry_token(self, *, token_hash, terminal_id, retry_group_id, expires_at, now=None):
        self.risk_retry_tokens.append(
            {
                "token_hash": token_hash,
                "terminal_id": terminal_id,
                "retry_group_id": retry_group_id,
                "expires_at": expires_at,
                "used_at": None,
                "created_at_epoch": now,
            }
        )
        return True

    def consume_risk_retry_token(self, *, token_hash, terminal_id, now):
        for token in self.risk_retry_tokens:
            if token["token_hash"] != token_hash:
                continue
            if token["terminal_id"] != terminal_id:
                return False, "terminal_mismatch", dict(token)
            if token["used_at"] is not None:
                return False, "already_used", dict(token)
            if now > token["expires_at"]:
                return False, "expired", dict(token)
            token["used_at"] = now
            return True, "ok", dict(token)
        return False, "not_found", None

    def backup_to(self, target_path):
        return str(target_path)

    def invalidate_search_cache(self):
        self.search_cache_invalidated = True

    def close(self):
        return None

    def close_all_connections(self):
        self.close_all_connections_called = True


def load_main_module(api_key="", use_gpu=None, force_cpu=None, extra_env=None, disable_login_liveness=True):
    for key in [
        "FACE_ENV",
        "FACE_REQUIRE_API_KEY",
        "FACE_CORS_ORIGINS",
        "FACE_LOG_PATH",
        "FACE_LOG_MAX_BYTES",
        "FACE_LOG_BACKUP_COUNT",
        "FACE_DB_PATH",
        "FACE_DUPLICATE_POLICY",
        "FACE_MIN_REGISTER_DET_SCORE",
        "FACE_MIN_REGISTER_FACE_PIXELS",
        "FACE_MIN_REGISTER_BRIGHTNESS",
        "FACE_MAX_REGISTER_BRIGHTNESS",
        "FACE_MIN_LOGIN_DET_SCORE",
        "FACE_MIN_LOGIN_FACE_PIXELS",
        "FACE_MIN_FACE_SHARPNESS",
        "FACE_MAX_IMAGE_BYTES",
        "FACE_MAX_BASE64_CHARS",
        "FACE_MAX_IMAGE_PIXELS",
        "FACE_DET_SIZE",
        "FACE_LOGIN_LIVENESS_ENABLED",
        "FACE_REGISTER_LIVENESS_ENABLED",
        "FACE_CHALLENGE_TTL_SECONDS",
        "FACE_CHALLENGE_ACTION_SECONDS",
        "FACE_CHALLENGE_MIN_FRAMES",
        "FACE_CHALLENGE_MAX_FRAMES",
        "FACE_CHALLENGE_ACTIONS",
        "FACE_DEFAULT_POLICY_PROFILE",
        "FACE_TERMINAL_POLICY_MAP",
        "FACE_MAINTENANCE_FILE",
        "FACE_ALLOW_ONLINE_RESTORE",
        "FACE_ANTI_SPOOF_ENABLED",
        "FACE_ANTI_SPOOF_BLOCK_LEVEL",
        "FACE_ANTI_SPOOF_MEDIUM_ACTION",
        "FACE_ANTI_SPOOF_RETRY_TOKEN_TTL_SECONDS",
        "FACE_ANTI_SPOOF_MIN_FRAME_VARIATION",
        "FACE_ANTI_SPOOF_MIN_FRAME_DELTA",
        "FACE_ANTI_SPOOF_MIN_FACE_MOTION",
        "FACE_ANTI_SPOOF_MIN_SHARPNESS_VARIATION",
        "FACE_ANTI_SPOOF_MIN_TEXTURE_VARIATION",
        "FACE_LIVENESS_MIN_BRIGHTNESS_VARIATION",
    ]:
        os.environ.pop(key, None)
    if api_key:
        os.environ["FACE_API_KEY"] = api_key
    else:
        os.environ.pop("FACE_API_KEY", None)
    if use_gpu is None:
        os.environ.pop("FACE_USE_GPU", None)
    else:
        os.environ["FACE_USE_GPU"] = use_gpu
    if force_cpu is None:
        os.environ.pop("FACE_FORCE_CPU", None)
    else:
        os.environ["FACE_FORCE_CPU"] = force_cpu
    if disable_login_liveness:
        os.environ["FACE_LOGIN_LIVENESS_ENABLED"] = "0"
    if extra_env:
        os.environ.update(extra_env)
    FakeFaceEngine.instances = []

    fake_face_engine = types.ModuleType("face_engine")
    fake_face_engine.FaceEngine = FakeFaceEngine

    fake_storage = types.ModuleType("storage")
    fake_storage.FaceDB = FakeFaceDB

    fake_onnxruntime = types.ModuleType("onnxruntime")
    fake_onnxruntime.get_available_providers = lambda: ["CPUExecutionProvider"]

    sys.modules["face_engine"] = fake_face_engine
    sys.modules["storage"] = fake_storage
    sys.modules["onnxruntime"] = fake_onnxruntime
    sys.modules.pop("main", None)

    return importlib.import_module("main")


def get_route_dependency_calls(app, path: str, method: str):
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return [dependency.call for dependency in route.dependant.dependencies]
    raise AssertionError(f"Route not found: {method} {path}")


class MainApiContractTests(unittest.TestCase):
    def setUp(self):
        self._module_snapshot = {
            name: sys.modules.get(name)
            for name in ("face_engine", "storage", "onnxruntime", "main")
        }

    def tearDown(self):
        for name, module in self._module_snapshot.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    def assert_error_detail(self, detail, code, message, reason=None):
        self.assertEqual(detail["code"], code)
        self.assertEqual(detail["message"], message)
        if reason is None:
            self.assertTrue(detail["reason"])
        else:
            self.assertEqual(detail["reason"], reason)

    def assert_auth_error_detail(self, detail):
        self.assert_error_detail(
            detail,
            "AUTH_INVALID_OR_MISSING",
            "认证失败",
            "请求缺少有效的 X-API-Key，请检查前端或业务系统的接口配置",
        )

    def test_runtime_defaults_to_cpu_inference(self):
        module = load_main_module()

        self.assertTrue(module.FORCE_CPU)
        self.assertFalse(module.USE_GPU)
        self.assertEqual(module.engine.force_cpu, True)
        self.assertEqual(module.engine.use_gpu, False)

    def test_face_use_gpu_switches_runtime_to_gpu_mode(self):
        module = load_main_module(use_gpu="1")

        self.assertFalse(module.FORCE_CPU)
        self.assertTrue(module.USE_GPU)
        self.assertEqual(module.engine.force_cpu, False)
        self.assertEqual(module.engine.use_gpu, True)

    def test_face_force_cpu_overrides_face_use_gpu(self):
        module = load_main_module(use_gpu="1", force_cpu="1")

        self.assertTrue(module.FORCE_CPU)
        self.assertTrue(module.USE_GPU)
        self.assertEqual(module.engine.force_cpu, True)
        self.assertEqual(module.engine.use_gpu, True)

    def test_startup_validation_rejects_production_without_api_key(self):
        with self.assertRaises(RuntimeError) as exc_info:
            load_main_module(extra_env={"FACE_ENV": "production"})

        self.assertIn("FACE_API_KEY", str(exc_info.exception))

    def test_startup_validation_rejects_invalid_image_limit(self):
        with self.assertRaises(RuntimeError) as exc_info:
            load_main_module(extra_env={"FACE_MAX_IMAGE_BYTES": "not-a-number"})

        self.assertIn("FACE_MAX_IMAGE_BYTES", str(exc_info.exception))

    def test_effective_config_includes_runtime_v1_fields(self):
        module = load_main_module(
            api_key="secret",
            extra_env={
                "FACE_ENV": "production",
                "FACE_CORS_ORIGINS": "http://localhost:3000,http://127.0.0.1:3000",
                "FACE_LOG_PATH": "logs/custom.log",
                "FACE_DUPLICATE_POLICY": "reject",
            },
        )

        body = module.effective_config()

        self.assertEqual(body["environment"], "production")
        self.assertEqual(body["cors_origins"], ["http://localhost:3000", "http://127.0.0.1:3000"])
        self.assertEqual(body["log_path"], "logs/custom.log")
        self.assertEqual(body["duplicate_policy"], "reject")

    def test_configure_cors_uses_configured_origins(self):
        module = load_main_module(
            api_key="secret",
            extra_env={"FACE_ENV": "production", "FACE_CORS_ORIGINS": "http://app.local"},
        )

        self.assertEqual(module.CORS_ORIGINS, ["http://app.local"])

    def test_structured_log_event_masks_sensitive_fields(self):
        module = load_main_module(extra_env={"FACE_LOG_MAX_BYTES": "2048", "FACE_LOG_BACKUP_COUNT": "3"})
        events = []

        with patch.object(module.app_logger, "info", lambda payload: events.append(payload)):
            safe = module.log_event(
                "test_event",
                api_key="secret",
                embedding=[0.1, 0.2],
                route="/extract/base64",
            )

        self.assertEqual(safe["event"], "test_event")
        self.assertEqual(safe["api_key"], "***")
        self.assertEqual(safe["embedding"], "***")
        self.assertIn('"api_key": "***"', events[0])
        self.assertEqual(module.LOG_MAX_BYTES, 2048)
        self.assertEqual(module.LOG_BACKUP_COUNT, 3)
        self.assertEqual(module.app_logger.handlers[0].maxBytes, 2048)
        self.assertEqual(module.app_logger.handlers[0].backupCount, 3)

    def test_structured_log_event_masks_nested_sensitive_fields(self):
        module = load_main_module()

        safe = module.log_event(
            "test_event",
            nested={
                "image": "raw-image",
                "items": [
                    {"embedding": [0.1, 0.2]},
                    {"api_key": "secret"},
                ],
            },
        )

        self.assertEqual(safe["nested"]["image"], "***")
        self.assertEqual(safe["nested"]["items"][0]["embedding"], "***")
        self.assertEqual(safe["nested"]["items"][1]["api_key"], "***")

    def test_sanitize_log_payload_rejects_non_dict_payload(self):
        module = load_main_module()

        with self.assertRaises(TypeError) as exc_info:
            module.sanitize_log_payload("api_key=secret")

        self.assertIn("sanitize_log_payload", str(exc_info.exception))
        self.assertIn("dict", str(exc_info.exception))

    def test_decode_base64_rejects_decoded_bytes_over_limit(self):
        module = load_main_module()
        module.MAX_IMAGE_BYTES = 3
        payload = "YWJjZA=="  # b"abcd"

        with self.assertRaises(HTTPException) as exc_info:
            module.decode_base64(payload)

        self.assertEqual(exc_info.exception.status_code, 413)
        self.assertEqual(exc_info.exception.detail["code"], "IMAGE_TOO_LARGE")
        self.assertIn("超过服务允许", exc_info.exception.detail["reason"])

    def test_decode_base64_ignores_data_url_prefix_for_length_check(self):
        module = load_main_module()
        module.MAX_BASE64_IMAGE_CHARS = 8
        module.MAX_IMAGE_BYTES = 1024
        seen = []

        def capture_image_bytes(image_bytes):
            seen.append(image_bytes)
            return object()

        module.decode_image_bytes = capture_image_bytes

        image = module.decode_base64("data:image/png;base64,YWJjZA==")

        self.assertIsNotNone(image)
        self.assertEqual(seen, [b"abcd"])

    def test_decode_base64_rejects_invalid_base64_characters(self):
        module = load_main_module()

        with self.assertRaises(HTTPException) as exc_info:
            module.decode_base64("YWJjZA==!!!!")

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assert_error_detail(exc_info.exception.detail, "IMAGE_DECODE_FAILED", "无效图像，无法解码")

    def test_decode_image_bytes_rejects_raw_upload_over_limit(self):
        module = load_main_module()
        module.MAX_IMAGE_BYTES = 3

        with self.assertRaises(HTTPException) as exc_info:
            module.decode_image_bytes(b"abcd")

        self.assertEqual(exc_info.exception.status_code, 413)
        self.assertEqual(exc_info.exception.detail["code"], "IMAGE_TOO_LARGE")

    def test_decoded_image_pixels_over_limit_returns_413(self):
        module = load_main_module()
        module.MAX_IMAGE_BYTES = 1024 * 1024
        module.MAX_IMAGE_PIXELS = 3
        module.cv2.imdecode = lambda *_args, **_kwargs: module.np.zeros((2, 2, 3), dtype=module.np.uint8)

        with self.assertRaises(HTTPException) as exc_info:
            module.decode_image_bytes(b"valid-image-bytes")

        self.assertEqual(exc_info.exception.status_code, 413)
        self.assertEqual(exc_info.exception.detail["code"], "IMAGE_PIXELS_TOO_LARGE")
        self.assertEqual(exc_info.exception.detail["message"], "图片分辨率过高")

    def test_auth_errors_return_chinese_reason_payload(self):
        module = load_main_module()

        async def run_check():
            with self.assertRaises(HTTPException) as exc_info:
                await module.require_api_key(None)
            self.assertEqual(exc_info.exception.status_code, 401)
            self.assertEqual(
                exc_info.exception.detail,
                {
                    "code": "AUTH_INVALID_OR_MISSING",
                    "message": "认证失败",
                    "reason": "请求缺少有效的 X-API-Key，请检查前端或业务系统的接口配置",
                },
            )

        import asyncio
        asyncio.run(run_check())

    def test_known_error_detail_includes_reason(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda _: object()
        module.engine.analyze = lambda _: []

        with self.assertRaises(HTTPException) as exc_info:
            module.register(module.RegisterReq(terminal_id="t-1", username="zhangsan", image="dummy"))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertEqual(exc_info.exception.detail["code"], "NO_FACE")
        self.assertEqual(exc_info.exception.detail["message"], "未检测到人脸")
        self.assertEqual(
            exc_info.exception.detail["reason"],
            "图片中没有检测到可用于识别的人脸，请调整光线、角度或距离后重试",
        )

    def test_request_validation_error_returns_structured_payload(self):
        module = load_main_module()
        expected = {
            "detail": {
                "code": "VALIDATION_ERROR",
                "message": "请求参数校验失败",
                "reason": "请求参数格式或取值不符合接口要求，请检查请求体、路径参数或查询参数",
            }
        }

        try:
            from fastapi.testclient import TestClient
        except RuntimeError:
            import asyncio
            import json

            handler = module.app.exception_handlers[module.RequestValidationError]
            response = asyncio.run(handler(None, module.RequestValidationError([])))
            body = json.loads(response.body.decode("utf-8"))
        else:
            client = TestClient(module.app)
            response = client.post("/search", json={"image": "dummy", "top_k": 0, "threshold": 0.5})
            body = response.json()

        self.assertEqual(response.status_code, 422)
        self.assertEqual(body, expected)

    def test_sensitive_routes_require_expected_auth_mode(self):
        module = load_main_module()

        explicit_auth = [
            ("/extract/base64", "POST"),
            ("/system/status", "GET"),
            ("/config/effective", "GET"),
            ("/auth/face-login", "POST"),
            ("/audit/login/recent", "GET"),
            ("/audit/login/summary", "GET"),
            ("/liveness/challenges", "POST"),
            ("/liveness/challenges/submit", "POST"),
            ("/admin/overview", "GET"),
            ("/admin/maintenance", "GET"),
            ("/admin/maintenance", "POST"),
            ("/admin/faces/{face_id}/delete", "POST"),
            ("/admin/backup", "POST"),
            ("/admin/restore", "POST"),
            ("/policy/tuning-summary", "GET"),
            ("/search/benchmark-summary", "GET"),
            ("/search/index-status", "GET"),
            ("/performance/scale-plan", "GET"),
        ]
        conditional_auth = [
            ("/faces/register", "POST"),
            ("/faces", "GET"),
            ("/faces/{face_id}", "DELETE"),
            ("/search", "POST"),
        ]

        for path, method in explicit_auth:
            calls = get_route_dependency_calls(module.app, path, method)
            self.assertIn(module.require_api_key, calls, msg=f"{method} {path} should require explicit auth")

        for path, method in conditional_auth:
            calls = get_route_dependency_calls(module.app, path, method)
            self.assertIn(module.verify_api_key, calls, msg=f"{method} {path} should use conditional auth")

    def test_register_returns_no_face_failure_payload(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda _: object()
        module.engine.analyze = lambda _: []

        with self.assertRaises(HTTPException) as exc_info:
            module.register(module.RegisterReq(terminal_id="t-1", username="zhangsan", image="dummy"))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assert_error_detail(exc_info.exception.detail, "NO_FACE", "未检测到人脸")

    def test_register_rejects_duplicate_user_when_policy_is_reject(self):
        module = load_main_module(
            api_key="secret",
            extra_env={"FACE_DUPLICATE_POLICY": "reject", "FACE_MIN_FACE_SHARPNESS": "0"},
        )
        module.decode_base64 = lambda _: module.np.ones((100, 100, 3), dtype=module.np.uint8) * 120
        module.engine.analyze = lambda _: [
            {"bbox": [0, 0, 80, 80], "det_score": 0.9, "embedding": EMBEDDING, "gender": "M", "age": 20}
        ]
        module.db.list_by_user_id = lambda _user_id: [{"id": "existing"}]

        with self.assertRaises(HTTPException) as exc_info:
            module.register(module.RegisterReq(terminal_id="t-1", user_id=1, username="zhangsan", image="dummy"))

        self.assertEqual(exc_info.exception.status_code, 409)
        self.assert_error_detail(exc_info.exception.detail, "DUPLICATE_FACE_USER", "该用户已注册人脸")

    def test_register_rejects_low_quality_face(self):
        module = load_main_module(
            api_key="secret",
            extra_env={"FACE_MIN_REGISTER_DET_SCORE": "0.8", "FACE_MIN_FACE_SHARPNESS": "0"},
        )
        module.decode_base64 = lambda _: module.np.ones((100, 100, 3), dtype=module.np.uint8) * 120
        module.engine.analyze = lambda _: [
            {"bbox": [0, 0, 80, 80], "det_score": 0.5, "embedding": EMBEDDING, "gender": "M", "age": 20}
        ]

        with self.assertRaises(HTTPException) as exc_info:
            module.register(module.RegisterReq(terminal_id="t-1", user_id=1, username="zhangsan", image="dummy"))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assert_error_detail(exc_info.exception.detail, "FACE_DET_SCORE_LOW", "人脸检测置信度过低")

    def test_delete_face_returns_structured_not_found(self):
        module = load_main_module(api_key="secret")
        module.db.remove = lambda _: False

        with self.assertRaises(HTTPException) as exc_info:
            module.delete_face("missing-id")

        self.assertEqual(exc_info.exception.status_code, 404)
        self.assert_error_detail(exc_info.exception.detail, "FACE_ID_NOT_FOUND", "该 ID 不存在")

    def test_extract_base64_rejects_oversized_payload(self):
        module = load_main_module()
        oversized = "a" * (module.MAX_BASE64_IMAGE_CHARS + 1)

        with self.assertRaises(HTTPException) as exc_info:
            module.extract_base64(module.Base64ImageReq(image=oversized))

        self.assertEqual(exc_info.exception.status_code, 413)
        self.assert_error_detail(exc_info.exception.detail, "IMAGE_TOO_LARGE", "图片数据过大")

    def test_face_login_returns_invalid_match_record_failure_payload(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda _: object()
        module.engine.analyze = lambda _: [
            {
                "bbox": [0.0, 1.0, 2.0, 3.0],
                "det_score": 0.99,
                "landmarks": [[1, 1], [2, 2]],
                "embedding": EMBEDDING,
                "gender": "M",
                "age": 30,
            }
        ]
        module.db.search = lambda *args, **kwargs: [{"user_id": 1, "username": "   ", "similarity": 0.91}]

        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="t-1"))

        self.assertEqual(exc_info.exception.status_code, 403)
        self.assert_error_detail(exc_info.exception.detail, "INVALID_MATCH_RECORD", "身份验证失败，匹配记录无效")

    def test_system_status_requires_explicit_api_key(self):
        module = load_main_module()

        async def run_check():
            with self.assertRaises(HTTPException) as exc_info:
                await module.require_api_key(None)
            self.assertEqual(exc_info.exception.status_code, 401)
            self.assert_auth_error_detail(exc_info.exception.detail)

        import asyncio
        asyncio.run(run_check())

    def test_extract_base64_invalid_image_returns_structured_failure(self):
        module = load_main_module()

        with self.assertRaises(HTTPException) as exc_info:
            module.extract_base64(module.Base64ImageReq(image="not-base64"))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assert_error_detail(exc_info.exception.detail, "IMAGE_DECODE_FAILED", "无效图像，无法解码")

    def test_extract_base64_returns_no_face_code(self):
        module = load_main_module()
        module.decode_base64 = lambda _: object()
        module.engine.analyze = lambda _: []

        with self.assertRaises(HTTPException) as exc_info:
            module.extract_base64(module.Base64ImageReq(image="dummy"))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertEqual(exc_info.exception.detail["code"], "NO_FACE")
        self.assertEqual(exc_info.exception.detail["message"], "未检测到人脸")

    def test_extract_base64_returns_multiple_faces_code(self):
        module = load_main_module()
        module.decode_base64 = lambda _: object()
        module.engine.analyze = lambda _: [
            {"bbox": [0, 0, 1, 1], "det_score": 0.9, "embedding": EMBEDDING, "gender": "M", "age": 20},
            {"bbox": [1, 1, 2, 2], "det_score": 0.8, "embedding": EMBEDDING, "gender": "F", "age": 21},
        ]

        with self.assertRaises(HTTPException) as exc_info:
            module.extract_base64(module.Base64ImageReq(image="dummy"))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertEqual(exc_info.exception.detail["code"], "MULTIPLE_FACES")
        self.assertEqual(exc_info.exception.detail["message"], "检测到多张人脸")

    def test_extract_base64_returns_embedding_and_face_summary(self):
        module = load_main_module()
        module.decode_base64 = lambda _: object()
        module.engine.analyze = lambda _: [
            {
                "bbox": [0.0, 1.0, 2.0, 3.0],
                "det_score": 0.99,
                "landmarks": [[1, 1], [2, 2]],
                "embedding": EMBEDDING,
                "gender": "M",
                "age": 30,
            }
        ]

        body = module.extract_base64(module.Base64ImageReq(image="dummy"))

        self.assertEqual(body["code"], "OK")
        self.assertEqual(body["message"], "ok")
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["embedding"], EMBEDDING)
        self.assertEqual(body["face"]["bbox"], [0.0, 1.0, 2.0, 3.0])
        self.assertEqual(body["face"]["det_score"], 0.99)
        self.assertNotIn("embedding", body["face"])

    def test_extract_base64_requires_explicit_api_key(self):
        module = load_main_module()

        async def run_check():
            with self.assertRaises(HTTPException) as exc_info:
                await module.require_api_key(None)
            self.assertEqual(exc_info.exception.status_code, 401)
            self.assert_auth_error_detail(exc_info.exception.detail)

        import asyncio
        asyncio.run(run_check())

    def test_face_login_returns_no_face_failure_payload(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda _: object()
        module.engine.analyze = lambda _: []

        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="t-1"))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assert_error_detail(
            exc_info.exception.detail,
            "NO_FACE",
            "未检测到人脸",
            "图片中没有检测到可用于识别的人脸，请调整光线、角度或距离后重试",
        )

    def test_face_login_preserves_failure_reason_from_inner_error(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda _: object()

        def raise_custom_error(_image):
            module.raise_api_error(400, "NO_FACE", "未检测到人脸", "custom reason")

        module.get_single_face_or_raise = raise_custom_error

        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="t-1"))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assert_error_detail(exc_info.exception.detail, "NO_FACE", "未检测到人脸", "custom reason")

    def test_face_login_handles_plain_http_exception_detail_from_face_detection(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda _: object()

        def raise_plain_error(_image):
            raise HTTPException(status_code=418, detail="plain failure")

        module.get_single_face_or_raise = raise_plain_error

        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="t-1"))

        self.assertEqual(exc_info.exception.status_code, 418)
        self.assert_error_detail(exc_info.exception.detail, "NO_FACE", "未检测到人脸")

    def test_face_login_returns_multiple_faces_failure_payload(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda _: object()
        module.engine.analyze = lambda _: [
            {"bbox": [0, 0, 1, 1], "det_score": 0.9, "embedding": EMBEDDING, "gender": "M", "age": 20},
            {"bbox": [1, 1, 2, 2], "det_score": 0.8, "embedding": EMBEDDING, "gender": "F", "age": 21},
        ]

        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="t-1"))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assert_error_detail(exc_info.exception.detail, "MULTIPLE_FACES", "检测到多张人脸")

    def test_face_login_returns_no_match_failure_payload(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda _: object()
        module.engine.analyze = lambda _: [
            {
                "bbox": [0.0, 1.0, 2.0, 3.0],
                "det_score": 0.99,
                "landmarks": [[1, 1], [2, 2]],
                "embedding": EMBEDDING,
                "gender": "M",
                "age": 30,
            }
        ]
        module.db.search = lambda *args, **kwargs: []

        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="t-1"))

        self.assertEqual(exc_info.exception.status_code, 403)
        self.assert_error_detail(exc_info.exception.detail, "NO_MATCH", "身份验证失败，未匹配到有效用户")

    def test_compare_returns_structured_no_face_failure(self):
        module = load_main_module()
        first_image = object()
        second_image = object()
        images = iter([first_image, second_image])
        module.decode_base64 = lambda _: next(images)

        def analyze(image):
            if image is first_image:
                return []
            return [{"bbox": [0, 0, 1, 1], "det_score": 0.9, "embedding": EMBEDDING, "gender": "M", "age": 20}]

        module.engine.analyze = analyze

        with self.assertRaises(HTTPException) as exc_info:
            module.compare(module.CompareReq(image1="img-1", image2="img-2", threshold=0.5))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assert_error_detail(exc_info.exception.detail, "NO_FACE", "至少一张图未检测到人脸")

    def test_search_returns_structured_no_face_failure(self):
        module = load_main_module()
        module.decode_base64 = lambda _: object()
        module.engine.analyze = lambda _: []

        with self.assertRaises(HTTPException) as exc_info:
            module.search(module.SearchReq(image="dummy", top_k=5, threshold=0.5))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assert_error_detail(exc_info.exception.detail, "NO_FACE", "未检测到人脸")

    def test_face_login_writes_success_audit(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda _: object()
        module.engine.analyze = lambda _: [
            {
                "bbox": [0.0, 1.0, 2.0, 3.0],
                "det_score": 0.99,
                "landmarks": [[1, 1], [2, 2]],
                "embedding": EMBEDDING,
                "gender": "M",
                "age": 30,
            }
        ]
        module.db.search = lambda *args, **kwargs: [
            {"id": "face-7", "user_id": 7, "username": "zhangsan", "similarity": 0.91}
        ]

        body = module.face_login(module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="t-1", state="s-1"))

        self.assertTrue(body["authenticated"])
        self.assertEqual(len(module.db.audit_entries), 1)
        self.assertEqual(module.db.audit_entries[0]["success"], True)
        self.assertEqual(module.db.audit_entries[0]["terminal_id"], "t-1")
        self.assertEqual(module.db.audit_entries[0]["matched_user_id"], 7)
        self.assertEqual(module.db.audit_entries[0]["quality_metrics"]["det_score"], 0.99)
        self.assertEqual(body["quality_metrics"]["det_score"], 0.99)
        self.assertEqual(body["match"]["face_id"], "face-7")
        self.assertEqual(body["similarity"], 0.91)
        self.assertEqual(body["threshold"], 0.6)

    def test_face_login_records_low_similarity_for_no_match(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda _: object()
        module.engine.analyze = lambda _: [
            {
                "bbox": [0.0, 1.0, 2.0, 3.0],
                "det_score": 0.99,
                "landmarks": [[1, 1], [2, 2]],
                "embedding": EMBEDDING,
                "gender": "M",
                "age": 30,
            }
        ]
        module.db.search = lambda *args, **kwargs: [{"user_id": 7, "username": "zhangsan", "similarity": 0.51}]

        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="t-1", state="s-low"))

        self.assertEqual(exc_info.exception.status_code, 403)
        self.assert_error_detail(exc_info.exception.detail, "NO_MATCH", "身份验证失败，未匹配到有效用户")
        self.assertEqual(module.db.audit_entries[0]["similarity"], 0.51)
        self.assertEqual(module.db.audit_entries[0]["failure_reason"], "NO_MATCH")

    def test_face_login_writes_failure_audit(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda _: object()
        module.engine.analyze = lambda _: []

        with self.assertRaises(HTTPException):
            module.face_login(module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="t-2"))

        self.assertEqual(len(module.db.audit_entries), 1)
        self.assertEqual(module.db.audit_entries[0]["success"], False)
        self.assertEqual(module.db.audit_entries[0]["failure_reason"], "NO_FACE")
        self.assertEqual(module.db.audit_entries[0]["terminal_id"], "t-2")

    def test_list_login_audits_returns_entries(self):
        module = load_main_module(api_key="secret")
        module.db.add_login_audit(success=True, matched_user_id=1, matched_username="alice")
        module.db.add_login_audit(success=False, failure_reason="NO_MATCH")

        body = module.list_login_audits(limit=10)

        self.assertEqual(len(body["items"]), 2)

    def test_list_login_audits_supports_success_and_terminal_filters(self):
        module = load_main_module(api_key="secret")
        module.db.add_login_audit(success=True, terminal_id="door-1")
        module.db.add_login_audit(success=False, terminal_id="door-1")
        module.db.add_login_audit(success=False, terminal_id="door-2")

        body = module.list_login_audits(limit=10, success=False, terminal_id="door-1")

        self.assertEqual(len(body["items"]), 1)
        self.assertFalse(body["items"][0]["success"])
        self.assertEqual(body["items"][0]["terminal_id"], "door-1")

    def test_list_login_audits_returns_anti_spoof_risk(self):
        module = load_main_module(api_key="secret")
        module.db.add_login_audit(
            success=False,
            failure_reason="ANTI_SPOOF_HIGH_RISK",
            terminal_id="door-1",
            anti_spoof_risk={
                "level": "high",
                "reasons": ["static_face_box"],
                "action": "block",
                "message": "疑似翻拍或静态画面，请重新面对摄像头",
            },
        )

        body = module.list_login_audits(limit=10, terminal_id="door-1")

        self.assertEqual(body["items"][0]["anti_spoof_risk"]["level"], "high")
        self.assertEqual(body["items"][0]["anti_spoof_risk"]["action"], "block")

    def test_login_audit_summary_returns_counts(self):
        module = load_main_module(api_key="secret")
        module.db.add_login_audit(success=True)
        module.db.add_login_audit(success=False, failure_reason="NO_MATCH")

        body = module.login_audit_summary(limit=10)

        self.assertEqual(body["total"], 2)
        self.assertEqual(body["success_count"], 1)
        self.assertEqual(body["failure_count"], 1)

    def test_liveness_challenge_create_and_submit_passes(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda image: module.np.ones((10, 10, 3), dtype=module.np.uint8) * (
            120 if image == "bright" else 20
        )
        module.engine.analyze = lambda _: [{"embedding": EMBEDDING, "det_score": 0.9}]

        created = module.create_liveness_challenge(
            module.LivenessChallengeCreateReq(purpose="login", terminal_id="door-1")
        )
        body = module.submit_liveness_challenge(
            module.LivenessChallengeSubmitReq(
                challenge_id=created["challenge_id"],
                purpose="login",
                terminal_id="door-1",
                frames=["dark"] * 10 + ["bright"] * 10,
            )
        )

        self.assertTrue(body["passed"])
        self.assertEqual(module.db.challenges[created["challenge_id"]]["status"], "passed")

    def test_anti_spoof_risk_scoring_marks_static_frames_high(self):
        module = load_main_module(api_key="secret")
        frames = [module.np.ones((40, 40, 3), dtype=module.np.uint8) * 80 for _ in range(10)]
        faces = [{"bbox": [10, 10, 30, 30]}, {"bbox": [10, 10, 30, 30]}, {"bbox": [10, 10, 30, 30]}]

        risk = module.evaluate_anti_spoof_risk(frames, faces)

        self.assertEqual(risk["level"], "high")
        self.assertEqual(risk["action"], "block")
        self.assertIn("repeated_frames", risk["reasons"])
        self.assertIn("static_face_box", risk["reasons"])
        self.assertNotIn("poor_capture_quality", risk["reasons"])

    def test_anti_spoof_risk_scoring_marks_normal_motion_low(self):
        module = load_main_module(api_key="secret")
        frames = []
        for value, left in zip((40, 80, 120, 80, 40, 120), (4, 6, 9, 12, 15, 18)):
            frame = module.np.ones((40, 40, 3), dtype=module.np.uint8) * value
            frame[8:18, left:left + 8] = 220
            frames.append(frame)
        faces = [{"bbox": [10, 10, 30, 30]}, {"bbox": [12, 10, 32, 30]}, {"bbox": [13, 11, 33, 31]}]

        risk = module.evaluate_anti_spoof_risk(frames, faces)

        self.assertEqual(risk["level"], "low")
        self.assertEqual(risk["action"], "allow")
        self.assertEqual(risk["reasons"], ["normal_motion"])

    def test_anti_spoof_risk_scoring_marks_uniform_screen_motion_medium(self):
        module = load_main_module(api_key="secret")
        frames = [
            module.np.ones((40, 40, 3), dtype=module.np.uint8) * value
            for value in (40, 80, 120, 80, 40, 120)
        ]
        faces = [{"bbox": [10, 10, 30, 30]}, {"bbox": [12, 10, 32, 30]}, {"bbox": [13, 11, 33, 31]}]

        risk = module.evaluate_anti_spoof_risk(frames, faces)

        self.assertEqual(risk["level"], "medium")
        self.assertEqual(risk["action"], "retry")
        self.assertIn("uniform_frame_delta", risk["reasons"])
        self.assertNotEqual(risk["reasons"], ["normal_motion"])

    def test_anti_spoof_repeated_frame_delta_threshold_is_configurable(self):
        module = load_main_module(
            api_key="secret",
            extra_env={
                "FACE_ANTI_SPOOF_MIN_FRAME_DELTA": "2.0",
                "FACE_ANTI_SPOOF_MIN_FRAME_VARIATION": "0",
            },
        )
        frames = [
            module.np.ones((20, 20, 3), dtype=module.np.uint8) * 10,
            module.np.ones((20, 20, 3), dtype=module.np.uint8) * 11,
        ]

        risk = module.evaluate_anti_spoof_risk(frames)

        self.assertIn("repeated_frames", risk["reasons"])
        self.assertEqual(risk["metrics"]["max_frame_delta"], 1.0)

    def test_anti_spoof_uniform_frame_delta_uses_texture_threshold(self):
        module = load_main_module(
            api_key="secret",
            extra_env={"FACE_ANTI_SPOOF_MIN_TEXTURE_VARIATION": "0"},
        )
        frames = [
            module.np.ones((40, 40, 3), dtype=module.np.uint8) * value
            for value in (40, 80, 120, 80, 40, 120)
        ]

        risk = module.evaluate_anti_spoof_risk(frames)

        self.assertNotIn("uniform_frame_delta", risk["reasons"])
        self.assertEqual(risk["metrics"]["max_frame_delta_texture"], 0.0)

    def test_anti_spoof_low_sharpness_variation_strengthens_static_face_risk(self):
        module = load_main_module(
            api_key="secret",
            extra_env={
                "FACE_ANTI_SPOOF_MIN_FRAME_DELTA": "0",
                "FACE_ANTI_SPOOF_MIN_FRAME_VARIATION": "0",
                "FACE_ANTI_SPOOF_MIN_TEXTURE_VARIATION": "0",
                "FACE_ANTI_SPOOF_MIN_SHARPNESS_VARIATION": "1",
            },
        )
        frames = [module.np.ones((20, 20, 3), dtype=module.np.uint8) * 80 for _ in range(3)]
        faces = [{"bbox": [5, 5, 15, 15]}, {"bbox": [5, 5, 15, 15]}, {"bbox": [5, 5, 15, 15]}]

        risk = module.evaluate_anti_spoof_risk(frames, faces)

        self.assertEqual(risk["level"], "high")
        self.assertIn("static_face_box", risk["reasons"])
        self.assertIn("low_sharpness_variation", risk["reasons"])
        self.assertEqual(risk["metrics"]["sharpness_variation"], 0.0)

    def test_liveness_challenge_submit_returns_low_anti_spoof_risk(self):
        module = load_main_module(api_key="secret")

        def decode_frame(image):
            index = int(image.split("-")[1])
            base = 72 + index * 3
            frame = module.np.ones((20, 20, 3), dtype=module.np.uint8) * base
            checker = (module.np.indices((20, 20)).sum(axis=0) % 2).astype(bool)
            if index % 2:
                frame[checker] = module.np.clip(frame[checker] + 12, 0, 255)
            else:
                frame[~checker] = module.np.clip(frame[~checker] + 12, 0, 255)
            return frame

        module.decode_base64 = decode_frame

        def analyze(image):
            mean = int(module.np.mean(image))
            left = 2 + min(4, max(0, (mean - 72) // 14))
            return [{"embedding": EMBEDDING, "det_score": 0.9, "bbox": [left, 2, left + 12, 14]}]

        module.engine.analyze = analyze
        created = module.create_liveness_challenge(
            module.LivenessChallengeCreateReq(purpose="login", terminal_id="door-1")
        )

        body = module.submit_liveness_challenge(
            module.LivenessChallengeSubmitReq(
                challenge_id=created["challenge_id"],
                purpose="login",
                terminal_id="door-1",
                frames=[f"frame-{index}" for index in range(20)],
            )
        )

        self.assertTrue(body["passed"])
        self.assertEqual(body["anti_spoof_risk"]["level"], "low")
        self.assertEqual(module.db.challenges[created["challenge_id"]]["anti_spoof_risk"]["level"], "low")

    def test_liveness_challenge_submit_marks_static_frames_high_risk(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda image: module.np.ones((20, 20, 3), dtype=module.np.uint8) * 80
        module.engine.analyze = lambda _: [{"embedding": EMBEDDING, "det_score": 0.9, "bbox": [4, 4, 16, 16]}]
        created = module.create_liveness_challenge(
            module.LivenessChallengeCreateReq(purpose="login", terminal_id="door-1")
        )

        body = module.submit_liveness_challenge(
            module.LivenessChallengeSubmitReq(
                challenge_id=created["challenge_id"],
                purpose="login",
                terminal_id="door-1",
                frames=["flat"] * 10,
            )
        )

        self.assertFalse(body["passed"])
        self.assertEqual(body["result_reason"], "anti_spoof_high_risk")
        self.assertEqual(body["anti_spoof_risk"]["level"], "high")
        self.assertIn("重新面对摄像头", body["anti_spoof_risk"]["message"])

    def test_liveness_challenge_submit_normalizes_purpose(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda image: module.np.ones((10, 10, 3), dtype=module.np.uint8) * (
            120 if image == "bright" else 20
        )
        module.engine.analyze = lambda _: [{"embedding": EMBEDDING, "det_score": 0.9}]

        created = module.create_liveness_challenge(
            module.LivenessChallengeCreateReq(purpose=" Login ", terminal_id="door-1")
        )
        body = module.submit_liveness_challenge(
            module.LivenessChallengeSubmitReq(
                challenge_id=created["challenge_id"],
                purpose=" LOGIN ",
                terminal_id="door-1",
                frames=["dark"] * 10 + ["bright"] * 10,
            )
        )

        self.assertTrue(body["passed"])

    def test_liveness_challenge_action_window_is_enforced(self):
        module = load_main_module(api_key="secret")
        created = module.create_liveness_challenge(
            module.LivenessChallengeCreateReq(purpose="login", terminal_id="door-1")
        )
        module.db.challenges[created["challenge_id"]]["created_at_epoch"] = module.time.time() - 20

        with self.assertRaises(HTTPException) as exc_info:
            module.submit_liveness_challenge(
                module.LivenessChallengeSubmitReq(
                    challenge_id=created["challenge_id"],
                    purpose="login",
                    terminal_id="door-1",
                    frames=["dark"] * 10 + ["bright"] * 10,
                )
            )

        self.assertEqual(exc_info.exception.status_code, 403)
        self.assert_error_detail(exc_info.exception.detail, "LIVENESS_ACTION_WINDOW_EXPIRED", "活体动作超时")

    def test_liveness_challenge_submit_rejects_invalid_purpose_before_matching_challenge(self):
        module = load_main_module(api_key="secret")
        created = module.create_liveness_challenge(
            module.LivenessChallengeCreateReq(purpose="login", terminal_id="door-1")
        )

        with self.assertRaises(HTTPException) as exc_info:
            module.submit_liveness_challenge(
                module.LivenessChallengeSubmitReq(
                    challenge_id=created["challenge_id"],
                    purpose="admin",
                    terminal_id="door-1",
                    frames=["dark"] * 10 + ["bright"] * 10,
                )
        )

        self.assertEqual(exc_info.exception.status_code, 422)
        self.assert_error_detail(exc_info.exception.detail, "VALIDATION_ERROR", "purpose 必须是 login 或 register")
        self.assertIn("当前值为 'admin'", exc_info.exception.detail["reason"])

    def test_liveness_challenge_create_rejects_invalid_purpose_with_specific_message(self):
        module = load_main_module(api_key="secret")

        with self.assertRaises(HTTPException) as exc_info:
            module.create_liveness_challenge(
                module.LivenessChallengeCreateReq(purpose="admin", terminal_id="door-1")
            )

        self.assertEqual(exc_info.exception.status_code, 422)
        self.assert_error_detail(exc_info.exception.detail, "VALIDATION_ERROR", "purpose 必须是 login 或 register")
        self.assertIn("当前值为 'admin'", exc_info.exception.detail["reason"])

    def test_liveness_challenge_cannot_be_written_in_maintenance_mode(self):
        module = load_main_module(api_key="secret")
        module.set_maintenance_mode(True)
        try:
            with self.assertRaises(HTTPException) as create_exc:
                module.create_liveness_challenge(module.LivenessChallengeCreateReq(purpose="login", terminal_id="door-1"))
            self.assertEqual(create_exc.exception.status_code, 503)

            with self.assertRaises(HTTPException) as submit_exc:
                module.submit_liveness_challenge(
                    module.LivenessChallengeSubmitReq(
                        challenge_id="challenge-1",
                        purpose="login",
                        terminal_id="door-1",
                        frames=["dark"] * 10 + ["bright"] * 10,
                    )
                )
            self.assertEqual(submit_exc.exception.status_code, 503)
        finally:
            module.set_maintenance_mode(False)

    def test_failed_liveness_challenge_requires_new_challenge(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda image: module.np.ones((10, 10, 3), dtype=module.np.uint8) * 80
        created = module.create_liveness_challenge(
            module.LivenessChallengeCreateReq(purpose="login", terminal_id="door-1")
        )
        failed = module.submit_liveness_challenge(
            module.LivenessChallengeSubmitReq(
                challenge_id=created["challenge_id"],
                purpose="login",
                terminal_id="door-1",
                frames=["flat"] * 10,
            )
        )
        self.assertFalse(failed["passed"])

        with self.assertRaises(HTTPException) as exc_info:
            module.submit_liveness_challenge(
                module.LivenessChallengeSubmitReq(
                    challenge_id=created["challenge_id"],
                    purpose="login",
                    terminal_id="door-1",
                    frames=["dark"] * 10 + ["bright"] * 10,
                )
            )
        self.assertEqual(exc_info.exception.status_code, 403)

    def test_failed_liveness_challenge_returns_actionable_reason(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda image: module.np.ones((10, 10, 3), dtype=module.np.uint8) * 80
        created = module.create_liveness_challenge(
            module.LivenessChallengeCreateReq(purpose="login", terminal_id="door-1")
        )

        failed = module.submit_liveness_challenge(
            module.LivenessChallengeSubmitReq(
                challenge_id=created["challenge_id"],
                purpose="login",
                terminal_id="door-1",
                frames=["flat"] * 10,
            )
        )

        self.assertFalse(failed["passed"])
        self.assertEqual(failed["result_reason"], "brightness_variation=0.0")
        self.assertIn("动作幅度", failed["reason"])
        self.assertNotEqual(failed["reason"], failed["message"])

    def test_failed_login_liveness_challenge_writes_login_audit(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda image: module.np.ones((10, 10, 3), dtype=module.np.uint8) * 80
        created = module.create_liveness_challenge(
            module.LivenessChallengeCreateReq(purpose="login", terminal_id="door-1")
        )

        failed = module.submit_liveness_challenge(
            module.LivenessChallengeSubmitReq(
                challenge_id=created["challenge_id"],
                purpose="login",
                terminal_id="door-1",
                frames=["flat"] * 10,
            )
        )

        self.assertFalse(failed["passed"])
        self.assertEqual(len(module.db.audit_entries), 1)
        audit = module.db.audit_entries[0]
        self.assertFalse(audit["success"])
        self.assertEqual(audit["terminal_id"], "door-1")
        self.assertEqual(audit["failure_reason"], "LIVENESS_CHALLENGE_FAILED")
        self.assertEqual(audit["liveness_status"], "failed")
        self.assertEqual(audit["liveness_reason"], "brightness_variation=0.0")

    def test_liveness_brightness_variation_threshold_is_configurable(self):
        module = load_main_module(
            api_key="secret",
            extra_env={"FACE_LIVENESS_MIN_BRIGHTNESS_VARIATION": "20"},
        )
        module.decode_base64 = lambda image: module.np.ones((20, 20, 3), dtype=module.np.uint8) * (
            20 if image == "bright" else 10
        )
        module.engine.analyze = lambda _: [{"embedding": EMBEDDING, "det_score": 0.9}]

        created = module.create_liveness_challenge(
            module.LivenessChallengeCreateReq(purpose="login", terminal_id="door-1")
        )
        failed = module.submit_liveness_challenge(
            module.LivenessChallengeSubmitReq(
                challenge_id=created["challenge_id"],
                purpose="login",
                terminal_id="door-1",
                frames=["dark"] * 10 + ["bright"] * 10,
            )
        )

        self.assertFalse(failed["passed"])
        self.assertEqual(failed["result_reason"], "brightness_variation=10.0")

    def test_face_login_requires_liveness_challenge_when_enabled(self):
        module = load_main_module(api_key="secret", disable_login_liveness=False)

        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="door-1"))

        self.assertEqual(exc_info.exception.status_code, 403)
        self.assert_error_detail(exc_info.exception.detail, "LIVENESS_CHALLENGE_REQUIRED", "需要先完成活体挑战")
        self.assertEqual(module.db.audit_entries[0]["liveness_status"], "failed")

    def test_face_login_consumes_liveness_challenge_once(self):
        module = load_main_module(
            api_key="secret",
            disable_login_liveness=False,
            extra_env={"FACE_MIN_FACE_SHARPNESS": "0"},
        )
        challenge_id = module.db.add_liveness_challenge(
            purpose="login",
            terminal_id="door-1",
            action="blink",
            expires_at=module.time.time() + 60,
            action_window_seconds=10,
        )
        module.db.mark_liveness_challenge_result(challenge_id, passed=True, result_reason="ok")
        module.db.challenges[challenge_id]["face_embedding"] = EMBEDDING
        module.decode_base64 = lambda _: module.np.ones((100, 100, 3), dtype=module.np.uint8) * 120
        module.get_single_face_or_raise = lambda _: {
            "bbox": [0, 0, 80, 80],
            "det_score": 0.99,
            "embedding": EMBEDDING,
        }
        module.db.search = lambda *args, **kwargs: [
            {"user_id": 7, "username": "alice", "similarity": 0.91, "metadata": {}}
        ]

        body = module.face_login(
            module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="door-1", challenge_id=challenge_id)
        )

        self.assertTrue(body["authenticated"])
        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(
                module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="door-1", challenge_id=challenge_id)
            )
        self.assertEqual(exc_info.exception.status_code, 403)

    def test_face_login_rejects_liveness_face_mismatch(self):
        module = load_main_module(
            api_key="secret",
            disable_login_liveness=False,
            extra_env={"FACE_MIN_FACE_SHARPNESS": "0"},
        )
        challenge_id = module.db.add_liveness_challenge(
            purpose="login",
            terminal_id="door-1",
            action="blink",
            expires_at=module.time.time() + 60,
            action_window_seconds=10,
        )
        module.db.mark_liveness_challenge_result(
            challenge_id,
            passed=True,
            result_reason="ok",
            face_embedding=[0.1] * 512,
        )
        module.decode_base64 = lambda _: module.np.ones((100, 100, 3), dtype=module.np.uint8) * 120
        module.get_single_face_or_raise = lambda _: {
            "bbox": [0, 0, 80, 80],
            "det_score": 0.99,
            "embedding": [0.0] * 511 + [1.0],
        }

        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(
                module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="door-1", challenge_id=challenge_id)
            )

        self.assertEqual(exc_info.exception.status_code, 403)
        self.assert_error_detail(exc_info.exception.detail, "LIVENESS_CHALLENGE_INVALID", "活体挑战无效")

    def test_face_login_blocks_high_anti_spoof_liveness_result(self):
        module = load_main_module(
            api_key="secret",
            disable_login_liveness=False,
            extra_env={"FACE_MIN_FACE_SHARPNESS": "0"},
        )
        challenge_id = module.db.add_liveness_challenge(
            purpose="login",
            terminal_id="door-1",
            action="blink",
            expires_at=module.time.time() + 60,
            action_window_seconds=10,
        )
        risk = {
            "level": "high",
            "reasons": ["repeated_frames", "static_face_box"],
            "action": "block",
            "message": "疑似翻拍或静态画面，请重新面对摄像头",
        }
        module.db.mark_liveness_challenge_result(
            challenge_id,
            passed=False,
            result_reason="anti_spoof_high_risk",
            anti_spoof_risk=risk,
        )
        module.decode_base64 = lambda _: module.np.ones((100, 100, 3), dtype=module.np.uint8) * 120
        module.get_single_face_or_raise = lambda _: {
            "bbox": [0, 0, 80, 80],
            "det_score": 0.99,
            "embedding": EMBEDDING,
        }

        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(
                module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="door-1", challenge_id=challenge_id)
            )

        self.assertEqual(exc_info.exception.status_code, 403)
        self.assert_error_detail(exc_info.exception.detail, "ANTI_SPOOF_HIGH_RISK", "疑似翻拍风险")
        self.assertEqual(module.db.audit_entries[0]["failure_reason"], "ANTI_SPOOF_HIGH_RISK")
        self.assertEqual(module.db.audit_entries[0]["anti_spoof_risk"]["level"], "high")

    def test_face_login_returns_low_anti_spoof_risk_without_breaking_success_response(self):
        module = load_main_module(
            api_key="secret",
            disable_login_liveness=False,
            extra_env={"FACE_MIN_FACE_SHARPNESS": "0"},
        )
        challenge_id = module.db.add_liveness_challenge(
            purpose="login",
            terminal_id="door-1",
            action="blink",
            expires_at=module.time.time() + 60,
            action_window_seconds=10,
        )
        risk = {
            "level": "low",
            "reasons": ["normal_motion"],
            "action": "allow",
            "message": "活体检测通过",
        }
        module.db.mark_liveness_challenge_result(
            challenge_id,
            passed=True,
            result_reason="ok",
            face_embedding=EMBEDDING,
            anti_spoof_risk=risk,
        )
        module.decode_base64 = lambda _: module.np.ones((100, 100, 3), dtype=module.np.uint8) * 120
        module.get_single_face_or_raise = lambda _: {
            "bbox": [0, 0, 80, 80],
            "det_score": 0.99,
            "embedding": EMBEDDING,
        }
        module.db.search = lambda *args, **kwargs: [
            {"id": "face-7", "user_id": 7, "username": "alice", "similarity": 0.91, "metadata": {}}
        ]

        body = module.face_login(
            module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="door-1", challenge_id=challenge_id)
        )

        self.assertTrue(body["authenticated"])
        self.assertEqual(body["anti_spoof_risk"]["level"], "low")
        self.assertEqual(module.db.audit_entries[0]["anti_spoof_risk"]["level"], "low")

    def test_face_login_medium_anti_spoof_returns_retry_detail_and_token(self):
        module = load_main_module(
            api_key="secret",
            disable_login_liveness=False,
            extra_env={"FACE_MIN_FACE_SHARPNESS": "0"},
        )
        challenge_id = module.db.add_liveness_challenge(
            purpose="login",
            terminal_id="door-1",
            action="blink",
            expires_at=module.time.time() + 60,
            action_window_seconds=10,
        )
        risk = {
            "level": "medium",
            "reasons": ["low_frame_variation"],
            "action": "retry",
            "message": "画面变化不足，请调整光线、脸部位置后重试",
        }
        module.db.mark_liveness_challenge_result(
            challenge_id,
            passed=True,
            result_reason="ok",
            face_embedding=EMBEDDING,
            anti_spoof_risk=risk,
        )
        module.decode_base64 = lambda _: module.np.ones((100, 100, 3), dtype=module.np.uint8) * 120
        module.get_single_face_or_raise = lambda _: {
            "bbox": [0, 0, 80, 80],
            "det_score": 0.99,
            "embedding": EMBEDDING,
        }
        module.db.search = lambda *args, **kwargs: [
            {"id": "face-7", "user_id": 7, "username": "alice", "similarity": 0.91, "metadata": {}}
        ]

        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(
                module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="door-1", challenge_id=challenge_id)
            )

        self.assertEqual(exc_info.exception.status_code, 403)
        detail = exc_info.exception.detail
        self.assert_error_detail(detail, "ANTI_SPOOF_MEDIUM_RETRY_REQUIRED", "检测到中风险，请重试一次")
        self.assertIn("retry", detail)
        self.assertTrue(detail["retry"]["risk_retry_token"])
        self.assertTrue(detail["retry"]["expires_at"].endswith("Z"))
        self.assertEqual(detail["retry"]["remaining_attempts"], 1)
        self.assertNotIn("risk_retry_token", module.db.audit_entries[0])
        self.assertEqual(module.db.audit_entries[0]["failure_reason"], "ANTI_SPOOF_MEDIUM_RETRY_REQUIRED")
        self.assertEqual(module.db.audit_entries[0]["anti_spoof_risk"]["level"], "medium")
        token_hash = hashlib.sha256(detail["retry"]["risk_retry_token"].encode("utf-8")).hexdigest()
        self.assertEqual(module.db.risk_retry_tokens[0]["token_hash"], token_hash)

    def test_face_login_accepts_low_risk_retry_with_valid_token_once(self):
        module = load_main_module(
            api_key="secret",
            disable_login_liveness=False,
            extra_env={"FACE_MIN_FACE_SHARPNESS": "0"},
        )
        raw_token = "retry-token"
        module.db.add_risk_retry_token(
            token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            terminal_id="door-1",
            retry_group_id="challenge-original",
            expires_at=module.time.time() + 60,
            now=module.time.time(),
        )
        challenge_id = module.db.add_liveness_challenge(
            purpose="login",
            terminal_id="door-1",
            action="blink",
            expires_at=module.time.time() + 60,
            action_window_seconds=10,
        )
        risk = {
            "level": "low",
            "reasons": ["normal_motion"],
            "action": "allow",
            "message": "活体检测通过",
        }
        module.db.mark_liveness_challenge_result(
            challenge_id,
            passed=True,
            result_reason="ok",
            face_embedding=EMBEDDING,
            anti_spoof_risk=risk,
        )
        module.decode_base64 = lambda _: module.np.ones((100, 100, 3), dtype=module.np.uint8) * 120
        module.get_single_face_or_raise = lambda _: {
            "bbox": [0, 0, 80, 80],
            "det_score": 0.99,
            "embedding": EMBEDDING,
        }
        module.db.search = lambda *args, **kwargs: [
            {"id": "face-7", "user_id": 7, "username": "alice", "similarity": 0.91, "metadata": {}}
        ]

        body = module.face_login(
            module.FaceLoginReq(
                image="dummy",
                threshold=0.6,
                terminal_id="door-1",
                challenge_id=challenge_id,
                risk_retry_token=raw_token,
            )
        )

        self.assertTrue(body["authenticated"])
        self.assertIsNotNone(module.db.risk_retry_tokens[0]["used_at"])

    def test_face_login_rejects_second_medium_retry_without_new_token(self):
        module = load_main_module(
            api_key="secret",
            disable_login_liveness=False,
            extra_env={"FACE_MIN_FACE_SHARPNESS": "0"},
        )
        raw_token = "retry-token"
        module.db.add_risk_retry_token(
            token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            terminal_id="door-1",
            retry_group_id="challenge-original",
            expires_at=module.time.time() + 60,
            now=module.time.time(),
        )
        challenge_id = module.db.add_liveness_challenge(
            purpose="login",
            terminal_id="door-1",
            action="blink",
            expires_at=module.time.time() + 60,
            action_window_seconds=10,
        )
        risk = {
            "level": "medium",
            "reasons": ["low_frame_variation"],
            "action": "retry",
            "message": "画面变化不足，请调整光线、脸部位置后重试",
        }
        module.db.mark_liveness_challenge_result(
            challenge_id,
            passed=True,
            result_reason="ok",
            face_embedding=EMBEDDING,
            anti_spoof_risk=risk,
        )
        module.decode_base64 = lambda _: module.np.ones((100, 100, 3), dtype=module.np.uint8) * 120
        module.get_single_face_or_raise = lambda _: {
            "bbox": [0, 0, 80, 80],
            "det_score": 0.99,
            "embedding": EMBEDDING,
        }

        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(
                module.FaceLoginReq(
                    image="dummy",
                    threshold=0.6,
                    terminal_id="door-1",
                    challenge_id=challenge_id,
                    risk_retry_token=raw_token,
                )
            )

        self.assertEqual(exc_info.exception.status_code, 403)
        self.assertEqual(exc_info.exception.detail["code"], "ANTI_SPOOF_MEDIUM_RETRY_EXHAUSTED")
        self.assertNotIn("risk_retry_token", exc_info.exception.detail)
        self.assertEqual(len(module.db.risk_retry_tokens), 1)
        self.assertIsNotNone(module.db.risk_retry_tokens[0]["used_at"])
        self.assertEqual(module.db.audit_entries[0]["failure_reason"], "ANTI_SPOOF_MEDIUM_RETRY_EXHAUSTED")

    def test_face_login_medium_anti_spoof_review_requires_manual_review(self):
        module = load_main_module(
            api_key="secret",
            disable_login_liveness=False,
            extra_env={
                "FACE_MIN_FACE_SHARPNESS": "0",
                "FACE_ANTI_SPOOF_MEDIUM_ACTION": "review",
            },
        )
        challenge_id = module.db.add_liveness_challenge(
            purpose="login",
            terminal_id="door-1",
            action="blink",
            expires_at=module.time.time() + 60,
            action_window_seconds=10,
        )
        risk = {
            "level": "medium",
            "reasons": ["low_frame_variation"],
            "action": "review",
            "message": "画面变化不足，请调整光线、脸部位置后重试",
        }
        module.db.mark_liveness_challenge_result(
            challenge_id,
            passed=True,
            result_reason="ok",
            face_embedding=EMBEDDING,
            anti_spoof_risk=risk,
        )
        module.decode_base64 = lambda _: module.np.ones((100, 100, 3), dtype=module.np.uint8) * 120
        module.get_single_face_or_raise = lambda _: {
            "bbox": [0, 0, 80, 80],
            "det_score": 0.99,
            "embedding": EMBEDDING,
        }
        module.db.search = lambda *args, **kwargs: [
            {"id": "face-7", "user_id": 7, "username": "alice", "similarity": 0.91, "metadata": {}}
        ]

        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(
                module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="door-1", challenge_id=challenge_id)
            )

        self.assertEqual(exc_info.exception.status_code, 403)
        self.assert_error_detail(
            exc_info.exception.detail,
            "ANTI_SPOOF_MEDIUM_REVIEW_REQUIRED",
            "中风险需要人工复核",
        )
        self.assertEqual(module.db.audit_entries[0]["failure_reason"], "ANTI_SPOOF_MEDIUM_REVIEW_REQUIRED")
        self.assertEqual(module.db.audit_entries[0]["anti_spoof_risk"]["action"], "review")
        self.assertEqual(module.db.risk_retry_tokens, [])

    def test_face_login_medium_anti_spoof_block_uses_distinct_error_code(self):
        module = load_main_module(
            api_key="secret",
            disable_login_liveness=False,
            extra_env={
                "FACE_MIN_FACE_SHARPNESS": "0",
                "FACE_ANTI_SPOOF_MEDIUM_ACTION": "block",
            },
        )
        challenge_id = module.db.add_liveness_challenge(
            purpose="login",
            terminal_id="door-1",
            action="blink",
            expires_at=module.time.time() + 60,
            action_window_seconds=10,
        )
        risk = {
            "level": "medium",
            "reasons": ["low_frame_variation"],
            "action": "block",
            "message": "画面变化不足，请调整光线、脸部位置后重试",
        }
        module.db.mark_liveness_challenge_result(
            challenge_id,
            passed=True,
            result_reason="ok",
            face_embedding=EMBEDDING,
            anti_spoof_risk=risk,
        )
        module.decode_base64 = lambda _: module.np.ones((100, 100, 3), dtype=module.np.uint8) * 120
        module.get_single_face_or_raise = lambda _: {
            "bbox": [0, 0, 80, 80],
            "det_score": 0.99,
            "embedding": EMBEDDING,
        }
        module.db.search = lambda *args, **kwargs: [
            {"id": "face-7", "user_id": 7, "username": "alice", "similarity": 0.91, "metadata": {}}
        ]

        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(
                module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="door-1", challenge_id=challenge_id)
            )

        self.assertEqual(exc_info.exception.status_code, 403)
        self.assert_error_detail(
            exc_info.exception.detail,
            "ANTI_SPOOF_MEDIUM_BLOCKED",
            "中风险未通过",
        )
        self.assertEqual(module.db.audit_entries[0]["failure_reason"], "ANTI_SPOOF_MEDIUM_BLOCKED")
        self.assertEqual(module.db.audit_entries[0]["anti_spoof_risk"]["action"], "block")
        self.assertEqual(module.db.risk_retry_tokens, [])

    def test_face_login_medium_anti_spoof_unknown_action_fails_closed(self):
        module = load_main_module(
            api_key="secret",
            disable_login_liveness=False,
            extra_env={"FACE_MIN_FACE_SHARPNESS": "0"},
        )
        module.FACE_ANTI_SPOOF_MEDIUM_ACTION = "warn"
        challenge_id = module.db.add_liveness_challenge(
            purpose="login",
            terminal_id="door-1",
            action="blink",
            expires_at=module.time.time() + 60,
            action_window_seconds=10,
        )
        risk = {
            "level": "medium",
            "reasons": ["low_frame_variation"],
            "action": "warn",
            "message": "画面变化不足，请调整光线、脸部位置后重试",
        }
        module.db.mark_liveness_challenge_result(
            challenge_id,
            passed=True,
            result_reason="ok",
            face_embedding=EMBEDDING,
            anti_spoof_risk=risk,
        )
        module.decode_base64 = lambda _: module.np.ones((100, 100, 3), dtype=module.np.uint8) * 120
        module.get_single_face_or_raise = lambda _: {
            "bbox": [0, 0, 80, 80],
            "det_score": 0.99,
            "embedding": EMBEDDING,
        }
        module.db.search = lambda *args, **kwargs: [
            {"id": "face-7", "user_id": 7, "username": "alice", "similarity": 0.91, "metadata": {}}
        ]

        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(
                module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="door-1", challenge_id=challenge_id)
            )

        self.assertEqual(exc_info.exception.status_code, 403)
        self.assert_error_detail(
            exc_info.exception.detail,
            "ANTI_SPOOF_CONFIG_INVALID",
            "防翻拍配置异常",
            "服务端中风险处理策略配置无效，已按失败处理，请联系管理员检查防翻拍策略配置",
        )
        self.assertNotIn("FACE_ANTI_SPOOF_MEDIUM_ACTION", exc_info.exception.detail["reason"])
        self.assertEqual(module.db.audit_entries[0]["failure_reason"], "ANTI_SPOOF_CONFIG_INVALID")
        self.assertEqual(module.db.audit_entries[0]["anti_spoof_risk"]["action"], "warn")

    def test_admin_restore_requires_maintenance_and_confirmation(self):
        module = load_main_module(api_key="secret")

        with self.assertRaises(HTTPException) as exc_info:
            module.admin_restore(module.RestoreReq(backup_dir="missing", confirm=True))
        self.assertEqual(exc_info.exception.status_code, 503)
        self.assert_error_detail(exc_info.exception.detail, "MAINTENANCE_MODE_REQUIRED", "需要先进入维护模式")

        module.set_maintenance_mode(True)
        try:
            with self.assertRaises(HTTPException) as confirm_exc:
                module.admin_restore(module.RestoreReq(backup_dir="missing", confirm=False))
            self.assertEqual(confirm_exc.exception.status_code, 400)
        finally:
            module.set_maintenance_mode(False)

    def test_admin_restore_invalidates_search_cache_after_restore(self):
        module = load_main_module(api_key="secret")
        module.set_maintenance_mode(True)
        try:
            module.restore_db_files = lambda backup_dir: ["faces.db"]
            body = module.admin_restore(module.RestoreReq(backup_dir="backups/ok", confirm=True))
            self.assertTrue(body["ok"])
            self.assertTrue(module.db.search_cache_invalidated)
        finally:
            module.set_maintenance_mode(False)

    def test_admin_restore_closes_all_registered_db_connections(self):
        module = load_main_module(api_key="secret")
        module.set_maintenance_mode(True)
        try:
            module.restore_db_files = lambda backup_dir: ["faces.db"]
            body = module.admin_restore(module.RestoreReq(backup_dir="backups/ok", confirm=True))

            self.assertTrue(body["ok"])
            self.assertTrue(module.db.close_all_connections_called)
        finally:
            module.set_maintenance_mode(False)

    def test_admin_restore_is_disabled_by_default_in_production(self):
        module = load_main_module(
            api_key="secret",
            extra_env={"FACE_ENV": "production", "FACE_CORS_ORIGINS": "http://app.local"},
        )

        with self.assertRaises(HTTPException) as exc_info:
            module.admin_restore(module.RestoreReq(backup_dir="backups/ok", confirm=True))

        self.assertEqual(exc_info.exception.status_code, 403)
        self.assert_error_detail(exc_info.exception.detail, "ONLINE_RESTORE_DISABLED", "当前环境不允许在线恢复")

    def test_admin_restore_rejects_paths_outside_backups(self):
        module = load_main_module(api_key="secret")
        module.set_maintenance_mode(True)
        try:
            with self.assertRaises(HTTPException) as exc_info:
                module.admin_restore(module.RestoreReq(backup_dir="../outside", confirm=True))
            self.assertEqual(exc_info.exception.status_code, 400)
            self.assert_error_detail(exc_info.exception.detail, "BACKUP_PATH_INVALID", "备份路径不合法")
        finally:
            module.set_maintenance_mode(False)

    def test_restore_db_files_uses_source_project_root_for_path_validation(self):
        module = load_main_module(api_key="secret")
        with patch.object(module.admin_ops, "restore_db_files", return_value=["faces.db"]) as restore_mock:
            restored = module.restore_db_files(module.Path("backups/ok"))

        self.assertEqual(restored, ["faces.db"])
        _args, kwargs = restore_mock.call_args
        self.assertEqual(kwargs["project_root"].resolve(), module.Path(module.__file__).parent.resolve())

    def test_restore_removes_stale_wal_when_backup_has_main_db_only(self):
        module = load_main_module(api_key="secret")
        os.makedirs("backups", exist_ok=True)
        with tempfile.TemporaryDirectory(dir="backups") as backup_dir, tempfile.TemporaryDirectory() as db_dir:
            db_path = os.path.join(db_dir, "faces.db")
            module.DB_PATH = db_path
            with open(db_path, "w", encoding="utf-8") as f:
                f.write("old")
            with open(db_path + "-wal", "w", encoding="utf-8") as f:
                f.write("stale wal")
            with open(os.path.join(backup_dir, "faces.db"), "w", encoding="utf-8") as f:
                f.write("backup")

            restored = module.restore_db_files(module.Path(backup_dir))

            self.assertEqual(restored, [db_path])
            with open(db_path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "backup")
            self.assertFalse(os.path.exists(db_path + "-wal"))

    def test_public_health_is_minimal(self):
        module = load_main_module()

        body = module.health()

        self.assertEqual(body, {"status": "ok", "service": "face_api"})

    def test_openapi_contains_v11_routes_and_key_fields(self):
        module = load_main_module(api_key="secret")

        schema = module.app.openapi()

        self.assertIn("/liveness/challenges", schema["paths"])
        self.assertIn("/admin/restore", schema["paths"])
        register_props = schema["components"]["schemas"]["RegisterReq"]["properties"]
        login_props = schema["components"]["schemas"]["FaceLoginReq"]["properties"]
        self.assertIn("terminal_id", register_props)
        self.assertIn("challenge_id", register_props)
        self.assertIn("terminal_id", login_props)
        self.assertIn("challenge_id", login_props)
        self.assertIn("risk_retry_token", login_props)

    def test_api_schema_models_are_importable(self):
        from api_schemas import (
            AntiSpoofRisk,
            Base64ImageReq,
            FaceLoginReq,
            FaceLoginResp,
            LivenessChallengeSubmitResp,
            LoginAuditItem,
            RegisterReq,
            SystemStatusResp,
        )

        self.assertEqual(Base64ImageReq.model_fields["image"].annotation, str)
        self.assertIn("terminal_id", FaceLoginReq.model_fields)
        self.assertIn("risk_retry_token", FaceLoginReq.model_fields)
        self.assertIn("username", RegisterReq.model_fields)
        self.assertIn("device", SystemStatusResp.model_fields)
        self.assertEqual(AntiSpoofRisk.model_fields["level"].annotation, str)
        self.assertIn("anti_spoof_risk", FaceLoginResp.model_fields)
        self.assertIn("anti_spoof_risk", LivenessChallengeSubmitResp.model_fields)
        self.assertIn("anti_spoof_risk", LoginAuditItem.model_fields)

    def test_policy_and_search_v11_summaries_are_read_only(self):
        module = load_main_module(api_key="secret")
        module.db.add_login_audit(success=False, similarity=0.4, terminal_id="door-1")

        tuning = module.policy_tuning_summary(limit=10, terminal_id="door-1")
        search_status = module.search_benchmark_summary()

        self.assertFalse(tuning["auto_apply"])
        self.assertEqual(tuning["policy"]["profile"], "default")
        self.assertFalse(tuning["sample_sufficient"])
        self.assertIn("样本不足", tuning["recommendation"])
        self.assertEqual(search_status["mode"], "exact")
        self.assertEqual(search_status["target_record_count"], 50000)

    def test_policy_tuning_summary_exposes_false_accept_and_reject_risks(self):
        module = load_main_module(api_key="secret")
        for _ in range(20):
            module.db.add_login_audit(success=True, similarity=0.57, terminal_id="door-1")
        for _ in range(10):
            module.db.add_login_audit(success=False, similarity=0.54, failure_reason="NO_MATCH", terminal_id="door-1")

        tuning = module.policy_tuning_summary(limit=50, terminal_id="door-1")

        self.assertTrue(tuning["sample_sufficient"])
        self.assertFalse(tuning["auto_apply"])
        self.assertTrue(tuning["manual_review_required"])
        self.assertIn("false accept", tuning["false_accept_risk"])
        self.assertIn("false reject", tuning["false_reject_risk"])
        self.assertTrue(tuning["risk_notes"])

    def test_performance_scale_plan_exposes_v16_contract(self):
        module = load_main_module(api_key="secret")

        index_status = module.search_index_status()
        plan = module.performance_scale_plan()

        self.assertFalse(index_status["enabled"])
        self.assertEqual(index_status["mode"], "exact")
        self.assertTrue(index_status["fallback"]["enabled"])
        self.assertIn("enter_conditions", index_status)
        self.assertEqual(plan["benchmark"]["target_record_count"], 50000)
        self.assertIn("p95_ms", plan["benchmark"]["metrics"])
        self.assertIn("image_path", plan["bulk_manifest"]["import_manifest_required_fields"])
        self.assertIn("scripts/benchmark-scale.py", plan["bulk_manifest"]["scripts"]["benchmark"])

    def test_openapi_contains_v16_routes(self):
        module = load_main_module(api_key="secret")

        schema = module.app.openapi()

        self.assertIn("/search/index-status", schema["paths"])
        self.assertIn("/performance/scale-plan", schema["paths"])

    def test_config_effective_returns_runtime_defaults(self):
        module = load_main_module(disable_login_liveness=False)

        body = module.effective_config()

        self.assertEqual(body["face_login_threshold"], 0.55)
        self.assertTrue(body["force_cpu"])
        self.assertEqual(body["model"], "buffalo_l")
        self.assertEqual(body["log_rotation"]["max_bytes"], 10 * 1024 * 1024)
        self.assertEqual(body["log_rotation"]["backup_count"], 5)
        self.assertTrue(body["liveness"]["login_enabled"])
        self.assertFalse(body["liveness"]["register_enabled"])
        self.assertEqual(body["liveness"]["challenge_ttl_seconds"], 60)
        self.assertEqual(body["liveness"]["action_window_seconds"], 10)
        self.assertEqual(body["anti_spoof"]["mode"], "lightweight-risk-score")
        self.assertTrue(body["anti_spoof"]["enabled"])
        self.assertEqual(body["anti_spoof"]["default_block_level"], "high")
        self.assertEqual(body["anti_spoof"]["medium_action"], "retry")
        self.assertEqual(body["anti_spoof"]["thresholds"]["min_texture_variation"], 1.0)
        self.assertEqual(body["anti_spoof"]["retry"]["medium_max_retries"], 1)
        self.assertEqual(body["anti_spoof"]["retry"]["token_ttl_seconds"], 300)
        self.assertIn("printed_photo", body["anti_spoof"]["sample_types"])
        self.assertEqual(body["search_target"]["target_record_count"], 50000)
        self.assertEqual(body["search_target"]["target_latency_ms"], 1000)

    def test_config_effective_requires_explicit_api_key(self):
        module = load_main_module()

        async def run_check():
            with self.assertRaises(HTTPException) as exc_info:
                await module.require_api_key(None)
            self.assertEqual(exc_info.exception.status_code, 401)
            self.assert_auth_error_detail(exc_info.exception.detail)

        import asyncio
        asyncio.run(run_check())

    def test_system_status_returns_runtime_summary(self):
        module = load_main_module()

        body = module.system_status()

        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["device"], "CPU")
        self.assertEqual(body["log_rotation"]["backup_count"], 5)
        self.assertEqual(body["search_cache"]["mode"], "exact")
        self.assertEqual(body["search_cache"]["target_record_count"], 50000)
        self.assertFalse(body["liveness"]["login_enabled"])
        self.assertEqual(body["anti_spoof"]["default_block_level"], "high")
        self.assertEqual(body["anti_spoof"]["medium_action"], "retry")
        self.assertEqual(body["anti_spoof"]["thresholds"]["min_texture_variation"], 1.0)
        self.assertEqual(body["anti_spoof"]["retry"]["medium_max_retries"], 1)
        self.assertEqual(body["anti_spoof"]["retry"]["token_ttl_seconds"], 300)
        self.assertEqual(body["recognition_policy"]["profile"], "default")
        self.assertFalse(body["maintenance_mode"])
        self.assertEqual(body["faces_count"], 0)

    def test_system_status_exposes_fields_for_local_status_pages(self):
        module = load_main_module()

        data = module.system_status()
        for key in [
            "status",
            "device",
            "auth_enabled",
            "db_path",
            "log_path",
            "faces_count",
            "maintenance_mode",
            "liveness",
            "search_cache",
        ]:
            self.assertIn(key, data)

    def test_system_status_uses_lightweight_search_cache_summary(self):
        module = load_main_module()

        def fail_if_heavy_cache_loads():
            raise AssertionError("system status must not load the full search cache")

        module.db.get_search_cache_status = fail_if_heavy_cache_loads
        module.db.get_search_cache_summary = lambda: {
            "ready": False,
            "dirty": True,
            "record_count": 0,
            "mode": "exact",
            "target_record_count": 50000,
            "target_latency_ms": 1000,
        }

        data = module.system_status()

        self.assertTrue(data["search_cache"]["dirty"])

    def test_admin_overview_does_not_return_full_face_list(self):
        module = load_main_module(api_key="secret")

        def fail_if_full_face_list_loads():
            raise AssertionError("admin overview must not load all face records")

        module.db.list_all = fail_if_full_face_list_loads

        data = module.admin_overview()

        self.assertEqual(data["faces"], {"count": 0})


if __name__ == "__main__":
    unittest.main()
