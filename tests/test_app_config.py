import os
import unittest
from unittest.mock import patch

from app_config import env_bool, env_int, env_list, load_settings


class AppConfigTest(unittest.TestCase):
    def test_env_bool_accepts_truthy_values(self):
        with patch.dict(os.environ, {"FACE_USE_GPU": "true"}, clear=False):
            self.assertTrue(env_bool("FACE_USE_GPU", False))

    def test_env_bool_uses_default_when_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(env_bool("FACE_USE_GPU", False))

    def test_env_int_rejects_invalid_integer(self):
        with patch.dict(os.environ, {"FACE_DET_SIZE": "abc"}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "FACE_DET_SIZE 必须是整数"):
                env_int("FACE_DET_SIZE", 640, 1)

    def test_env_list_splits_comma_values(self):
        with patch.dict(os.environ, {"FACE_CORS_ORIGINS": "http://a.local, http://b.local"}, clear=False):
            self.assertEqual(
                env_list("FACE_CORS_ORIGINS", ["*"]),
                ["http://a.local", "http://b.local"],
            )

    def test_load_settings_defaults_to_cpu(self):
        with patch.dict(os.environ, {"FACE_DB_PATH": "faces.db"}, clear=True):
            settings = load_settings()

        self.assertFalse(settings.use_gpu)
        self.assertTrue(settings.force_cpu)
        self.assertEqual(settings.face_model, "buffalo_l")
        self.assertEqual(settings.face_det_size, 640)


if __name__ == "__main__":
    unittest.main()
