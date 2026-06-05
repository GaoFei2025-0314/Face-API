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
import json
import logging
import os
from pathlib import Path
import time
from typing import Optional

import cv2
import numpy as np
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

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


def env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


def setup_app_logger(log_path: str) -> logging.Logger:
    logger = logging.getLogger("face_api")
    logger.setLevel(logging.INFO)
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()
    logger.propagate = False
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger


def sanitize_log_payload(payload: dict) -> dict:
    safe = {}
    for key, value in payload.items():
        if key.lower() in SENSITIVE_LOG_FIELDS:
            safe[key] = "***"
        else:
            safe[key] = value
    return safe


def log_event(event: str, **payload) -> dict:
    safe = sanitize_log_payload({"event": event, "ts": round(time.time(), 3), **payload})
    try:
        app_logger.info(json.dumps(safe, ensure_ascii=False, default=str))
    except NameError:
        pass
    return safe

# ---------- 启动时加载（模块级单例）----------
ENVIRONMENT = os.getenv("FACE_ENV", "development").strip().lower() or "development"
PRODUCTION_LIKE = ENVIRONMENT in {"prod", "production"}
API_KEY = os.getenv("FACE_API_KEY", "")
USE_GPU = env_bool("FACE_USE_GPU", False)
FORCE_CPU = env_bool("FACE_FORCE_CPU", False) or not USE_GPU
FACE_MODEL = os.getenv("FACE_MODEL", "buffalo_l")
FACE_DET_SIZE = env_int("FACE_DET_SIZE", 640, 1)
DEFAULT_MAX_IMAGE_BYTES = 8 * 1024 * 1024
DEFAULT_MAX_BASE64_IMAGE_CHARS = ((DEFAULT_MAX_IMAGE_BYTES + 2) // 3) * 4 + 256
MAX_BASE64_IMAGE_CHARS = env_int("FACE_MAX_BASE64_CHARS", DEFAULT_MAX_BASE64_IMAGE_CHARS, 1)
MAX_IMAGE_BYTES = env_int("FACE_MAX_IMAGE_BYTES", DEFAULT_MAX_IMAGE_BYTES, 1)
MAX_IMAGE_PIXELS = env_int("FACE_MAX_IMAGE_PIXELS", 4_096_000, 1)
DB_PATH = os.getenv("FACE_DB_PATH", "faces.db")
LOG_PATH = os.getenv("FACE_LOG_PATH", "logs/face_api.log")
CORS_ORIGINS = env_list("FACE_CORS_ORIGINS", ["*"])
DUPLICATE_POLICY = os.getenv("FACE_DUPLICATE_POLICY", "allow").strip().lower() or "allow"
MIN_REGISTER_DET_SCORE = float(os.getenv("FACE_MIN_REGISTER_DET_SCORE", "0.5"))
MIN_REGISTER_FACE_PIXELS = env_int("FACE_MIN_REGISTER_FACE_PIXELS", 2500, 1)
MIN_REGISTER_BRIGHTNESS = float(os.getenv("FACE_MIN_REGISTER_BRIGHTNESS", "30"))
MAX_REGISTER_BRIGHTNESS = float(os.getenv("FACE_MAX_REGISTER_BRIGHTNESS", "225"))
if PRODUCTION_LIKE and not API_KEY:
    raise RuntimeError("FACE_API_KEY 在 production 环境不能为空")
if DUPLICATE_POLICY not in {"allow", "reject", "replace"}:
    raise RuntimeError("FACE_DUPLICATE_POLICY 必须是 allow、reject 或 replace")
db_dir = Path(DB_PATH).expanduser().resolve().parent
if not db_dir.exists() or not os.access(db_dir, os.W_OK):
    raise RuntimeError(f"FACE_DB_PATH 目录不可写：{db_dir}")
app_logger = setup_app_logger(LOG_PATH)
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


ERROR_DEFINITIONS = {
    "AUTH_INVALID_OR_MISSING": {
        "message": "认证失败",
        "reason": "请求缺少有效的 X-API-Key，请检查前端或业务系统的接口配置",
    },
    "IMAGE_DECODE_FAILED": {
        "message": "无效图像，无法解码",
        "reason": "上传内容不是有效图片，或 Base64 内容损坏，请重新选择 jpg、png 或 webp 图片",
    },
    "VALIDATION_ERROR": {
        "message": "请求参数校验失败",
        "reason": "请求参数格式或取值不符合接口要求，请检查请求体、路径参数或查询参数",
    },
    "IMAGE_TOO_LARGE": {
        "message": "图片数据过大",
        "reason": "上传图片超过服务允许的大小限制，请压缩图片或降低分辨率后重试",
    },
    "IMAGE_PIXELS_TOO_LARGE": {
        "message": "图片分辨率过高",
        "reason": "图片宽高像素总数超过服务限制，请降低分辨率后重试",
    },
    "NO_FACE": {
        "message": "未检测到人脸",
        "reason": "图片中没有检测到可用于识别的人脸，请调整光线、角度或距离后重试",
    },
    "MULTIPLE_FACES": {
        "message": "检测到多张人脸",
        "reason": "当前接口要求图片中只能有一张人脸，请使用单人照片后重试",
    },
    "INVALID_EMBEDDING_RESPONSE": {
        "message": "人脸特征提取失败",
        "reason": "模型返回的人脸特征不完整，请检查模型文件、推理环境或输入图片质量",
    },
    "INVALID_USERNAME": {
        "message": "username 不能为空",
        "reason": "注册人脸时必须传入非空 username，用于和业务系统用户记录对应",
    },
    "FACE_QUALITY_LOW": {
        "message": "人脸质量不符合注册要求",
        "reason": "注册照片的人脸置信度、大小或亮度不符合要求，请重新拍摄清晰的单人正脸照片",
    },
    "DUPLICATE_FACE_USER": {
        "message": "该用户已注册人脸",
        "reason": "当前重复注册策略不允许同一 user_id 注册多条人脸记录，请先删除或调整重复注册策略",
    },
    "FACE_ID_NOT_FOUND": {
        "message": "该 ID 不存在",
        "reason": "请求删除的人脸 ID 不在当前本地人脸库中",
    },
    "NO_MATCH": {
        "message": "身份验证失败，未匹配到有效用户",
        "reason": "当前人脸与底库记录的相似度未达到登录阈值，请重新拍摄或先完成人脸注册",
    },
    "INVALID_MATCH_RECORD": {
        "message": "身份验证失败，匹配记录无效",
        "reason": "底库命中了人脸记录，但该记录缺少有效 username 或 user_id，请检查人脸库数据",
    },
}


def error_detail(code: str, message: Optional[str] = None, reason: Optional[str] = None) -> dict:
    definition = ERROR_DEFINITIONS.get(code, {})
    return {
        "code": code,
        "message": message or definition.get("message", "请求失败"),
        "reason": reason or definition.get("reason", "请求处理失败，请检查请求参数或联系服务维护人员"),
    }


def raise_api_error(status_code: int, code: str, message: Optional[str] = None, reason: Optional[str] = None):
    raise HTTPException(status_code=status_code, detail=error_detail(code, message, reason))


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


def validate_register_quality(face: dict, image: np.ndarray) -> None:
    det_score = float(face.get("det_score") or 0)
    bbox = face.get("bbox") or [0, 0, 0, 0]
    width = max(float(bbox[2]) - float(bbox[0]), 0)
    height = max(float(bbox[3]) - float(bbox[1]), 0)
    face_pixels = width * height
    brightness = float(np.mean(image)) if image.size else 0
    if (
        det_score < MIN_REGISTER_DET_SCORE
        or face_pixels < MIN_REGISTER_FACE_PIXELS
        or brightness < MIN_REGISTER_BRIGHTNESS
        or brightness > MAX_REGISTER_BRIGHTNESS
    ):
        raise_api_error(400, "FACE_QUALITY_LOW")


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
    )


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
) -> None:
    write_login_audit(
        success=False,
        similarity=similarity,
        threshold=threshold,
        failure_reason=code,
        terminal_id=terminal_id,
        state=state,
        elapsed_ms=elapsed_ms,
    )
    raise_api_error(status_code, code, message, reason)


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
        "duplicate_policy": DUPLICATE_POLICY,
        "search_cache": db.get_search_cache_status(),
        "faces_count": db.count(),
    }


# ---------- Pydantic Schema ----------
class Base64ImageReq(BaseModel):
    image: str = Field(
        ...,
        description="图片的 Base64 编码，支持带或不带 data URL 前缀",
        examples=["data:image/jpeg;base64,/9j/4AAQSkZJRg..."],
    )


class CompareReq(BaseModel):
    image1: str = Field(..., description="第一张图的 Base64")
    image2: str = Field(..., description="第二张图的 Base64")
    threshold: float = Field(0.5, ge=0.0, le=1.0, description="判定同人的阈值")


class SearchReq(BaseModel):
    image: str = Field(..., description="查询图片的 Base64")
    top_k: int = Field(5, ge=1, le=100, description="返回最相似的前 N 个")
    threshold: float = Field(0.5, ge=0.0, le=1.0, description="最低相似度过滤")


class RegisterReq(BaseModel):
    user_id: Optional[int] = Field(None, description="外部用户表 users.id", examples=[10001])
    username: str = Field(..., description="外部用户表 users.username", examples=["zhangsan"])
    image: str = Field(..., description="单人人脸照片的 Base64")
    metadata: Optional[dict] = Field(
        None,
        description="自定义元数据，不作为登录认证主依据",
        examples=[{"department": "研发部", "tenant_id": "000000"}],
    )


class FaceLoginReq(BaseModel):
    image: str = Field(..., description="摄像头截图或照片的 Base64")
    terminal_id: Optional[str] = Field(None, description="终端标识，用于审计和业务侧追踪")
    state: Optional[str] = Field(None, description="前端请求追踪标识")
    threshold: float = Field(0.6, ge=0.0, le=1.0, description="认证匹配阈值，默认 0.60")


# ---------- 响应模型 ----------
class FaceInfo(BaseModel):
    bbox: list = Field(..., description="人脸框 [x1, y1, x2, y2]")
    det_score: float = Field(..., description="检测置信度 0~1")
    landmarks: Optional[list] = Field(None, description="5 个关键点坐标")
    gender: str = Field(..., description="性别 M/F")
    age: int = Field(..., description="估计年龄")


class DetectResp(BaseModel):
    count: int
    faces: list[FaceInfo]
    elapsed_ms: float = Field(..., description="服务端处理耗时（毫秒）")


class CompareResp(BaseModel):
    similarity: float
    threshold: float
    is_same_person: bool
    elapsed_ms: float


class RegisterResp(BaseModel):
    id: str
    user_id: Optional[int] = None
    username: str
    message: str


class MatchItem(BaseModel):
    id: str
    user_id: Optional[int] = None
    username: str
    similarity: float
    metadata: dict


class SearchResp(BaseModel):
    query_face_count: int
    threshold: float
    matches: list[MatchItem]
    elapsed_ms: float


class FaceLoginMatch(BaseModel):
    user_id: Optional[int] = None
    username: str


class FaceLoginResp(BaseModel):
    authenticated: bool
    message: str
    match: FaceLoginMatch
    state: Optional[str] = None
    elapsed_ms: float


class ExtractResp(BaseModel):
    count: int
    code: str
    message: str
    embedding: list[float]
    face: dict
    elapsed_ms: float


class SystemStatusResp(BaseModel):
    status: str
    device: str
    providers: list[str]
    model: str
    det_size: list[int]
    auth_enabled: bool
    force_cpu: bool
    use_gpu: bool
    environment: str
    cors_origins: list[str]
    db_path: str
    log_path: str
    duplicate_policy: str
    search_cache: dict
    faces_count: int


class EffectiveConfigResp(BaseModel):
    face_login_threshold: float
    auth_enabled: bool
    force_cpu: bool
    use_gpu: bool
    environment: str
    cors_origins: list[str]
    log_path: str
    duplicate_policy: str
    model: str
    det_size: list[int]
    db_path: str
    max_base64_image_chars: int
    max_image_bytes: int
    max_image_pixels: int


class LoginAuditItem(BaseModel):
    id: str
    success: bool
    matched_user_id: Optional[int] = None
    matched_username: Optional[str] = None
    similarity: Optional[float] = None
    threshold: Optional[float] = None
    failure_reason: Optional[str] = None
    terminal_id: Optional[str] = None
    state: Optional[str] = None
    elapsed_ms: Optional[float] = None
    created_at: Optional[str] = None


class LoginAuditListResp(BaseModel):
    items: list[LoginAuditItem]


class LoginAuditSummaryResp(BaseModel):
    total: int
    success_count: int
    failure_count: int
    success_rate: float


# ---------- 路由分组 tag ----------
TAG_SYSTEM = "系统"
TAG_DETECT = "人脸检测"
TAG_COMPARE = "人脸比对"
TAG_DB = "人脸库管理"
TAG_SEARCH = "人脸搜索"
TAG_AUTH = "认证"


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
        "device": engine.device,
        "faces": db.count(),
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
        "duplicate_policy": DUPLICATE_POLICY,
        "model": FACE_MODEL,
        "det_size": [FACE_DET_SIZE, FACE_DET_SIZE],
        "db_path": DB_PATH,
        "max_base64_image_chars": MAX_BASE64_IMAGE_CHARS,
        "max_image_bytes": MAX_IMAGE_BYTES,
        "max_image_pixels": MAX_IMAGE_PIXELS,
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
    img = decode_base64(req.image)
    faces = engine.analyze(img)

    if not faces:
        raise_api_error(400, "NO_FACE")
    if len(faces) > 1:
        raise_api_error(400, "MULTIPLE_FACES", f"检测到 {len(faces)} 张人脸，注册需单人图片")

    username = req.username.strip()
    if not username:
        raise_api_error(400, "INVALID_USERNAME")

    validate_register_quality(faces[0], img)
    if req.user_id is not None and DUPLICATE_POLICY != "allow":
        existing = db.list_by_user_id(req.user_id)
        if existing and DUPLICATE_POLICY == "reject":
            raise_api_error(409, "DUPLICATE_FACE_USER")
        if existing and DUPLICATE_POLICY == "replace":
            db.remove_by_user_id(req.user_id)

    face_id = db.add(username, faces[0]["embedding"], req.metadata, req.user_id)
    log_event("face_registered", user_id=req.user_id, username=username, face_id=face_id)
    return {
        "id": face_id,
        "user_id": req.user_id,
        "username": username,
        "message": "注册成功",
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
    if db.remove(face_id):
        return {"deleted": face_id}
    raise_api_error(404, "FACE_ID_NOT_FOUND")


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
    t0 = time.perf_counter()
    img = decode_base64(req.image)
    try:
        face = get_single_face_or_raise(img)
    except HTTPException as exc:
        reason = exc.detail.get("reason") if isinstance(exc.detail, dict) else None
        raise_with_audit(
            status_code=exc.status_code,
            code=exc.detail["code"],
            message=exc.detail["message"],
            reason=reason,
            threshold=normalize_auth_threshold(req.threshold),
            terminal_id=req.terminal_id,
            state=req.state,
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )

    threshold = normalize_auth_threshold(req.threshold)
    results = db.search(face["embedding"], top_k=1, threshold=threshold)
    if not results:
        raise_with_audit(
            status_code=403,
            code="NO_MATCH",
            message="身份验证失败，未匹配到有效用户",
            threshold=threshold,
            terminal_id=req.terminal_id,
            state=req.state,
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )

    best_match = results[0]
    username = str(best_match.get("username") or "").strip()
    if not username:
        raise_with_audit(
            status_code=403,
            code="INVALID_MATCH_RECORD",
            message="身份验证失败，匹配记录无效",
            threshold=threshold,
            terminal_id=req.terminal_id,
            state=req.state,
            similarity=best_match.get("similarity"),
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )

    elapsed = (time.perf_counter() - t0) * 1000
    write_login_audit(
        success=True,
        matched_user_id=best_match.get("user_id"),
        matched_username=username,
        similarity=best_match.get("similarity"),
        threshold=threshold,
        terminal_id=req.terminal_id,
        state=req.state,
        elapsed_ms=round(elapsed, 2),
    )
    return {
        "authenticated": True,
        "message": "认证成功",
        "match": {
            "user_id": best_match.get("user_id"),
            "username": username,
        },
        "state": req.state,
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
