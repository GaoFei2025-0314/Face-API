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

    def test_env_list_returns_copy_of_default(self):
        default = ["*"]
        with patch.dict(os.environ, {}, clear=True):
            result = env_list("FACE_CORS_ORIGINS", default)

        result.append("http://changed.local")

        self.assertEqual(default, ["*"])
        self.assertEqual(env_list("FACE_CORS_ORIGINS", default), ["*"])

    def test_load_settings_defaults_to_cpu(self):
        with patch.dict(os.environ, {"FACE_DB_PATH": "faces.db"}, clear=True):
            settings = load_settings()

        self.assertFalse(settings.use_gpu)
        self.assertTrue(settings.force_cpu)
        self.assertEqual(settings.face_model, "buffalo_l")
        self.assertEqual(settings.face_det_size, 640)

    def test_challenge_max_frames_default_is_not_lower_than_min_frames(self):
        with patch.dict(
            os.environ,
            {"FACE_DB_PATH": "faces.db", "FACE_CHALLENGE_MIN_FRAMES": "40"},
            clear=True,
        ):
            settings = load_settings()

        self.assertEqual(settings.face_challenge_min_frames, 40)
        self.assertEqual(settings.face_challenge_max_frames, 40)

    def test_challenge_max_frames_rejects_value_lower_than_min_frames(self):
        with patch.dict(
            os.environ,
            {
                "FACE_DB_PATH": "faces.db",
                "FACE_CHALLENGE_MIN_FRAMES": "40",
                "FACE_CHALLENGE_MAX_FRAMES": "30",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "FACE_CHALLENGE_MAX_FRAMES 必须大于等于 40"):
                load_settings()

    def test_anti_spoof_defaults_keep_lightweight_user_experience(self):
        with patch.dict(os.environ, {"FACE_DB_PATH": "faces.db"}, clear=True):
            settings = load_settings()

        self.assertTrue(settings.face_anti_spoof_enabled)
        self.assertEqual(settings.face_anti_spoof_block_level, "high")
        self.assertEqual(settings.face_anti_spoof_medium_action, "review")
        self.assertEqual(settings.face_anti_spoof_min_frame_variation, 5.0)
        self.assertEqual(settings.face_anti_spoof_min_frame_delta, 1.0)
        self.assertEqual(settings.face_anti_spoof_min_face_motion, 0.015)
        self.assertEqual(settings.face_anti_spoof_min_sharpness_variation, 1.0)
        self.assertEqual(settings.face_liveness_min_brightness_variation, 5.0)

    def test_float_settings_reject_invalid_values_with_context(self):
        with patch.dict(
            os.environ,
            {"FACE_DB_PATH": "faces.db", "FACE_MIN_FACE_SHARPNESS": "abc"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "FACE_MIN_FACE_SHARPNESS 必须是数字"):
                load_settings()

    def test_liveness_and_anti_spoof_numeric_thresholds_are_configurable(self):
        with patch.dict(
            os.environ,
            {
                "FACE_DB_PATH": "faces.db",
                "FACE_ANTI_SPOOF_MIN_FRAME_DELTA": "2.5",
                "FACE_LIVENESS_MIN_BRIGHTNESS_VARIATION": "8.5",
            },
            clear=True,
        ):
            settings = load_settings()

        self.assertEqual(settings.face_anti_spoof_min_frame_delta, 2.5)
        self.assertEqual(settings.face_liveness_min_brightness_variation, 8.5)

    def test_anti_spoof_rejects_invalid_policy_values(self):
        with patch.dict(
            os.environ,
            {
                "FACE_DB_PATH": "faces.db",
                "FACE_ANTI_SPOOF_BLOCK_LEVEL": "medium",
                "FACE_ANTI_SPOOF_MEDIUM_ACTION": "block",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "FACE_ANTI_SPOOF_BLOCK_LEVEL"):
                load_settings()

    def test_production_rejects_wildcard_cors_origins(self):
        with patch.dict(
            os.environ,
            {
                "FACE_ENV": "production",
                "FACE_API_KEY": "secret",
                "FACE_DB_PATH": "faces.db",
                "FACE_CORS_ORIGINS": "*",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "FACE_CORS_ORIGINS"):
                load_settings()


if __name__ == "__main__":
    unittest.main()
