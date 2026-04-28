"""
人脸识别 API 服务 - FastAPI 实现
启动：uvicorn main:app --host 0.0.0.0 --port 8000 --reload
文档：http://localhost:8000/docs

环境变量：
- FACE_MODEL: 模型名（默认 buffalo_l）
- FACE_DET_SIZE: 检测尺寸（默认 640）
- FACE_DB_PATH: 数据库路径（默认 faces.db）
- FACE_FORCE_CPU: 强制 CPU（设为 1 时启用，调试用）
- FACE_API_KEY: API 鉴权密钥（不设则不鉴权）
"""
import base64
import os
import time
from typing import Optional

import cv2
import numpy as np
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
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

# CORS：开发期全开放，生产环境收敛
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- 启动时加载（模块级单例）----------
FORCE_CPU = os.getenv("FACE_FORCE_CPU", "0") == "1"
engine = FaceEngine(force_cpu=FORCE_CPU)
db = FaceDB()  # 自动读 FACE_DB_PATH 环境变量


# ---------- 可选鉴权 ----------
API_KEY = os.getenv("FACE_API_KEY", "")


async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """如果环境变量没设 FACE_API_KEY，则不强制校验（开发模式）"""
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, "Invalid or missing X-API-Key")


# ---------- 辅助函数 ----------
def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "无效图像，无法解码")
    return img


def decode_base64(b64_str: str) -> np.ndarray:
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    try:
        image_bytes = base64.b64decode(b64_str)
    except Exception:
        raise HTTPException(400, "Base64 解码失败")
    return decode_image_bytes(image_bytes)


def strip_embedding(face: dict) -> dict:
    return {k: v for k, v in face.items() if k != "embedding"}


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
    name: str = Field(..., description="人员姓名或标识", examples=["张三"])
    image: str = Field(..., description="单人人脸照片的 Base64")
    metadata: Optional[dict] = Field(
        None,
        description="自定义元数据，任意 JSON 对象",
        examples=[{"department": "研发部", "employee_id": "E001"}],
    )


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
    name: str
    message: str


class MatchItem(BaseModel):
    id: str
    name: str
    similarity: float
    metadata: dict


class SearchResp(BaseModel):
    query_face_count: int
    threshold: float
    matches: list[MatchItem]
    elapsed_ms: float


# ---------- 路由分组 tag ----------
TAG_SYSTEM = "系统"
TAG_DETECT = "人脸检测"
TAG_COMPARE = "人脸比对"
TAG_DB = "人脸库管理"
TAG_SEARCH = "人脸搜索"


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
        raise HTTPException(400, "至少一张图未检测到人脸")

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
    """图片中必须只有一张脸"""
    img = decode_base64(req.image)
    faces = engine.analyze(img)

    if not faces:
        raise HTTPException(400, "未检测到人脸")
    if len(faces) > 1:
        raise HTTPException(400, f"检测到 {len(faces)} 张人脸，注册需单人图片")

    face_id = db.add(req.name, faces[0]["embedding"], req.metadata)
    return {"id": face_id, "name": req.name, "message": "注册成功"}


@app.get(
    "/faces",
    tags=[TAG_DB],
    summary="列出所有已注册人脸",
    dependencies=[Depends(verify_api_key)],
)
def list_faces():
    return {"count": db.count(), "faces": db.list_all()}


@app.delete(
    "/faces/{face_id}",
    tags=[TAG_DB],
    summary="删除指定人脸",
    dependencies=[Depends(verify_api_key)],
)
def delete_face(face_id: str):
    if db.remove(face_id):
        return {"deleted": face_id}
    raise HTTPException(404, "该 ID 不存在")


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
        raise HTTPException(400, "未检测到人脸")

    faces.sort(key=lambda f: f["det_score"], reverse=True)
    results = db.search(faces[0]["embedding"], req.top_k, req.threshold)
    elapsed = (time.perf_counter() - t0) * 1000

    return {
        "query_face_count": len(faces),
        "threshold": req.threshold,
        "matches": results,
        "elapsed_ms": round(elapsed, 2),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
