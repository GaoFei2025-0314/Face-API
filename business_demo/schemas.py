from typing import Any, Optional

from pydantic import BaseModel, Field


class BusinessUserCreateReq(BaseModel):
    user_id: str = Field(..., description="业务系统用户 ID")
    username: str = Field(..., description="业务系统用户名")
    display_name: Optional[str] = Field(None, description="显示名称")
    department: Optional[str] = Field(None, description="部门")


class FaceBindingReq(BaseModel):
    image: str
    terminal_id: str
    challenge_id: Optional[str] = None


class LivenessChallengeReq(BaseModel):
    purpose: str = "login"
    terminal_id: str


class LivenessSubmitReq(BaseModel):
    challenge_id: str
    terminal_id: str
    frames: list[str]
    purpose: str = "login"


class FaceLoginReq(BaseModel):
    image: str
    terminal_id: str
    challenge_id: str
    state: Optional[str] = None
    threshold: float = 0.6


class TerminalLoginEventReq(BaseModel):
    event_id: str = Field(..., min_length=1)
    terminal_id: str
    matched_user_id: str
    similarity: Optional[float] = None
    recognized_at_epoch: float
    state: Optional[str] = None
    face_api_result: dict[str, Any] = Field(default_factory=dict)
