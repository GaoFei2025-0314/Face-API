"""Runtime configuration helpers for face_api."""
from dataclasses import dataclass
import os
from pathlib import Path


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} 必须是整数，当前值为 {raw!r}") from exc
    if value < minimum:
        raise RuntimeError(f"{name} 必须大于等于 {minimum}，当前值为 {value}")
    return value


def env_float(name: str, default: float, minimum: float = 0.0) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} 必须是数字，当前值为 {raw!r}") from exc
    if value < minimum:
        raise RuntimeError(f"{name} 必须大于等于 {minimum}，当前值为 {value}")
    return value


def env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class RuntimeSettings:
    environment: str
    production_like: bool
    api_key: str
    use_gpu: bool
    force_cpu: bool
    face_model: str
    face_det_size: int
    max_base64_image_chars: int
    max_image_bytes: int
    max_image_pixels: int
    db_path: str
    log_path: str
    log_max_bytes: int
    log_backup_count: int
    cors_origins: list[str]
    duplicate_policy: str
    min_register_det_score: float
    min_register_face_pixels: int
    min_register_brightness: float
    max_register_brightness: float
    min_login_det_score: float
    min_login_face_pixels: int
    min_face_sharpness: float
    face_login_liveness_enabled: bool
    face_register_liveness_enabled: bool
    face_challenge_ttl_seconds: int
    face_challenge_action_seconds: int
    face_liveness_min_brightness_variation: float
    face_challenge_min_frames: int
    face_challenge_max_frames: int
    face_challenge_actions: list[str]
    face_anti_spoof_enabled: bool
    face_anti_spoof_block_level: str
    face_anti_spoof_medium_action: str
    face_anti_spoof_min_frame_variation: float
    face_anti_spoof_min_frame_delta: float
    face_anti_spoof_min_face_motion: float
    face_anti_spoof_min_sharpness_variation: float
    face_default_policy_profile: str
    face_terminal_policy_map: str
    maintenance_mode_file: Path
    allow_online_restore: bool


def load_settings() -> RuntimeSettings:
    environment = os.getenv("FACE_ENV", "development").strip().lower() or "development"
    production_like = environment in {"prod", "production"}
    api_key = os.getenv("FACE_API_KEY", "")
    use_gpu = env_bool("FACE_USE_GPU", False)
    force_cpu = env_bool("FACE_FORCE_CPU", False) or not use_gpu
    default_max_image_bytes = 8 * 1024 * 1024
    default_max_base64_image_chars = ((default_max_image_bytes + 2) // 3) * 4 + 256
    challenge_min_frames = env_int("FACE_CHALLENGE_MIN_FRAMES", 10, 1)
    challenge_max_frames_default = max(30, challenge_min_frames)

    settings = RuntimeSettings(
        environment=environment,
        production_like=production_like,
        api_key=api_key,
        use_gpu=use_gpu,
        force_cpu=force_cpu,
        face_model=os.getenv("FACE_MODEL", "buffalo_l"),
        face_det_size=env_int("FACE_DET_SIZE", 640, 1),
        max_base64_image_chars=env_int("FACE_MAX_BASE64_CHARS", default_max_base64_image_chars, 1),
        max_image_bytes=env_int("FACE_MAX_IMAGE_BYTES", default_max_image_bytes, 1),
        max_image_pixels=env_int("FACE_MAX_IMAGE_PIXELS", 4_096_000, 1),
        db_path=os.getenv("FACE_DB_PATH", "faces.db"),
        log_path=os.getenv("FACE_LOG_PATH", "logs/face_api.log"),
        log_max_bytes=env_int("FACE_LOG_MAX_BYTES", 10 * 1024 * 1024, 1024),
        log_backup_count=env_int("FACE_LOG_BACKUP_COUNT", 5, 1),
        cors_origins=env_list("FACE_CORS_ORIGINS", ["*"]),
        duplicate_policy=os.getenv("FACE_DUPLICATE_POLICY", "allow").strip().lower() or "allow",
        min_register_det_score=env_float("FACE_MIN_REGISTER_DET_SCORE", 0.5, 0.0),
        min_register_face_pixels=env_int("FACE_MIN_REGISTER_FACE_PIXELS", 2500, 1),
        min_register_brightness=env_float("FACE_MIN_REGISTER_BRIGHTNESS", 30.0, 0.0),
        max_register_brightness=env_float("FACE_MAX_REGISTER_BRIGHTNESS", 225.0, 0.0),
        min_login_det_score=env_float("FACE_MIN_LOGIN_DET_SCORE", 0.4, 0.0),
        min_login_face_pixels=env_int("FACE_MIN_LOGIN_FACE_PIXELS", 1600, 1),
        min_face_sharpness=env_float("FACE_MIN_FACE_SHARPNESS", 2.0, 0.0),
        face_login_liveness_enabled=env_bool("FACE_LOGIN_LIVENESS_ENABLED", True),
        face_register_liveness_enabled=env_bool("FACE_REGISTER_LIVENESS_ENABLED", False),
        face_challenge_ttl_seconds=env_int("FACE_CHALLENGE_TTL_SECONDS", 60, 1),
        face_challenge_action_seconds=env_int("FACE_CHALLENGE_ACTION_SECONDS", 10, 1),
        face_liveness_min_brightness_variation=env_float("FACE_LIVENESS_MIN_BRIGHTNESS_VARIATION", 5.0, 0.0),
        face_challenge_min_frames=challenge_min_frames,
        face_challenge_max_frames=env_int(
            "FACE_CHALLENGE_MAX_FRAMES",
            challenge_max_frames_default,
            challenge_min_frames,
        ),
        face_challenge_actions=env_list("FACE_CHALLENGE_ACTIONS", ["blink"]),
        face_anti_spoof_enabled=env_bool("FACE_ANTI_SPOOF_ENABLED", True),
        face_anti_spoof_block_level=os.getenv("FACE_ANTI_SPOOF_BLOCK_LEVEL", "high").strip().lower() or "high",
        face_anti_spoof_medium_action=os.getenv("FACE_ANTI_SPOOF_MEDIUM_ACTION", "review").strip().lower() or "review",
        face_anti_spoof_min_frame_variation=env_float("FACE_ANTI_SPOOF_MIN_FRAME_VARIATION", 5.0, 0.0),
        face_anti_spoof_min_frame_delta=env_float("FACE_ANTI_SPOOF_MIN_FRAME_DELTA", 1.0, 0.0),
        face_anti_spoof_min_face_motion=env_float("FACE_ANTI_SPOOF_MIN_FACE_MOTION", 0.015, 0.0),
        face_anti_spoof_min_sharpness_variation=env_float("FACE_ANTI_SPOOF_MIN_SHARPNESS_VARIATION", 1.0, 0.0),
        face_default_policy_profile=os.getenv("FACE_DEFAULT_POLICY_PROFILE", "default").strip() or "default",
        face_terminal_policy_map=os.getenv("FACE_TERMINAL_POLICY_MAP", "").strip(),
        maintenance_mode_file=Path(os.getenv("FACE_MAINTENANCE_FILE", ".maintenance_mode")),
        allow_online_restore=env_bool("FACE_ALLOW_ONLINE_RESTORE", not production_like),
    )
    validate_settings(settings)
    return settings


def validate_settings(settings: RuntimeSettings) -> None:
    if settings.production_like and not settings.api_key:
        raise RuntimeError("FACE_API_KEY 在 production 环境不能为空")
    if settings.production_like and "*" in settings.cors_origins:
        raise RuntimeError("FACE_CORS_ORIGINS 在 production 环境不能使用 *，请配置明确的前端来源白名单")
    if settings.duplicate_policy not in {"allow", "reject", "replace"}:
        raise RuntimeError("FACE_DUPLICATE_POLICY 必须是 allow、reject 或 replace")
    if "blink" not in settings.face_challenge_actions:
        raise RuntimeError("FACE_CHALLENGE_ACTIONS 第一版必须包含 blink")
    if settings.face_anti_spoof_block_level != "high":
        raise RuntimeError("FACE_ANTI_SPOOF_BLOCK_LEVEL V2.1 仅支持 high，避免轻量防翻拍过度打扰用户")
    if settings.face_anti_spoof_medium_action not in {"review", "retry"}:
        raise RuntimeError("FACE_ANTI_SPOOF_MEDIUM_ACTION 必须是 review 或 retry")
    db_dir = Path(settings.db_path).expanduser().resolve().parent
    if not db_dir.exists() or not os.access(db_dir, os.W_OK):
        raise RuntimeError(f"FACE_DB_PATH 目录不可写：{db_dir}")
