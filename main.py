"""
人脸识别 API 服务 - FastAPI 实现
启动：uvicorn main:app --host 0.0.0.0 --port 8000 --reload
文档：http://localhost:8000/docs

环境变量：
- FACE_MODEL: 模型名（默认 buffalo_l）
- FACE_DET_SIZE: 检测尺寸（默认 640）
- FACE_DB_PATH: 数据库路径（默认 faces.db）
- FACE_USE_GPU: 启用 GPU 推理（设为 1 时优先使用 CUDA）
- FACE_FORCE_CPU: 强制 CPU（设为 1 时覆盖 FACE_USE_GPU）
- FACE_API_KEY: API 鉴权密钥（不设则不鉴权）
"""
import base64
from datetime import datetime, timezone
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import secrets
import uuid
from pathlib import Path
import time
from typing import Optional

import cv2
import numpy as np
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse

from api_errors import ERROR_DEFINITIONS, error_detail, raise_api_error
from app_config import load_settings
import admin_ops
from api_schemas import (
    Base64ImageReq,
    CompareReq,
    CompareResp,
    ConfirmReq,
    DetectResp,
    EffectiveConfigResp,
    ExtractResp,
    FaceInfo,
    FaceLoginReq,
    FaceLoginResp,
    LivenessChallengeCreateReq,
    LivenessChallengeCreateResp,
    LivenessChallengeSubmitReq,
    LivenessChallengeSubmitResp,
    LoginAuditListResp,
    LoginAuditSummaryResp,
    MaintenanceModeReq,
    PerformanceScalePlanResp,
    RegisterReq,
    RegisterResp,
    RestoreReq,
    SearchReq,
    SearchResp,
    SystemStatusResp,
)
from face_engine import FaceEngine
from storage import FaceDB

# ---------- App 初始化 ----------
app = FastAPI(
    title="人脸识别 API",
    version="1.0",
    description="""
## 简介
基于 InsightFace 封装的人脸识别 REST API，支持：
- 人脸检测（bbox / 关键点 / 性别 / 年龄）
- 1:1 人脸比对
- 1:N 人脸搜索
- 人脸库增删查（SQLite 持久化）

## 阈值约定
所有相似度为余弦相似度，取值范围 [-1, 1]。经验阈值：
- `>= 0.60` 高置信度同人
- `0.45 ~ 0.60` 建议结合业务判断
- `< 0.45` 通常非同人

## 图片入参格式
- 文件上传接口：`multipart/form-data` 的 `file` 字段
- Base64 接口：支持带或不带 `data:image/xxx;base64,` 前缀

## 错误码
| 状态码 | 含义 |
|---|---|
| 400 | 参数错误 / 图片无法解码 / 未检测到人脸 |
| 401 | 未提供或错误的 API Key（仅启用鉴权时） |
| 404 | 资源不存在 |
| 422 | 请求体格式错误 |
| 500 | 服务内部错误 |
    """,
    contact={"name": "API 维护", "email": "you@example.com"},
)

SENSITIVE_LOG_FIELDS = {"api_key", "x_api_key", "embedding", "image", "image1", "image2"}


def setup_app_logger(log_path: str, max_bytes: int, backup_count: int) -> logging.Logger:
    logger = logging.getLogger("face_api")
    logger.setLevel(logging.INFO)
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()
    logger.propagate = False
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger


def sanitize_log_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise TypeError(f"sanitize_log_payload only accepts dict payloads, got {type(payload).__name__}")

    def sanitize_value(value):
        if isinstance(value, dict):
            return {
                key: "***" if str(key).lower() in SENSITIVE_LOG_FIELDS else sanitize_value(nested_value)
                for key, nested_value in value.items()
            }
        if isinstance(value, list):
            return [sanitize_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(sanitize_value(item) for item in value)
        return value

    return sanitize_value(payload)


def log_event(event: str, **payload) -> dict:
    safe = sanitize_log_payload({"event": event, "ts": round(time.time(), 3), **payload})
    try:
        app_logger.info(json.dumps(safe, ensure_ascii=False, default=str))
    except NameError:
        pass
    return safe

# ---------- 启动时加载（模块级单例）----------
settings = load_settings()
ENVIRONMENT = settings.environment
PRODUCTION_LIKE = settings.production_like
API_KEY = settings.api_key
USE_GPU = settings.use_gpu
FORCE_CPU = settings.force_cpu
FACE_MODEL = settings.face_model
FACE_DET_SIZE = settings.face_det_size
MAX_BASE64_IMAGE_CHARS = settings.max_base64_image_chars
MAX_IMAGE_BYTES = settings.max_image_bytes
MAX_IMAGE_PIXELS = settings.max_image_pixels
DB_PATH = settings.db_path
LOG_PATH = settings.log_path
LOG_MAX_BYTES = settings.log_max_bytes
LOG_BACKUP_COUNT = settings.log_backup_count
CORS_ORIGINS = settings.cors_origins
DUPLICATE_POLICY = settings.duplicate_policy
MIN_REGISTER_DET_SCORE = settings.min_register_det_score
MIN_REGISTER_FACE_PIXELS = settings.min_register_face_pixels
MIN_REGISTER_BRIGHTNESS = settings.min_register_brightness
MAX_REGISTER_BRIGHTNESS = settings.max_register_brightness
MIN_LOGIN_DET_SCORE = settings.min_login_det_score
MIN_LOGIN_FACE_PIXELS = settings.min_login_face_pixels
MIN_FACE_SHARPNESS = settings.min_face_sharpness
FACE_LOGIN_LIVENESS_ENABLED = settings.face_login_liveness_enabled
FACE_REGISTER_LIVENESS_ENABLED = settings.face_register_liveness_enabled
FACE_CHALLENGE_TTL_SECONDS = settings.face_challenge_ttl_seconds
FACE_CHALLENGE_ACTION_SECONDS = settings.face_challenge_action_seconds
FACE_LIVENESS_MIN_BRIGHTNESS_VARIATION = settings.face_liveness_min_brightness_variation
FACE_CHALLENGE_MIN_FRAMES = settings.face_challenge_min_frames
FACE_CHALLENGE_MAX_FRAMES = settings.face_challenge_max_frames
FACE_CHALLENGE_ACTIONS = settings.face_challenge_actions
FACE_ANTI_SPOOF_ENABLED = settings.face_anti_spoof_enabled
FACE_ANTI_SPOOF_BLOCK_LEVEL = settings.face_anti_spoof_block_level
FACE_ANTI_SPOOF_MEDIUM_ACTION = settings.face_anti_spoof_medium_action
FACE_ANTI_SPOOF_RETRY_TOKEN_TTL_SECONDS = settings.face_anti_spoof_retry_token_ttl_seconds
FACE_ANTI_SPOOF_MIN_FRAME_VARIATION = settings.face_anti_spoof_min_frame_variation
FACE_ANTI_SPOOF_MIN_FRAME_DELTA = settings.face_anti_spoof_min_frame_delta
FACE_ANTI_SPOOF_MIN_FACE_MOTION = settings.face_anti_spoof_min_face_motion
FACE_ANTI_SPOOF_MIN_SHARPNESS_VARIATION = settings.face_anti_spoof_min_sharpness_variation
FACE_DEFAULT_POLICY_PROFILE = settings.face_default_policy_profile
FACE_TERMINAL_POLICY_MAP = settings.face_terminal_policy_map
MAINTENANCE_MODE_FILE = settings.maintenance_mode_file
ALLOW_ONLINE_RESTORE = settings.allow_online_restore
app_logger = setup_app_logger(LOG_PATH, LOG_MAX_BYTES, LOG_BACKUP_COUNT)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
log_event(
    "startup_config",
    environment=ENVIRONMENT,
    use_gpu=USE_GPU,
    force_cpu=FORCE_CPU,
    model=FACE_MODEL,
    det_size=FACE_DET_SIZE,
    db_path=DB_PATH,
    cors_origins=CORS_ORIGINS,
)
engine = FaceEngine(force_cpu=FORCE_CPU, use_gpu=USE_GPU)
db = FaceDB()  # 自动读 FACE_DB_PATH 环境变量


# ---------- 可选鉴权 ----------


async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """如果环境变量没设 FACE_API_KEY，则不强制校验（开发模式）"""
    if API_KEY and x_api_key != API_KEY:
        raise_api_error(401, "AUTH_INVALID_OR_MISSING")


async def require_api_key(x_api_key: Optional[str] = Header(None)):
    """认证接口必须显式配置并提供 API Key。"""
    if not API_KEY or x_api_key != API_KEY:
        raise_api_error(401, "AUTH_INVALID_OR_MISSING")


# ---------- 辅助函数 ----------
def validate_image_bytes(image_bytes: bytes) -> None:
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise_api_error(413, "IMAGE_TOO_LARGE")


def validate_decoded_image(image: np.ndarray) -> None:
    height, width = image.shape[:2]
    if height * width > MAX_IMAGE_PIXELS:
        raise_api_error(413, "IMAGE_PIXELS_TOO_LARGE")


def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    validate_image_bytes(image_bytes)
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise_api_error(400, "IMAGE_DECODE_FAILED")
    validate_decoded_image(img)
    return img


def decode_base64(b64_str: str) -> np.ndarray:
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    if len(b64_str) > MAX_BASE64_IMAGE_CHARS:
        raise_api_error(413, "IMAGE_TOO_LARGE")
    try:
        image_bytes = base64.b64decode(b64_str, validate=True)
    except Exception:
        raise_api_error(400, "IMAGE_DECODE_FAILED")
    return decode_image_bytes(image_bytes)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(_request, _exc):
    return JSONResponse(status_code=422, content={"detail": error_detail("VALIDATION_ERROR")})


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    t0 = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        log_event(
            "request",
            method=request.method,
            route=request.url.path,
            status_code=status_code,
            elapsed_ms=elapsed,
        )


def normalize_auth_threshold(threshold: float) -> float:
    """认证场景收紧最低阈值，允许业务侧传入更严格的值。"""
    return max(threshold, 0.55)


def get_single_face_or_raise(image: np.ndarray) -> dict:
    faces = engine.analyze(image)
    if not faces:
        raise_api_error(400, "NO_FACE")
    if len(faces) > 1:
        raise_api_error(400, "MULTIPLE_FACES")

    face = faces[0]
    embedding = face.get("embedding")
    if not hasattr(embedding, "__len__") or len(embedding) != 512:
        raise_api_error(500, "INVALID_EMBEDDING_RESPONSE")
    return face


def strip_embedding(face: dict) -> dict:
    return {k: v for k, v in face.items() if k != "embedding"}


def compute_face_quality(face: dict, image: np.ndarray) -> dict:
    det_score = float(face.get("det_score") or 0)
    bbox = face.get("bbox") or [0, 0, 0, 0]
    width = max(float(bbox[2]) - float(bbox[0]), 0)
    height = max(float(bbox[3]) - float(bbox[1]), 0)
    face_pixels = width * height
    image_pixels = 0
    brightness = None
    sharpness = None
    if isinstance(image, np.ndarray) and image.size:
        image_pixels = int(image.shape[0] * image.shape[1])
        brightness = round(float(np.mean(image)), 2)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        sharpness = round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 2)
    return {
        "det_score": round(det_score, 4),
        "face_width": round(width, 2),
        "face_height": round(height, 2),
        "face_pixels": round(face_pixels, 2),
        "image_pixels": image_pixels,
        "face_area_ratio": round(face_pixels / image_pixels, 6) if image_pixels else None,
        "brightness": brightness,
        "sharpness": sharpness,
    }


def quality_failure_code(metrics: dict, *, flow: str) -> Optional[str]:
    min_det_score = MIN_REGISTER_DET_SCORE if flow == "register" else MIN_LOGIN_DET_SCORE
    min_face_pixels = MIN_REGISTER_FACE_PIXELS if flow == "register" else MIN_LOGIN_FACE_PIXELS
    if metrics["det_score"] < min_det_score:
        return "FACE_DET_SCORE_LOW"
    if metrics.get("image_pixels") and metrics["face_pixels"] < min_face_pixels:
        return "FACE_TOO_SMALL"
    brightness = metrics.get("brightness")
    if brightness is not None and brightness < MIN_REGISTER_BRIGHTNESS:
        return "FACE_TOO_DARK"
    if brightness is not None and brightness > MAX_REGISTER_BRIGHTNESS:
        return "FACE_TOO_BRIGHT"
    sharpness = metrics.get("sharpness")
    if sharpness is not None and sharpness < MIN_FACE_SHARPNESS:
        return "FACE_BLURRY"
    return None


def validate_face_quality(face: dict, image: np.ndarray, *, flow: str) -> dict:
    metrics = compute_face_quality(face, image)
    failure_code = quality_failure_code(metrics, flow=flow)
    if failure_code:
        raise_api_error(400, failure_code)
    return metrics


def validate_register_quality(face: dict, image: np.ndarray) -> dict:
    return validate_face_quality(face, image, flow="register")


def require_terminal_id_value(terminal_id: Optional[str]) -> str:
    value = (terminal_id or "").strip()
    if not value:
        raise_api_error(400, "TERMINAL_ID_REQUIRED")
    return value


def is_maintenance_mode() -> bool:
    return admin_ops.is_maintenance_mode(MAINTENANCE_MODE_FILE)


def set_maintenance_mode(enabled: bool) -> None:
    admin_ops.set_maintenance_mode(enabled, MAINTENANCE_MODE_FILE)


def ensure_not_maintenance():
    admin_ops.ensure_not_maintenance(MAINTENANCE_MODE_FILE)


def require_confirm(confirm: bool):
    admin_ops.require_confirm(confirm)


def parse_terminal_policy_map() -> dict[str, str]:
    mapping = {}
    if not FACE_TERMINAL_POLICY_MAP:
        return mapping
    for item in FACE_TERMINAL_POLICY_MAP.split(","):
        if ":" not in item:
            continue
        terminal_id, profile = item.split(":", 1)
        terminal_id = terminal_id.strip()
        profile = profile.strip()
        if terminal_id and profile:
            mapping[terminal_id] = profile
    return mapping


def get_policy_for_terminal(terminal_id: Optional[str]) -> dict:
    mapping = parse_terminal_policy_map()
    profile = mapping.get((terminal_id or "").strip(), FACE_DEFAULT_POLICY_PROFILE)
    thresholds = {
        "default": 0.55,
        "strict": 0.65,
        "balanced": 0.60,
        "permissive": 0.55,
    }
    return {
        "profile": profile,
        "terminal_id": terminal_id,
        "threshold": thresholds.get(profile, thresholds["default"]),
        "quality_thresholds": {
            "min_login_det_score": MIN_LOGIN_DET_SCORE,
            "min_login_face_pixels": MIN_LOGIN_FACE_PIXELS,
            "min_register_det_score": MIN_REGISTER_DET_SCORE,
            "min_register_face_pixels": MIN_REGISTER_FACE_PIXELS,
            "min_brightness": MIN_REGISTER_BRIGHTNESS,
            "max_brightness": MAX_REGISTER_BRIGHTNESS,
            "min_sharpness": MIN_FACE_SHARPNESS,
        },
        "auto_apply": False,
        "manual_review_required": True,
    }


def get_liveness_policy() -> dict:
    return {
        "login_enabled": FACE_LOGIN_LIVENESS_ENABLED,
        "register_enabled": FACE_REGISTER_LIVENESS_ENABLED,
        "mode": "single-image-plus-challenge-bound-face",
        "challenge_ttl_seconds": FACE_CHALLENGE_TTL_SECONDS,
        "action_window_seconds": FACE_CHALLENGE_ACTION_SECONDS,
        "supported_actions": FACE_CHALLENGE_ACTIONS,
        "default_action": "blink",
        "frame_count": {
            "min": FACE_CHALLENGE_MIN_FRAMES,
            "max": FACE_CHALLENGE_MAX_FRAMES,
        },
        "min_brightness_variation": FACE_LIVENESS_MIN_BRIGHTNESS_VARIATION,
    }


def get_anti_spoof_policy() -> dict:
    return {
        "enabled": FACE_ANTI_SPOOF_ENABLED,
        "mode": "lightweight-risk-score",
        "default_block_level": FACE_ANTI_SPOOF_BLOCK_LEVEL,
        "medium_action": FACE_ANTI_SPOOF_MEDIUM_ACTION,
        "thresholds": {
            "min_frame_variation": FACE_ANTI_SPOOF_MIN_FRAME_VARIATION,
            "min_frame_delta": FACE_ANTI_SPOOF_MIN_FRAME_DELTA,
            "min_face_motion": FACE_ANTI_SPOOF_MIN_FACE_MOTION,
            "min_sharpness_variation": FACE_ANTI_SPOOF_MIN_SHARPNESS_VARIATION,
        },
        "retry": {
            "medium_max_retries": 1,
            "token_ttl_seconds": FACE_ANTI_SPOOF_RETRY_TOKEN_TTL_SECONDS,
        },
        "sample_types": [
            "real_person",
            "printed_photo",
            "phone_screen",
            "desktop_screen",
            "video_replay",
        ],
    }


def liveness_failure_reason_text(reason: str) -> str:
    if reason == "anti_spoof_high_risk":
        return "疑似翻拍或静态画面，请重新面对摄像头"
    if reason == "no_frames":
        return "没有采集到可用于活体检测的连续帧，请重新打开摄像头后重试"
    if reason.startswith("brightness_variation="):
        return "活体动作幅度不够，请看着预览画面眨眼，并轻微前后移动或调整光线后重试"
    if reason.startswith("sample_") and "_face_count=" in reason:
        return "连续帧中没有稳定检测到单人脸，请让脸保持在预览画面中央，避免遮挡或离开画面"
    if reason == "sample_face_mismatch":
        return "连续帧中的人脸不一致，请保持同一个人完成活体动作"
    return "活体动作未通过，请看着预览画面重新完成动作"


def liveness_failure_audit_code(reason: str) -> str:
    if reason == "anti_spoof_high_risk":
        return "ANTI_SPOOF_HIGH_RISK"
    return "LIVENESS_CHALLENGE_FAILED"


def _frame_sharpness(image: np.ndarray) -> Optional[float]:
    if not isinstance(image, np.ndarray) or not image.size:
        return None
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _face_box_motion(sampled_faces: Optional[list[dict]], decoded_frames: list[np.ndarray]) -> Optional[float]:
    if not sampled_faces or len(sampled_faces) < 2:
        return None
    boxes = [face.get("bbox") for face in sampled_faces if face.get("bbox") and len(face.get("bbox")) >= 4]
    if len(boxes) < 2:
        return None
    centers = []
    areas = []
    for box in boxes:
        x1, y1, x2, y2 = [float(value) for value in box[:4]]
        width = max(x2 - x1, 0.0)
        height = max(y2 - y1, 0.0)
        centers.append(((x1 + x2) / 2.0, (y1 + y2) / 2.0))
        areas.append(width * height)
    if decoded_frames and isinstance(decoded_frames[0], np.ndarray) and decoded_frames[0].size:
        image_height, image_width = decoded_frames[0].shape[:2]
        image_diag = max((image_width ** 2 + image_height ** 2) ** 0.5, 1.0)
    else:
        image_diag = 1.0
    center_motion = 0.0
    base_x, base_y = centers[0]
    for x, y in centers[1:]:
        center_motion = max(center_motion, (((x - base_x) ** 2 + (y - base_y) ** 2) ** 0.5) / image_diag)
    max_area = max(areas) if areas else 0.0
    area_motion = ((max(areas) - min(areas)) / max_area) if max_area else 0.0
    return round(max(center_motion, area_motion), 6)


def evaluate_anti_spoof_risk(decoded_frames: list[np.ndarray], sampled_faces: Optional[list[dict]] = None) -> dict:
    if not FACE_ANTI_SPOOF_ENABLED:
        return {
            "level": "low",
            "reasons": ["anti_spoof_disabled"],
            "action": "allow",
            "message": "防翻拍检测未启用",
        }
    if not decoded_frames:
        return {
            "level": "medium",
            "reasons": ["insufficient_signal"],
            "action": FACE_ANTI_SPOOF_MEDIUM_ACTION,
            "message": "画面信号不足，请重新面对摄像头",
            "metrics": {},
        }

    brightness_values = [float(np.mean(image)) if isinstance(image, np.ndarray) and image.size else 0.0 for image in decoded_frames]
    sharpness_values = [
        value for value in (_frame_sharpness(image) for image in decoded_frames)
        if value is not None
    ]
    frame_variation = max(brightness_values) - min(brightness_values) if brightness_values else 0.0
    sharpness_variation = max(sharpness_values) - min(sharpness_values) if sharpness_values else 0.0
    max_frame_delta = 0.0
    max_frame_delta_texture = 0.0
    for left, right in zip(decoded_frames, decoded_frames[1:]):
        if isinstance(left, np.ndarray) and isinstance(right, np.ndarray) and left.shape == right.shape:
            delta = np.abs(left.astype(np.float32) - right.astype(np.float32))
            max_frame_delta = max(max_frame_delta, float(np.mean(delta)))
            max_frame_delta_texture = max(max_frame_delta_texture, float(np.std(delta)))
    face_motion = _face_box_motion(sampled_faces, decoded_frames)

    reasons = []
    if max_frame_delta < FACE_ANTI_SPOOF_MIN_FRAME_DELTA:
        reasons.append("repeated_frames")
    if frame_variation < FACE_ANTI_SPOOF_MIN_FRAME_VARIATION:
        reasons.append("low_frame_variation")
    if face_motion is not None and face_motion < FACE_ANTI_SPOOF_MIN_FACE_MOTION:
        reasons.append("static_face_box")
    if (
        max_frame_delta >= FACE_ANTI_SPOOF_MIN_FRAME_DELTA
        and frame_variation >= FACE_ANTI_SPOOF_MIN_FRAME_VARIATION
        and max_frame_delta_texture < max(1.0, FACE_ANTI_SPOOF_MIN_SHARPNESS_VARIATION)
    ):
        reasons.append("uniform_frame_delta")
    if sharpness_variation < FACE_ANTI_SPOOF_MIN_SHARPNESS_VARIATION and frame_variation < FACE_ANTI_SPOOF_MIN_FRAME_VARIATION:
        reasons.append("poor_capture_quality")

    metrics = {
        "frame_variation": round(frame_variation, 2),
        "max_frame_delta": round(max_frame_delta, 2),
        "max_frame_delta_texture": round(max_frame_delta_texture, 2),
        "face_box_motion": face_motion,
        "sharpness_variation": round(sharpness_variation, 2),
    }
    critical_reasons = {"repeated_frames", "low_frame_variation", "static_face_box"}
    critical_count = len(critical_reasons.intersection(reasons))
    if "static_face_box" in reasons and critical_count >= 2:
        return {
            "level": "high",
            "reasons": reasons,
            "action": "block",
            "message": "疑似翻拍或静态画面，请重新面对摄像头",
            "metrics": metrics,
        }
    if reasons:
        return {
            "level": "medium",
            "reasons": reasons,
            "action": FACE_ANTI_SPOOF_MEDIUM_ACTION,
            "message": "画面变化不足，请调整光线、脸部位置后重试",
            "metrics": metrics,
        }
    return {
        "level": "low",
        "reasons": ["normal_motion"],
        "action": "allow",
        "message": "活体检测通过",
        "metrics": metrics,
    }


def _sample_faces_for_anti_spoof(decoded_frames: list[np.ndarray]) -> list[dict]:
    if not decoded_frames:
        return []
    sample_indexes = sorted({0, len(decoded_frames) // 2, len(decoded_frames) - 1})
    sampled_faces = []
    for index in sample_indexes:
        faces = engine.analyze(decoded_frames[index])
        if len(faces) == 1:
            sampled_faces.append(faces[0])
    return sampled_faces


def evaluate_blink_frames(frames: list[str]) -> tuple[bool, str, Optional[list[float]], dict]:
    if not (FACE_CHALLENGE_MIN_FRAMES <= len(frames) <= FACE_CHALLENGE_MAX_FRAMES):
        raise_api_error(400, "LIVENESS_FRAME_COUNT_INVALID")
    brightness_values = []
    decoded_frames = []
    for frame in frames:
        img = decode_base64(frame)
        decoded_frames.append(img)
        brightness_values.append(float(np.mean(img)) if img.size else 0)
    if not brightness_values:
        risk = evaluate_anti_spoof_risk(decoded_frames)
        return False, "no_frames", None, risk
    variation = max(brightness_values) - min(brightness_values)
    if variation < FACE_LIVENESS_MIN_BRIGHTNESS_VARIATION:
        sampled_faces = _sample_faces_for_anti_spoof(decoded_frames)
        risk = evaluate_anti_spoof_risk(decoded_frames, sampled_faces)
        if risk["level"] == "high":
            return False, "anti_spoof_high_risk", None, risk
        return False, f"brightness_variation={round(variation, 2)}", None, risk

    sample_indexes = sorted({0, len(decoded_frames) // 2, len(decoded_frames) - 1})
    sampled_faces = []
    for index in sample_indexes:
        faces = engine.analyze(decoded_frames[index])
        if len(faces) != 1:
            risk = evaluate_anti_spoof_risk(decoded_frames, sampled_faces)
            return False, f"sample_{index}_face_count={len(faces)}", None, risk
        sampled_faces.append(faces[0])

    base_embedding = sampled_faces[0]["embedding"]
    for face in sampled_faces[1:]:
        if engine.cosine_similarity(base_embedding, face["embedding"]) < 0.5:
            risk = evaluate_anti_spoof_risk(decoded_frames, sampled_faces)
            return False, "sample_face_mismatch", None, risk
    risk = evaluate_anti_spoof_risk(decoded_frames, sampled_faces)
    if risk["level"] == "high":
        return False, "anti_spoof_high_risk", None, risk
    return True, f"brightness_variation={round(variation, 2)}", base_embedding, risk


def validate_liveness_for_flow(
    purpose: str,
    challenge_id: Optional[str],
    terminal_id: str,
    face_embedding,
) -> dict:
    enabled = FACE_LOGIN_LIVENESS_ENABLED if purpose == "login" else FACE_REGISTER_LIVENESS_ENABLED
    if not enabled:
        return {"status": "disabled", "reason": "disabled"}
    if not challenge_id:
        raise_api_error(403, "LIVENESS_CHALLENGE_REQUIRED")
    ok, reason, challenge = db.consume_liveness_challenge(
        challenge_id=challenge_id,
        purpose=purpose,
        terminal_id=terminal_id,
        now=time.time(),
    )
    if not ok:
        risk = challenge.get("anti_spoof_risk") if challenge else None
        if risk and risk.get("level") == "high":
            raise_api_error(403, "ANTI_SPOOF_HIGH_RISK")
        raise_api_error(403, "LIVENESS_CHALLENGE_INVALID", reason="请面对摄像头并完成眨眼后重试")
    challenge_embedding = challenge.get("face_embedding") if challenge else None
    if challenge_embedding is None:
        raise_api_error(403, "LIVENESS_CHALLENGE_INVALID", reason="活体挑战缺少人脸绑定信息，请重新挑战")
    if engine.cosine_similarity(challenge_embedding, face_embedding) < 0.5:
        raise_api_error(403, "LIVENESS_CHALLENGE_INVALID", reason="活体挑战人脸与当前图片不一致，请重新挑战")
    return {
        "status": "passed",
        "reason": reason,
        "challenge": challenge,
        "anti_spoof_risk": challenge.get("anti_spoof_risk") if challenge else None,
    }


def ensure_backup_subdir(backup_dir: Path) -> Path:
    return admin_ops.ensure_backup_subdir(backup_dir)


def copy_existing_db_files(target_dir: Path) -> list[str]:
    return admin_ops.copy_existing_db_files(target_dir, db_path=DB_PATH, db=db)


def restore_db_files(backup_dir: Path) -> list[str]:
    return admin_ops.restore_db_files(backup_dir, db_path=DB_PATH, project_root=Path(__file__).parent)


def get_available_providers() -> list[str]:
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        return list(providers)
    except Exception:
        return []


def write_login_audit(
    *,
    success: bool,
    matched_user_id: Optional[int] = None,
    matched_username: Optional[str] = None,
    similarity: Optional[float] = None,
    threshold: Optional[float] = None,
    failure_reason: Optional[str] = None,
    terminal_id: Optional[str] = None,
    state: Optional[str] = None,
    elapsed_ms: Optional[float] = None,
    liveness_status: Optional[str] = None,
    liveness_reason: Optional[str] = None,
    quality_metrics: Optional[dict] = None,
    anti_spoof_risk: Optional[dict] = None,
) -> str:
    return db.add_login_audit(
        success=success,
        matched_user_id=matched_user_id,
        matched_username=matched_username,
        similarity=similarity,
        threshold=threshold,
        failure_reason=failure_reason,
        terminal_id=terminal_id,
        state=state,
        elapsed_ms=elapsed_ms,
        liveness_status=liveness_status,
        liveness_reason=liveness_reason,
        quality_metrics=quality_metrics,
        anti_spoof_risk=anti_spoof_risk,
    )


def _risk_retry_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utc_iso_from_epoch(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(epoch_seconds, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def issue_risk_retry_token(*, terminal_id: str, retry_group_id: str, now: Optional[float] = None) -> dict:
    issued_at = time.time() if now is None else now
    expires_at = issued_at + FACE_ANTI_SPOOF_RETRY_TOKEN_TTL_SECONDS
    raw_token = secrets.token_urlsafe(32)
    stored = db.add_risk_retry_token(
        token_hash=_risk_retry_token_hash(raw_token),
        terminal_id=terminal_id,
        retry_group_id=retry_group_id,
        expires_at=expires_at,
        now=issued_at,
    )
    if not stored:
        raise RuntimeError("risk retry token could not be stored")
    return {
        "risk_retry_token": raw_token,
        "expires_at": _utc_iso_from_epoch(expires_at),
        "remaining_attempts": 1,
    }


def consume_risk_retry_token_for_login(*, token: str, terminal_id: str, now: Optional[float] = None) -> tuple[bool, str]:
    checked_at = time.time() if now is None else now
    ok, reason, _record = db.consume_risk_retry_token(
        token_hash=_risk_retry_token_hash(token),
        terminal_id=terminal_id,
        now=checked_at,
    )
    return ok, reason


def raise_with_audit(
    *,
    status_code: int,
    code: str,
    message: str,
    reason: Optional[str] = None,
    threshold: Optional[float] = None,
    terminal_id: Optional[str] = None,
    state: Optional[str] = None,
    similarity: Optional[float] = None,
    elapsed_ms: Optional[float] = None,
    liveness_status: Optional[str] = None,
    liveness_reason: Optional[str] = None,
    quality_metrics: Optional[dict] = None,
    anti_spoof_risk: Optional[dict] = None,
    detail_extra: Optional[dict] = None,
) -> None:
    write_login_audit(
        success=False,
        similarity=similarity,
        threshold=threshold,
        failure_reason=code,
        terminal_id=terminal_id,
        state=state,
        elapsed_ms=elapsed_ms,
        liveness_status=liveness_status,
        liveness_reason=liveness_reason,
        quality_metrics=quality_metrics,
        anti_spoof_risk=anti_spoof_risk,
    )
    raise_api_error(status_code, code, message, reason, extra=detail_extra)


def get_system_status() -> dict:
    return {
        "status": "ok",
        "device": engine.device,
        "providers": get_available_providers(),
        "model": FACE_MODEL,
        "det_size": [FACE_DET_SIZE, FACE_DET_SIZE],
        "auth_enabled": bool(API_KEY),
        "force_cpu": FORCE_CPU,
        "use_gpu": USE_GPU,
        "environment": ENVIRONMENT,
        "cors_origins": CORS_ORIGINS,
        "db_path": DB_PATH,
        "log_path": LOG_PATH,
        "log_rotation": {
            "max_bytes": LOG_MAX_BYTES,
            "backup_count": LOG_BACKUP_COUNT,
        },
        "duplicate_policy": DUPLICATE_POLICY,
        "search_cache": db.get_search_cache_summary(),
        "liveness": get_liveness_policy(),
        "anti_spoof": get_anti_spoof_policy(),
        "recognition_policy": get_policy_for_terminal(None),
        "maintenance_mode": is_maintenance_mode(),
        "faces_count": db.count(),
    }


# ---------- 路由分组 tag ----------
TAG_SYSTEM = "系统"
TAG_DETECT = "人脸检测"
TAG_COMPARE = "人脸比对"
TAG_DB = "人脸库管理"
TAG_SEARCH = "人脸搜索"
TAG_AUTH = "认证"
TAG_PERFORMANCE = "性能与规模化"


# ---------- 系统 ----------
@app.get("/", tags=[TAG_SYSTEM], summary="服务信息")
def root():
    return {
        "service": "Face Recognition API",
        "version": "1.0",
        "device": engine.device,
        "registered_faces": db.count(),
        "auth_enabled": bool(API_KEY),
        "docs": "/docs",
    }


@app.get("/health", tags=[TAG_SYSTEM], summary="健康检查")
def health():
    """前端可以用这个接口判断后端是否可用，无需鉴权"""
    return {
        "status": "ok",
        "service": "face_api",
    }


@app.get("/system/status", tags=[TAG_SYSTEM], summary="系统运行状态", response_model=SystemStatusResp, dependencies=[Depends(require_api_key)])
def system_status():
    return get_system_status()


@app.get(
    "/config/effective",
    tags=[TAG_SYSTEM],
    summary="当前生效配置",
    response_model=EffectiveConfigResp,
    dependencies=[Depends(require_api_key)],
)
def effective_config():
    return {
        "face_login_threshold": 0.55,
        "auth_enabled": bool(API_KEY),
        "force_cpu": FORCE_CPU,
        "use_gpu": USE_GPU,
        "environment": ENVIRONMENT,
        "cors_origins": CORS_ORIGINS,
        "log_path": LOG_PATH,
        "log_rotation": {
            "max_bytes": LOG_MAX_BYTES,
            "backup_count": LOG_BACKUP_COUNT,
        },
        "duplicate_policy": DUPLICATE_POLICY,
        "model": FACE_MODEL,
        "det_size": [FACE_DET_SIZE, FACE_DET_SIZE],
        "db_path": DB_PATH,
        "max_base64_image_chars": MAX_BASE64_IMAGE_CHARS,
        "max_image_bytes": MAX_IMAGE_BYTES,
        "max_image_pixels": MAX_IMAGE_PIXELS,
        "liveness": get_liveness_policy(),
        "anti_spoof": get_anti_spoof_policy(),
        "recognition_policy": get_policy_for_terminal(None),
        "search_target": {
            "mode": "exact",
            "target_record_count": 50000,
            "target_latency_ms": 1000,
        },
    }


@app.get("/admin.html", tags=[TAG_SYSTEM], summary="运维控制台页面")
def admin_page():
    return FileResponse("admin.html")


@app.get(
    "/policy/tuning-summary",
    tags=[TAG_SYSTEM],
    summary="识别策略调参建议",
    dependencies=[Depends(require_api_key)],
)
def policy_tuning_summary(limit: int = 100, terminal_id: Optional[str] = None):
    items = db.list_login_audits(limit, terminal_id=terminal_id)
    similarities = [item["similarity"] for item in items if item.get("similarity") is not None]
    failure_counts: dict[str, int] = {}
    quality_failure_count = 0
    liveness_failure_count = 0
    no_match_count = 0
    for item in items:
        reason = item.get("failure_reason")
        if reason:
            failure_counts[reason] = failure_counts.get(reason, 0) + 1
            if reason.startswith("FACE_"):
                quality_failure_count += 1
            if reason in {"NO_MATCH"}:
                no_match_count += 1
        if item.get("liveness_status") == "failed":
            liveness_failure_count += 1
    success_similarities = [
        item["similarity"]
        for item in items
        if item.get("success") and item.get("similarity") is not None
    ]
    failed_similarities = [
        item["similarity"]
        for item in items
        if not item.get("success") and item.get("similarity") is not None
    ]
    sample_sufficient = len(items) >= 30 and len(similarities) >= 10
    risk_notes = []
    if not sample_sufficient:
        recommendation = "样本不足，暂不建议调整阈值；请先积累至少 30 条该 terminal 的 login audit"
    else:
        avg_similarity = sum(similarities) / len(similarities)
        low_success = min(success_similarities) if success_similarities else None
        high_failure = max(failed_similarities) if failed_similarities else None
        if high_failure is not None and high_failure >= get_policy_for_terminal(terminal_id)["threshold"] - 0.03:
            risk_notes.append("false accept 风险：失败样本相似度接近当前阈值，不能自动降低阈值")
        if low_success is not None and low_success < get_policy_for_terminal(terminal_id)["threshold"] + 0.05:
            risk_notes.append("false reject 风险：成功样本相似度贴近阈值，需复核采集质量和底库照片")
        if quality_failure_count >= max(3, len(items) // 5):
            risk_notes.append("质量风险：质量失败占比较高，优先检查光照、焦距和摄像头安装")
        if liveness_failure_count >= max(3, len(items) // 5):
            risk_notes.append("活体风险：活体失败占比较高，优先检查摄像头帧率和前端动作引导")
        recommendation = "保持当前阈值，继续观察" if avg_similarity >= 0.7 and not risk_notes else "建议人工复核阈值、现场采集质量和底库照片"
    return {
        "policy": get_policy_for_terminal(terminal_id),
        "sample_count": len(items),
        "similarity_count": len(similarities),
        "sample_sufficient": sample_sufficient,
        "failure_counts": failure_counts,
        "quality_failure_count": quality_failure_count,
        "liveness_failure_count": liveness_failure_count,
        "no_match_count": no_match_count,
        "false_accept_risk": "false accept 风险需要人工复核，系统不会自动降低阈值",
        "false_reject_risk": "false reject 风险需要结合成功/失败样本和质量指标复核",
        "risk_notes": risk_notes,
        "auto_apply": False,
        "manual_review_required": True,
        "recommendation": recommendation,
    }


@app.get(
    "/search/benchmark-summary",
    tags=[TAG_SEARCH],
    summary="搜索基准目标摘要",
    dependencies=[Depends(require_api_key)],
)
def search_benchmark_summary():
    return db.get_search_benchmark_summary()


@app.get(
    "/search/index-status",
    tags=[TAG_PERFORMANCE],
    summary="搜索 index 状态与回退策略",
    dependencies=[Depends(require_api_key)],
)
def search_index_status():
    return db.get_search_index_status()


@app.get(
    "/performance/scale-plan",
    tags=[TAG_PERFORMANCE],
    summary="5万人脸性能与规模化方案",
    response_model=PerformanceScalePlanResp,
    dependencies=[Depends(require_api_key)],
)
def performance_scale_plan():
    return {
        "benchmark": db.get_search_benchmark_summary(),
        "index_status": db.get_search_index_status(),
        "bulk_manifest": {
            "import_manifest_required_fields": ["image_path", "username"],
            "import_manifest_optional_fields": ["user_id", "terminal_id", "metadata"],
            "export_manifest_fields": ["id", "user_id", "username", "metadata", "created_at"],
            "scripts": {
                "benchmark": "scripts/benchmark-scale.py",
                "bulk_manifest": "scripts/bulk-manifest.py",
            },
            "notes": [
                "批量导入先校验清单，再分批注册，失败记录必须输出原因",
                "导出清单不包含 embedding，避免把人脸特征直接暴露给前端或普通业务系统",
            ],
        },
    }


@app.post(
    "/liveness/challenges",
    tags=[TAG_AUTH],
    summary="创建活体 challenge",
    response_model=LivenessChallengeCreateResp,
    dependencies=[Depends(require_api_key)],
)
def create_liveness_challenge(req: LivenessChallengeCreateReq):
    ensure_not_maintenance()
    terminal_id = require_terminal_id_value(req.terminal_id)
    purpose = req.purpose.strip().lower()
    action = req.action.strip().lower()
    if purpose not in {"login", "register"}:
        raise_api_error(422, "VALIDATION_ERROR")
    if action not in FACE_CHALLENGE_ACTIONS:
        raise_api_error(400, "UNSUPPORTED_LIVENESS_ACTION")
    challenge_id = db.add_liveness_challenge(
        purpose=purpose,
        terminal_id=terminal_id,
        action=action,
        expires_at=time.time() + FACE_CHALLENGE_TTL_SECONDS,
        action_window_seconds=FACE_CHALLENGE_ACTION_SECONDS,
    )
    return {
        "challenge_id": challenge_id,
        "purpose": purpose,
        "terminal_id": terminal_id,
        "action": action,
        "expires_in_seconds": FACE_CHALLENGE_TTL_SECONDS,
        "action_window_seconds": FACE_CHALLENGE_ACTION_SECONDS,
        "status": "pending",
    }


@app.post(
    "/liveness/challenges/submit",
    tags=[TAG_AUTH],
    summary="提交活体 challenge 连续帧",
    response_model=LivenessChallengeSubmitResp,
    dependencies=[Depends(require_api_key)],
)
def submit_liveness_challenge(req: LivenessChallengeSubmitReq):
    ensure_not_maintenance()
    t0 = time.perf_counter()
    terminal_id = require_terminal_id_value(req.terminal_id)
    purpose = req.purpose.strip().lower()
    challenge = db.get_liveness_challenge(req.challenge_id)
    if not challenge:
        raise_api_error(404, "LIVENESS_CHALLENGE_INVALID")
    if challenge["purpose"] != purpose or challenge["terminal_id"] != terminal_id:
        raise_api_error(403, "LIVENESS_CHALLENGE_INVALID")
    if challenge["status"] != "pending":
        raise_api_error(403, "LIVENESS_CHALLENGE_INVALID")
    now = time.time()
    if now > float(challenge["expires_at"]):
        db.mark_liveness_challenge_result(req.challenge_id, passed=False, result_reason="expired")
        raise_api_error(403, "LIVENESS_CHALLENGE_INVALID")
    created_at_epoch = challenge.get("created_at_epoch")
    if created_at_epoch is not None:
        action_deadline = float(created_at_epoch) + float(challenge["action_window_seconds"])
        if now > action_deadline:
            db.mark_liveness_challenge_result(
                req.challenge_id,
                passed=False,
                result_reason="action_window_expired",
            )
            raise_api_error(403, "LIVENESS_ACTION_WINDOW_EXPIRED")
    if challenge["action"] != "blink":
        raise_api_error(400, "UNSUPPORTED_LIVENESS_ACTION")
    passed, reason, face_embedding, anti_spoof_risk = evaluate_blink_frames(req.frames)
    db.mark_liveness_challenge_result(
        req.challenge_id,
        passed=passed,
        result_reason=reason,
        face_embedding=face_embedding if passed else None,
        anti_spoof_risk=anti_spoof_risk,
    )
    elapsed = round((time.perf_counter() - t0) * 1000, 2)
    if not passed:
        user_reason = liveness_failure_reason_text(reason)
        log_event("liveness_failed", challenge_id=req.challenge_id, terminal_id=terminal_id, reason=reason)
        if purpose == "login":
            write_login_audit(
                success=False,
                failure_reason=liveness_failure_audit_code(reason),
                terminal_id=terminal_id,
                elapsed_ms=elapsed,
                liveness_status="failed",
                liveness_reason=reason,
                anti_spoof_risk=anti_spoof_risk,
            )
        return {
            "challenge_id": req.challenge_id,
            "status": "failed",
            "passed": False,
            "message": "请面对摄像头并完成眨眼后重试",
            "reason": user_reason,
            "result_reason": reason,
            "anti_spoof_risk": anti_spoof_risk,
            "elapsed_ms": elapsed,
        }
    return {
        "challenge_id": req.challenge_id,
        "status": "passed",
        "passed": True,
        "message": "活体挑战通过",
        "anti_spoof_risk": anti_spoof_risk,
        "elapsed_ms": elapsed,
    }


# ---------- 人脸检测 ----------
@app.post(
    "/detect",
    tags=[TAG_DETECT],
    summary="人脸检测（文件上传）",
    response_model=DetectResp,
    dependencies=[Depends(verify_api_key)],
)
async def detect(file: UploadFile = File(..., description="图片文件，支持 jpg/png/webp")):
    """
    上传图片，返回所有检测到的人脸信息。
    返回字段不包含 512 维特征向量。
    """
    t0 = time.perf_counter()
    img = decode_image_bytes(await file.read())
    faces = engine.analyze(img)
    elapsed = (time.perf_counter() - t0) * 1000
    return {
        "count": len(faces),
        "faces": [strip_embedding(f) for f in faces],
        "elapsed_ms": round(elapsed, 2),
    }


@app.post(
    "/detect/base64",
    tags=[TAG_DETECT],
    summary="人脸检测（Base64）",
    response_model=DetectResp,
    dependencies=[Depends(verify_api_key)],
)
def detect_base64(req: Base64ImageReq):
    """适合前端直接从 canvas / FileReader 拿到的 Base64 数据"""
    t0 = time.perf_counter()
    img = decode_base64(req.image)
    faces = engine.analyze(img)
    elapsed = (time.perf_counter() - t0) * 1000
    return {
        "count": len(faces),
        "faces": [strip_embedding(f) for f in faces],
        "elapsed_ms": round(elapsed, 2),
    }


@app.post(
    "/extract/base64",
    tags=[TAG_DETECT],
    summary="提取单人脸特征（Base64）",
    response_model=ExtractResp,
    dependencies=[Depends(require_api_key)],
)
def extract_base64(req: Base64ImageReq):
    t0 = time.perf_counter()
    img = decode_base64(req.image)
    face = get_single_face_or_raise(img)
    elapsed = (time.perf_counter() - t0) * 1000
    return {
        "count": 1,
        "code": "OK",
        "message": "ok",
        "embedding": face["embedding"],
        "face": strip_embedding(face),
        "elapsed_ms": round(elapsed, 2),
    }


# ---------- 1:1 比对 ----------
@app.post(
    "/compare",
    tags=[TAG_COMPARE],
    summary="1:1 人脸比对",
    response_model=CompareResp,
    dependencies=[Depends(verify_api_key)],
)
def compare(req: CompareReq):
    """传入两张图，判断是否同一个人。"""
    t0 = time.perf_counter()
    img1, img2 = decode_base64(req.image1), decode_base64(req.image2)
    faces1 = engine.analyze(img1)
    faces2 = engine.analyze(img2)

    if not faces1 or not faces2:
        raise_api_error(400, "NO_FACE", "至少一张图未检测到人脸")

    faces1.sort(key=lambda f: f["det_score"], reverse=True)
    faces2.sort(key=lambda f: f["det_score"], reverse=True)

    sim = engine.cosine_similarity(faces1[0]["embedding"], faces2[0]["embedding"])
    elapsed = (time.perf_counter() - t0) * 1000

    return {
        "similarity": sim,
        "threshold": req.threshold,
        "is_same_person": sim >= req.threshold,
        "elapsed_ms": round(elapsed, 2),
    }


# ---------- 人脸库管理 ----------
@app.post(
    "/faces/register",
    tags=[TAG_DB],
    summary="注册人脸到底库",
    response_model=RegisterResp,
    dependencies=[Depends(verify_api_key)],
)
def register(req: RegisterReq):
    """图片中必须只有一张脸，username 必须对应外部用户表。"""
    ensure_not_maintenance()
    terminal_id = require_terminal_id_value(req.terminal_id)
    img = decode_base64(req.image)
    faces = engine.analyze(img)

    if not faces:
        raise_api_error(400, "NO_FACE")
    if len(faces) > 1:
        raise_api_error(400, "MULTIPLE_FACES", f"检测到 {len(faces)} 张人脸，注册需单人图片")

    username = req.username.strip()
    if not username:
        raise_api_error(400, "INVALID_USERNAME")

    try:
        quality_metrics = validate_register_quality(faces[0], img)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        log_event(
            "face_register_quality_failed",
            terminal_id=terminal_id,
            user_id=req.user_id,
            code=detail.get("code"),
            quality_metrics=compute_face_quality(faces[0], img),
        )
        raise
    try:
        liveness_result = validate_liveness_for_flow("register", req.challenge_id, terminal_id, faces[0]["embedding"])
    except HTTPException as exc:
        log_event(
            "face_register_liveness_failed",
            terminal_id=terminal_id,
            user_id=req.user_id,
            code=exc.detail.get("code") if isinstance(exc.detail, dict) else None,
        )
        raise
    if req.user_id is not None and DUPLICATE_POLICY != "allow":
        existing = db.list_by_user_id(req.user_id)
        if existing and DUPLICATE_POLICY == "reject":
            raise_api_error(409, "DUPLICATE_FACE_USER")
        if existing and DUPLICATE_POLICY == "replace":
            db.remove_by_user_id(req.user_id)

    face_id = db.add(username, faces[0]["embedding"], req.metadata, req.user_id)
    log_event(
        "face_registered",
        user_id=req.user_id,
        username=username,
        face_id=face_id,
        terminal_id=terminal_id,
        liveness_status=liveness_result["status"],
        quality_metrics=quality_metrics,
    )
    return {
        "id": face_id,
        "user_id": req.user_id,
        "username": username,
        "message": "注册成功",
        "quality_metrics": quality_metrics,
    }


@app.get(
    "/faces",
    tags=[TAG_DB],
    summary="列出所有已注册人脸",
    dependencies=[Depends(verify_api_key)],
)
def list_faces():
    return {"count": db.count(), "faces": db.list_all()}


@app.get(
    "/faces/by-user/{user_id}",
    tags=[TAG_DB],
    summary="按业务用户 ID 查询人脸",
    dependencies=[Depends(verify_api_key)],
)
def list_faces_by_user(user_id: int):
    faces = db.list_by_user_id(user_id)
    return {"count": len(faces), "faces": faces}


@app.delete(
    "/faces/{face_id}",
    tags=[TAG_DB],
    summary="删除指定人脸",
    dependencies=[Depends(verify_api_key)],
)
def delete_face(face_id: str):
    ensure_not_maintenance()
    if db.remove(face_id):
        return {"deleted": face_id}
    raise_api_error(404, "FACE_ID_NOT_FOUND")


@app.get(
    "/admin/overview",
    tags=[TAG_SYSTEM],
    summary="运维控制台概览",
    dependencies=[Depends(require_api_key)],
)
def admin_overview():
    return {
        "status": get_system_status(),
        "faces": {"count": db.count()},
        "audit_summary": db.get_login_audit_summary(100),
        "maintenance_mode": is_maintenance_mode(),
    }


@app.get(
    "/admin/maintenance",
    tags=[TAG_SYSTEM],
    summary="查看维护模式",
    dependencies=[Depends(require_api_key)],
)
def get_maintenance_mode():
    return {"enabled": is_maintenance_mode()}


@app.post(
    "/admin/maintenance",
    tags=[TAG_SYSTEM],
    summary="设置维护模式",
    dependencies=[Depends(require_api_key)],
)
def update_maintenance_mode(req: MaintenanceModeReq):
    set_maintenance_mode(req.enabled)
    log_event("maintenance_mode_changed", enabled=req.enabled)
    return {"enabled": is_maintenance_mode()}


@app.post(
    "/admin/faces/{face_id}/delete",
    tags=[TAG_SYSTEM],
    summary="控制台确认删除人脸",
    dependencies=[Depends(require_api_key)],
)
def admin_delete_face(face_id: str, req: ConfirmReq):
    ensure_not_maintenance()
    require_confirm(req.confirm)
    if db.remove(face_id):
        log_event("admin_face_deleted", face_id=face_id)
        return {"deleted": face_id}
    raise_api_error(404, "FACE_ID_NOT_FOUND")


@app.post(
    "/admin/backup",
    tags=[TAG_SYSTEM],
    summary="控制台备份数据库",
    dependencies=[Depends(require_api_key)],
)
def admin_backup():
    t0 = time.perf_counter()
    backup_dir = Path("backups") / time.strftime("%Y%m%d-%H%M%S")
    files = copy_existing_db_files(backup_dir)
    elapsed = round((time.perf_counter() - t0) * 1000, 2)
    log_event("admin_backup_created", backup_dir=str(backup_dir), files=files, elapsed_ms=elapsed)
    return {"ok": True, "backup_dir": str(backup_dir), "files": files, "elapsed_ms": elapsed}


@app.post(
    "/admin/restore",
    tags=[TAG_SYSTEM],
    summary="控制台恢复数据库",
    dependencies=[Depends(require_api_key)],
)
def admin_restore(req: RestoreReq):
    if not ALLOW_ONLINE_RESTORE:
        raise_api_error(403, "ONLINE_RESTORE_DISABLED")
    if not is_maintenance_mode():
        raise_api_error(503, "MAINTENANCE_MODE_REQUIRED")
    require_confirm(req.confirm)
    t0 = time.perf_counter()
    db.close_all_connections()
    restored = restore_db_files(Path(req.backup_dir))
    db.invalidate_search_cache()
    elapsed = round((time.perf_counter() - t0) * 1000, 2)
    log_event("admin_db_restored", backup_dir=req.backup_dir, files=restored, elapsed_ms=elapsed)
    return {"ok": True, "restored_files": restored, "elapsed_ms": elapsed}


# ---------- 1:N 搜索 ----------
@app.post(
    "/search",
    tags=[TAG_SEARCH],
    summary="1:N 人脸搜索",
    response_model=SearchResp,
    dependencies=[Depends(verify_api_key)],
)
def search(req: SearchReq):
    """从底库中找出和传入图片最相似的 top_k 个人脸"""
    ensure_not_maintenance()
    t0 = time.perf_counter()
    img = decode_base64(req.image)
    faces = engine.analyze(img)

    if not faces:
        raise_api_error(400, "NO_FACE")

    faces.sort(key=lambda f: f["det_score"], reverse=True)
    results = db.search(faces[0]["embedding"], req.top_k, req.threshold)
    elapsed = (time.perf_counter() - t0) * 1000

    return {
        "query_face_count": len(faces),
        "threshold": req.threshold,
        "matches": results,
        "elapsed_ms": round(elapsed, 2),
    }


@app.post(
    "/auth/face-login",
    tags=[TAG_AUTH],
    summary="轻量人脸登录认证",
    response_model=FaceLoginResp,
    dependencies=[Depends(require_api_key)],
)
def face_login(req: FaceLoginReq):
    """执行单人脸校验和 top-1 检索，返回业务侧可继续处理的认证结果，不签发 token。"""
    ensure_not_maintenance()
    t0 = time.perf_counter()
    terminal_id = require_terminal_id_value(req.terminal_id)
    requested_threshold = normalize_auth_threshold(req.threshold)
    retry_token_consumed = False
    if req.risk_retry_token:
        retry_token_consumed, retry_reason = consume_risk_retry_token_for_login(
            token=req.risk_retry_token,
            terminal_id=terminal_id,
        )
        if not retry_token_consumed:
            raise_with_audit(
                status_code=403,
                code="ANTI_SPOOF_RETRY_TOKEN_INVALID",
                message="中风险重试令牌无效",
                threshold=requested_threshold,
                terminal_id=terminal_id,
                state=req.state,
                elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
                liveness_status="not_checked",
                liveness_reason=retry_reason,
            )
    if FACE_LOGIN_LIVENESS_ENABLED and not req.challenge_id:
        raise_with_audit(
            status_code=403,
            code="LIVENESS_CHALLENGE_REQUIRED",
            message="需要先完成活体挑战",
            threshold=requested_threshold,
            terminal_id=terminal_id,
            state=req.state,
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            liveness_status="failed",
            liveness_reason="LIVENESS_CHALLENGE_REQUIRED",
        )
    img = decode_base64(req.image)
    try:
        face = get_single_face_or_raise(img)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        raise_with_audit(
            status_code=exc.status_code,
            code=detail.get("code", "NO_FACE"),
            message=detail.get("message", "未检测到人脸"),
            reason=detail.get("reason"),
            threshold=requested_threshold,
            terminal_id=terminal_id,
            state=req.state,
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            liveness_status="not_checked",
            liveness_reason="face_invalid",
        )
    try:
        quality_metrics = validate_face_quality(face, img, flow="login")
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        metrics = compute_face_quality(face, img)
        raise_with_audit(
            status_code=exc.status_code,
            code=detail.get("code", "FACE_QUALITY_LOW"),
            message=detail.get("message", "人脸质量不符合登录要求"),
            reason=detail.get("reason"),
            threshold=requested_threshold,
            terminal_id=terminal_id,
            state=req.state,
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            liveness_status="not_checked",
            liveness_reason="quality_failed",
            quality_metrics=metrics,
        )

    try:
        liveness_result = validate_liveness_for_flow("login", req.challenge_id, terminal_id, face["embedding"])
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        anti_spoof_risk = None
        if req.challenge_id:
            challenge = db.get_liveness_challenge(req.challenge_id)
            anti_spoof_risk = challenge.get("anti_spoof_risk") if challenge else None
        raise_with_audit(
            status_code=exc.status_code,
            code=detail.get("code", "LIVENESS_CHALLENGE_INVALID"),
            message=detail.get("message", "活体挑战无效"),
            reason=detail.get("reason"),
            threshold=requested_threshold,
            terminal_id=terminal_id,
            state=req.state,
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            liveness_status="failed",
            liveness_reason=detail.get("code"),
            quality_metrics=quality_metrics,
            anti_spoof_risk=anti_spoof_risk,
        )

    anti_spoof_risk = liveness_result.get("anti_spoof_risk")
    policy = get_policy_for_terminal(terminal_id)
    threshold = max(requested_threshold, policy["threshold"])
    if anti_spoof_risk and anti_spoof_risk.get("level") == "medium":
        if FACE_ANTI_SPOOF_MEDIUM_ACTION == "retry":
            if retry_token_consumed:
                raise_with_audit(
                    status_code=403,
                    code="ANTI_SPOOF_MEDIUM_RETRY_EXHAUSTED",
                    message="中风险重试未通过",
                    threshold=threshold,
                    terminal_id=terminal_id,
                    state=req.state,
                    elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
                    liveness_status=liveness_result["status"],
                    liveness_reason=liveness_result["reason"],
                    quality_metrics=quality_metrics,
                    anti_spoof_risk=anti_spoof_risk,
                )
            retry = issue_risk_retry_token(
                terminal_id=terminal_id,
                retry_group_id=liveness_result["challenge"]["id"],
            )
            raise_with_audit(
                status_code=403,
                code="ANTI_SPOOF_MEDIUM_RETRY_REQUIRED",
                message="检测到中风险，请重试一次",
                threshold=threshold,
                terminal_id=terminal_id,
                state=req.state,
                elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
                liveness_status=liveness_result["status"],
                liveness_reason=liveness_result["reason"],
                quality_metrics=quality_metrics,
                anti_spoof_risk=anti_spoof_risk,
                detail_extra={"retry": retry},
            )
        if FACE_ANTI_SPOOF_MEDIUM_ACTION == "block":
            raise_with_audit(
                status_code=403,
                code="ANTI_SPOOF_MEDIUM_RETRY_EXHAUSTED",
                message="中风险重试未通过",
                threshold=threshold,
                terminal_id=terminal_id,
                state=req.state,
                elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
                liveness_status=liveness_result["status"],
                liveness_reason=liveness_result["reason"],
                quality_metrics=quality_metrics,
                anti_spoof_risk=anti_spoof_risk,
            )
    results = db.search(face["embedding"], top_k=1, threshold=-1.0)
    if not results:
        raise_with_audit(
            status_code=403,
            code="NO_MATCH",
            message="身份验证失败，未匹配到有效用户",
            threshold=threshold,
            terminal_id=terminal_id,
            state=req.state,
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            liveness_status=liveness_result["status"],
            liveness_reason=liveness_result["reason"],
            quality_metrics=quality_metrics,
            anti_spoof_risk=anti_spoof_risk,
        )

    best_match = results[0]
    similarity = best_match.get("similarity")
    if similarity is None or float(similarity) < threshold:
        raise_with_audit(
            status_code=403,
            code="NO_MATCH",
            message="身份验证失败，未匹配到有效用户",
            threshold=threshold,
            terminal_id=terminal_id,
            state=req.state,
            similarity=similarity,
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            liveness_status=liveness_result["status"],
            liveness_reason=liveness_result["reason"],
            quality_metrics=quality_metrics,
            anti_spoof_risk=anti_spoof_risk,
        )
    username = str(best_match.get("username") or "").strip()
    if not username:
        raise_with_audit(
            status_code=403,
            code="INVALID_MATCH_RECORD",
            message="身份验证失败，匹配记录无效",
            threshold=threshold,
            terminal_id=terminal_id,
            state=req.state,
            similarity=best_match.get("similarity"),
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            liveness_status=liveness_result["status"],
            liveness_reason=liveness_result["reason"],
            quality_metrics=quality_metrics,
            anti_spoof_risk=anti_spoof_risk,
        )

    elapsed = (time.perf_counter() - t0) * 1000
    write_login_audit(
        success=True,
        matched_user_id=best_match.get("user_id"),
        matched_username=username,
        similarity=best_match.get("similarity"),
        threshold=threshold,
        terminal_id=terminal_id,
        state=req.state,
        elapsed_ms=round(elapsed, 2),
        liveness_status=liveness_result["status"],
        liveness_reason=liveness_result["reason"],
        quality_metrics=quality_metrics,
        anti_spoof_risk=anti_spoof_risk,
    )
    return {
        "authenticated": True,
        "message": "认证成功",
        "match": {
            "face_id": best_match.get("id"),
            "user_id": best_match.get("user_id"),
            "username": username,
        },
        "similarity": float(best_match.get("similarity")),
        "threshold": threshold,
        "state": req.state,
        "quality_metrics": quality_metrics,
        "anti_spoof_risk": anti_spoof_risk,
        "elapsed_ms": round(elapsed, 2),
    }


@app.get(
    "/audit/login/recent",
    tags=[TAG_AUTH],
    summary="最近登录审计",
    response_model=LoginAuditListResp,
    dependencies=[Depends(require_api_key)],
)
def list_login_audits(limit: int = 20, success: Optional[bool] = None, terminal_id: Optional[str] = None):
    return {"items": db.list_login_audits(limit, success=success, terminal_id=terminal_id)}


@app.get(
    "/audit/login/summary",
    tags=[TAG_AUTH],
    summary="登录审计汇总",
    response_model=LoginAuditSummaryResp,
    dependencies=[Depends(require_api_key)],
)
def login_audit_summary(limit: int = 100, terminal_id: Optional[str] = None):
    return db.get_login_audit_summary(limit, terminal_id=terminal_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
