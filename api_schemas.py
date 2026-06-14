"""Pydantic request and response models for face_api."""
from typing import Optional

from pydantic import BaseModel, Field


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
    terminal_id: str = Field(..., description="终端标识，用于审计和现场排障")
    challenge_id: Optional[str] = Field(None, description="通过活体 challenge 后获得的一次性 ID")
    username: str = Field(..., description="外部用户表 users.username", examples=["zhangsan"])
    image: str = Field(..., description="单人人脸照片的 Base64")
    metadata: Optional[dict] = Field(
        None,
        description="自定义元数据，不作为登录认证主依据",
        examples=[{"department": "研发部", "tenant_id": "000000"}],
    )


class FaceLoginReq(BaseModel):
    image: str = Field(..., description="摄像头截图或照片的 Base64")
    terminal_id: str = Field(..., description="终端标识，用于审计和业务侧追踪")
    challenge_id: Optional[str] = Field(None, description="通过活体 challenge 后获得的一次性 ID")
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
    quality_metrics: dict


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
    quality_metrics: dict
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
    log_rotation: dict
    duplicate_policy: str
    search_cache: dict
    liveness: dict
    recognition_policy: dict
    maintenance_mode: bool
    faces_count: int


class EffectiveConfigResp(BaseModel):
    face_login_threshold: float
    auth_enabled: bool
    force_cpu: bool
    use_gpu: bool
    environment: str
    cors_origins: list[str]
    log_path: str
    log_rotation: dict
    duplicate_policy: str
    model: str
    det_size: list[int]
    db_path: str
    max_base64_image_chars: int
    max_image_bytes: int
    max_image_pixels: int
    liveness: dict
    recognition_policy: dict
    search_target: dict


class PerformanceScalePlanResp(BaseModel):
    benchmark: dict
    index_status: dict
    bulk_manifest: dict


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
    liveness_status: Optional[str] = None
    liveness_reason: Optional[str] = None
    quality_metrics: Optional[dict] = None
    created_at: Optional[str] = None


class LoginAuditListResp(BaseModel):
    items: list[LoginAuditItem]


class LoginAuditSummaryResp(BaseModel):
    total: int
    success_count: int
    failure_count: int
    success_rate: float


class LivenessChallengeCreateReq(BaseModel):
    purpose: str = Field(..., description="用途：login 或 register")
    terminal_id: str = Field(..., description="终端标识")
    action: str = Field("blink", description="动作类型，第一版稳定支持 blink")


class LivenessChallengeCreateResp(BaseModel):
    challenge_id: str
    purpose: str
    terminal_id: str
    action: str
    expires_in_seconds: int
    action_window_seconds: int
    status: str


class LivenessChallengeSubmitReq(BaseModel):
    challenge_id: str
    purpose: str = Field(..., description="用途：login 或 register")
    terminal_id: str = Field(..., description="终端标识")
    frames: list[str] = Field(..., description="连续图片帧 Base64，眨眼挑战要求 10 到 30 帧")


class LivenessChallengeSubmitResp(BaseModel):
    challenge_id: str
    status: str
    passed: bool
    message: str
    elapsed_ms: float
    reason: Optional[str] = None
    result_reason: Optional[str] = None


class MaintenanceModeReq(BaseModel):
    enabled: bool


class ConfirmReq(BaseModel):
    confirm: bool = Field(False, description="高风险操作必须传 true")


class RestoreReq(BaseModel):
    backup_dir: str
    confirm: bool = Field(False, description="恢复数据库必须二次确认")
