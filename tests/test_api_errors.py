import unittest

from fastapi import HTTPException

from api_errors import ERROR_DEFINITIONS, error_detail, raise_api_error


class ApiErrorsTest(unittest.TestCase):
    def test_known_error_detail_includes_chinese_reason(self):
        detail = error_detail("NO_FACE")

        self.assertEqual(detail["code"], "NO_FACE")
        self.assertEqual(detail["message"], "未检测到人脸")
        self.assertIn("调整光线", detail["reason"])

    def test_unknown_error_detail_has_safe_fallback(self):
        detail = error_detail("SOME_UNKNOWN_CODE")

        self.assertEqual(detail["code"], "SOME_UNKNOWN_CODE")
        self.assertEqual(detail["message"], "请求失败")
        self.assertIn("请求处理失败", detail["reason"])

    def test_raise_api_error_uses_structured_detail(self):
        with self.assertRaises(HTTPException) as ctx:
            raise_api_error(400, "NO_FACE")

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail["code"], "NO_FACE")

    def test_key_error_codes_remain_defined(self):
        required = {
            "AUTH_INVALID_OR_MISSING",
            "IMAGE_DECODE_FAILED",
            "NO_FACE",
            "MULTIPLE_FACES",
            "NO_MATCH",
            "MAINTENANCE_MODE_ACTIVE",
            "ONLINE_RESTORE_DISABLED",
        }

        self.assertTrue(required.issubset(ERROR_DEFINITIONS))


if __name__ == "__main__":
    unittest.main()
