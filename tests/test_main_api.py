import importlib
import os
import sys
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
        return 0.0


class FakeFaceDB:
    def __init__(self):
        self.audit_entries = []

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
        return {"ready": True, "dirty": False, "record_count": 0}


def load_main_module(api_key="", use_gpu=None, force_cpu=None, extra_env=None):
    for key in [
        "FACE_ENV",
        "FACE_REQUIRE_API_KEY",
        "FACE_CORS_ORIGINS",
        "FACE_LOG_PATH",
        "FACE_DB_PATH",
        "FACE_DUPLICATE_POLICY",
        "FACE_MIN_REGISTER_DET_SCORE",
        "FACE_MIN_REGISTER_FACE_PIXELS",
        "FACE_MIN_REGISTER_BRIGHTNESS",
        "FACE_MAX_REGISTER_BRIGHTNESS",
        "FACE_MAX_IMAGE_BYTES",
        "FACE_MAX_BASE64_CHARS",
        "FACE_MAX_IMAGE_PIXELS",
        "FACE_DET_SIZE",
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
        module = load_main_module()
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
            module.register(module.RegisterReq(username="zhangsan", image="dummy"))

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
            module.register(module.RegisterReq(username="zhangsan", image="dummy"))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assert_error_detail(exc_info.exception.detail, "NO_FACE", "未检测到人脸")

    def test_register_rejects_duplicate_user_when_policy_is_reject(self):
        module = load_main_module(api_key="secret", extra_env={"FACE_DUPLICATE_POLICY": "reject"})
        module.decode_base64 = lambda _: module.np.ones((100, 100, 3), dtype=module.np.uint8) * 120
        module.engine.analyze = lambda _: [
            {"bbox": [0, 0, 80, 80], "det_score": 0.9, "embedding": EMBEDDING, "gender": "M", "age": 20}
        ]
        module.db.list_by_user_id = lambda _user_id: [{"id": "existing"}]

        with self.assertRaises(HTTPException) as exc_info:
            module.register(module.RegisterReq(user_id=1, username="zhangsan", image="dummy"))

        self.assertEqual(exc_info.exception.status_code, 409)
        self.assert_error_detail(exc_info.exception.detail, "DUPLICATE_FACE_USER", "该用户已注册人脸")

    def test_register_rejects_low_quality_face(self):
        module = load_main_module(api_key="secret", extra_env={"FACE_MIN_REGISTER_DET_SCORE": "0.8"})
        module.decode_base64 = lambda _: module.np.ones((100, 100, 3), dtype=module.np.uint8) * 120
        module.engine.analyze = lambda _: [
            {"bbox": [0, 0, 80, 80], "det_score": 0.5, "embedding": EMBEDDING, "gender": "M", "age": 20}
        ]

        with self.assertRaises(HTTPException) as exc_info:
            module.register(module.RegisterReq(user_id=1, username="zhangsan", image="dummy"))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assert_error_detail(exc_info.exception.detail, "FACE_QUALITY_LOW", "人脸质量不符合注册要求")

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
        module.db.search = lambda *args, **kwargs: [{"user_id": 1, "username": "   "}]

        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(module.FaceLoginReq(image="dummy", threshold=0.6))

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
            module.face_login(module.FaceLoginReq(image="dummy", threshold=0.6))

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
            module.face_login(module.FaceLoginReq(image="dummy", threshold=0.6))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assert_error_detail(exc_info.exception.detail, "NO_FACE", "未检测到人脸", "custom reason")

    def test_face_login_returns_multiple_faces_failure_payload(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda _: object()
        module.engine.analyze = lambda _: [
            {"bbox": [0, 0, 1, 1], "det_score": 0.9, "embedding": EMBEDDING, "gender": "M", "age": 20},
            {"bbox": [1, 1, 2, 2], "det_score": 0.8, "embedding": EMBEDDING, "gender": "F", "age": 21},
        ]

        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(module.FaceLoginReq(image="dummy", threshold=0.6))

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
            module.face_login(module.FaceLoginReq(image="dummy", threshold=0.6))

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
        module.db.search = lambda *args, **kwargs: [{"user_id": 7, "username": "zhangsan"}]

        body = module.face_login(module.FaceLoginReq(image="dummy", threshold=0.6, terminal_id="t-1", state="s-1"))

        self.assertTrue(body["authenticated"])
        self.assertEqual(len(module.db.audit_entries), 1)
        self.assertEqual(module.db.audit_entries[0]["success"], True)
        self.assertEqual(module.db.audit_entries[0]["terminal_id"], "t-1")
        self.assertEqual(module.db.audit_entries[0]["matched_user_id"], 7)

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

    def test_login_audit_summary_returns_counts(self):
        module = load_main_module(api_key="secret")
        module.db.add_login_audit(success=True)
        module.db.add_login_audit(success=False, failure_reason="NO_MATCH")

        body = module.login_audit_summary(limit=10)

        self.assertEqual(body["total"], 2)
        self.assertEqual(body["success_count"], 1)
        self.assertEqual(body["failure_count"], 1)

    def test_config_effective_returns_runtime_defaults(self):
        module = load_main_module()

        body = module.effective_config()

        self.assertEqual(
            body,
            {
                "face_login_threshold": 0.55,
                "auth_enabled": False,
                "force_cpu": True,
                "use_gpu": False,
                "environment": "development",
                "cors_origins": ["*"],
                "log_path": "logs/face_api.log",
                "duplicate_policy": "allow",
                "model": "buffalo_l",
                "det_size": [640, 640],
                "db_path": "faces.db",
                "max_base64_image_chars": 11185068,
                "max_image_bytes": 8388608,
                "max_image_pixels": 4096000,
            },
        )

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

        self.assertEqual(
            body,
            {
                "status": "ok",
                "device": "CPU",
                "providers": ["CPUExecutionProvider"],
                "model": "buffalo_l",
                "det_size": [640, 640],
                "auth_enabled": False,
                "force_cpu": True,
                "use_gpu": False,
                "environment": "development",
                "cors_origins": ["*"],
                "db_path": "faces.db",
                "log_path": "logs/face_api.log",
                "duplicate_policy": "allow",
                "search_cache": {"ready": True, "dirty": False, "record_count": 0},
                "faces_count": 0,
            },
        )


if __name__ == "__main__":
    unittest.main()
