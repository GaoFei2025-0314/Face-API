import importlib
import os
import sys
import types
import unittest

from fastapi import HTTPException


EMBEDDING = [0.1] * 512


class FakeFaceEngine:
    def __init__(self, force_cpu=False):
        self.device = "CPU"

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

    def add_login_audit(self, **entry):
        stored = {"id": f"audit-{len(self.audit_entries) + 1}", **entry}
        self.audit_entries.append(stored)
        return stored["id"]

    def list_login_audits(self, limit=20):
        return self.audit_entries[:limit]

    def get_login_audit_summary(self, limit=100):
        entries = self.audit_entries[:limit]
        total = len(entries)
        success_count = sum(1 for entry in entries if entry.get("success"))
        failure_count = total - success_count
        return {
            "total": total,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": success_count / total if total else 0,
        }


def load_main_module(api_key=""):
    if api_key:
        os.environ["FACE_API_KEY"] = api_key
    else:
        os.environ.pop("FACE_API_KEY", None)
    os.environ["FACE_FORCE_CPU"] = "0"

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
    def test_decode_base64_rejects_decoded_bytes_over_limit(self):
        module = load_main_module()
        module.MAX_IMAGE_BYTES = 3
        payload = "YWJjZA=="  # b"abcd"

        with self.assertRaises(HTTPException) as exc_info:
            module.decode_base64(payload)

        self.assertEqual(exc_info.exception.status_code, 413)
        self.assertEqual(exc_info.exception.detail["code"], "IMAGE_TOO_LARGE")
        self.assertIn("超过服务允许", exc_info.exception.detail["reason"])

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
        self.assertEqual(exc_info.exception.detail, {"code": "NO_FACE", "message": "未检测到人脸"})

    def test_delete_face_returns_structured_not_found(self):
        module = load_main_module(api_key="secret")
        module.db.remove = lambda _: False

        with self.assertRaises(HTTPException) as exc_info:
            module.delete_face("missing-id")

        self.assertEqual(exc_info.exception.status_code, 404)
        self.assertEqual(exc_info.exception.detail, {"code": "FACE_ID_NOT_FOUND", "message": "该 ID 不存在"})

    def test_extract_base64_rejects_oversized_payload(self):
        module = load_main_module()
        oversized = "a" * (module.MAX_BASE64_IMAGE_CHARS + 1)

        with self.assertRaises(HTTPException) as exc_info:
            module.extract_base64(module.Base64ImageReq(image=oversized))

        self.assertEqual(exc_info.exception.status_code, 413)
        self.assertEqual(
            exc_info.exception.detail,
            {"code": "IMAGE_TOO_LARGE", "message": "图片数据过大"},
        )

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
        self.assertEqual(
            exc_info.exception.detail,
            {"code": "INVALID_MATCH_RECORD", "message": "身份验证失败，匹配记录无效"},
        )

    def test_system_status_requires_explicit_api_key(self):
        module = load_main_module()

        async def run_check():
            with self.assertRaises(HTTPException) as exc_info:
                await module.require_api_key(None)
            self.assertEqual(exc_info.exception.status_code, 401)
            self.assertEqual(exc_info.exception.detail, "Invalid or missing X-API-Key")

        import asyncio
        asyncio.run(run_check())

    def test_extract_base64_invalid_image_returns_structured_failure(self):
        module = load_main_module()

        with self.assertRaises(HTTPException) as exc_info:
            module.extract_base64(module.Base64ImageReq(image="not-base64"))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertEqual(
            exc_info.exception.detail,
            {"code": "IMAGE_DECODE_FAILED", "message": "无效图像，无法解码"},
        )

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
            self.assertEqual(exc_info.exception.detail, "Invalid or missing X-API-Key")

        import asyncio
        asyncio.run(run_check())

    def test_face_login_returns_no_face_failure_payload(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda _: object()
        module.engine.analyze = lambda _: []

        with self.assertRaises(HTTPException) as exc_info:
            module.face_login(module.FaceLoginReq(image="dummy", threshold=0.6))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertEqual(
            exc_info.exception.detail,
            {"code": "NO_FACE", "message": "未检测到人脸"},
        )

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
        self.assertEqual(
            exc_info.exception.detail,
            {"code": "MULTIPLE_FACES", "message": "检测到多张人脸"},
        )

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
        self.assertEqual(
            exc_info.exception.detail,
            {"code": "NO_MATCH", "message": "身份验证失败，未匹配到有效用户"},
        )

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
        self.assertEqual(
            exc_info.exception.detail,
            {"code": "NO_FACE", "message": "至少一张图未检测到人脸"},
        )

    def test_search_returns_structured_no_face_failure(self):
        module = load_main_module()
        module.decode_base64 = lambda _: object()
        module.engine.analyze = lambda _: []

        with self.assertRaises(HTTPException) as exc_info:
            module.search(module.SearchReq(image="dummy", top_k=5, threshold=0.5))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertEqual(
            exc_info.exception.detail,
            {"code": "NO_FACE", "message": "未检测到人脸"},
        )

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
        self.assertEqual(body["items"][0]["matched_username"], "alice")

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
                "force_cpu": False,
                "model": "buffalo_l",
                "det_size": [640, 640],
                "db_path": "faces.db",
            },
        )

    def test_config_effective_requires_explicit_api_key(self):
        module = load_main_module()

        async def run_check():
            with self.assertRaises(HTTPException) as exc_info:
                await module.require_api_key(None)
            self.assertEqual(exc_info.exception.status_code, 401)
            self.assertEqual(exc_info.exception.detail, "Invalid or missing X-API-Key")

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
                "force_cpu": False,
                "faces_count": 0,
            },
        )


if __name__ == "__main__":
    unittest.main()
