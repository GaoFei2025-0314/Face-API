"""Structured API error payloads for face_api."""
from typing import Optional

from fastapi import HTTPException


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
    "FACE_DET_SCORE_LOW": {
        "message": "人脸检测置信度过低",
        "reason": "模型虽然检测到人脸，但置信度偏低，请调整角度、距离或光线后重试",
    },
    "FACE_TOO_SMALL": {
        "message": "人脸区域过小",
        "reason": "人脸在画面中占比太小，请靠近摄像头或调整画面后重试",
    },
    "FACE_TOO_DARK": {
        "message": "画面过暗",
        "reason": "当前图片亮度不足，请补光后重试",
    },
    "FACE_TOO_BRIGHT": {
        "message": "画面过亮",
        "reason": "当前图片过曝，请降低强光或调整摄像头角度后重试",
    },
    "FACE_BLURRY": {
        "message": "画面清晰度不足",
        "reason": "当前图片可能模糊，请保持稳定并重新拍摄",
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
    "TERMINAL_ID_REQUIRED": {
        "message": "terminal_id 不能为空",
        "reason": "注册和登录请求必须携带 terminal_id，便于现场审计和排障",
    },
    "LIVENESS_CHALLENGE_REQUIRED": {
        "message": "需要先完成活体挑战",
        "reason": "请面对摄像头并完成眨眼后重试",
    },
    "LIVENESS_CHALLENGE_INVALID": {
        "message": "活体挑战无效",
        "reason": "请面对摄像头并完成眨眼后重试",
    },
    "LIVENESS_CHALLENGE_FAILED": {
        "message": "活体挑战失败",
        "reason": "请面对摄像头并完成眨眼后重试",
    },
    "LIVENESS_FRAME_COUNT_INVALID": {
        "message": "活体图片帧数量不符合要求",
        "reason": "请面对摄像头并完成眨眼后重试",
    },
    "LIVENESS_ACTION_WINDOW_EXPIRED": {
        "message": "活体动作超时",
        "reason": "活体动作需要在指定时间窗口内完成，请重新创建 challenge 后重试",
    },
    "ANTI_SPOOF_HIGH_RISK": {
        "message": "疑似翻拍风险",
        "reason": "疑似照片、屏幕或静态画面，请面对摄像头重新完成活体检测",
    },
    "ANTI_SPOOF_MEDIUM_RETRY_REQUIRED": {
        "message": "检测到中风险，请重试一次",
        "reason": "当前画面存在轻量防翻拍中风险，请重新面对摄像头完成一次采集",
    },
    "ANTI_SPOOF_MEDIUM_RETRY_EXHAUSTED": {
        "message": "中风险重试未通过",
        "reason": "本次中风险重试机会已使用，请重新发起登录或转人工复核",
    },
    "ANTI_SPOOF_RETRY_TOKEN_INVALID": {
        "message": "中风险重试令牌无效",
        "reason": "重试令牌不存在、已过期、已使用或不属于当前终端，请重新完成人脸登录",
    },
    "UNSUPPORTED_LIVENESS_ACTION": {
        "message": "不支持的活体动作",
        "reason": "第一版活体挑战至少稳定支持眨眼，请检查 action 参数",
    },
    "MAINTENANCE_MODE_ACTIVE": {
        "message": "服务处于维护模式",
        "reason": "当前正在维护数据库，请稍后再试",
    },
    "MAINTENANCE_CONFIRM_REQUIRED": {
        "message": "需要二次确认",
        "reason": "该操作风险较高，请确认后再执行",
    },
    "MAINTENANCE_MODE_REQUIRED": {
        "message": "需要先进入维护模式",
        "reason": "恢复数据库前必须进入维护模式，避免和正常请求并发执行",
    },
    "BACKUP_NOT_FOUND": {
        "message": "备份目录不存在",
        "reason": "指定的备份目录不存在，请检查路径",
    },
    "BACKUP_PATH_INVALID": {
        "message": "备份路径不合法",
        "reason": "恢复路径只能选择项目 backups 目录下的备份",
    },
    "ONLINE_RESTORE_DISABLED": {
        "message": "当前环境不允许在线恢复",
        "reason": "生产环境建议先停止 API 服务，再使用恢复脚本离线恢复数据库",
    },
}


def error_detail(
    code: str,
    message: Optional[str] = None,
    reason: Optional[str] = None,
    extra: Optional[dict] = None,
) -> dict:
    definition = ERROR_DEFINITIONS.get(code, {})
    detail = {
        "code": code,
        "message": message or definition.get("message", "请求失败"),
        "reason": reason or definition.get("reason", "请求处理失败，请检查请求参数或联系服务维护人员"),
    }
    if extra:
        detail.update(extra)
    return detail


def raise_api_error(
    status_code: int,
    code: str,
    message: Optional[str] = None,
    reason: Optional[str] = None,
    extra: Optional[dict] = None,
):
    raise HTTPException(status_code=status_code, detail=error_detail(code, message, reason, extra))
