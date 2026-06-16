# API Contract: 轻量防翻拍活体增强

V2.1 合同采用向后兼容字段增加，不删除现有字段，不改变现有鉴权规则。

## AntiSpoofRisk Object

```json
{
  "level": "low",
  "reasons": ["normal_motion"],
  "action": "allow",
  "message": "活体检测通过",
  "metrics": {
    "frame_variation": 12.4,
    "face_box_motion": 0.08,
    "sharpness_variation": 5.2
  }
}
```

字段说明：

- `level`: `low`、`medium`、`high`。
- `reasons`: 稳定英文原因码数组。
- `action`: `allow`、`review`、`retry`、`block`。
- `message`: 简短中文提示。
- `metrics`: 可选诊断指标，前端可以不展示。

## POST /liveness/challenges/submit

现有请求保持不变。

响应新增可选字段：

```json
{
  "challenge_id": "challenge-id",
  "status": "passed",
  "passed": true,
  "message": "活体挑战通过",
  "elapsed_ms": 83.4,
  "reason": "ok",
  "result_reason": "ok",
  "anti_spoof_risk": {
    "level": "low",
    "reasons": ["normal_motion"],
    "action": "allow",
    "message": "活体检测通过"
  }
}
```

高风险示例：

```json
{
  "challenge_id": "challenge-id",
  "status": "failed",
  "passed": false,
  "message": "请面对摄像头重新完成活体检测",
  "elapsed_ms": 71.2,
  "reason": "疑似翻拍或静态画面，请调整后重试",
  "result_reason": "anti_spoof_high_risk",
  "anti_spoof_risk": {
    "level": "high",
    "reasons": ["repeated_frames", "static_face_box"],
    "action": "block",
    "message": "疑似翻拍或静态画面，请重新面对摄像头"
  }
}
```

## POST /auth/face-login

现有请求保持不变。

成功响应新增可选字段：

```json
{
  "authenticated": true,
  "message": "认证成功",
  "match": {
    "face_id": "face-id",
    "user_id": 100001,
    "username": "GAOFEI"
  },
  "similarity": 0.72,
  "threshold": 0.6,
  "state": "trace-1",
  "quality_metrics": {},
  "anti_spoof_risk": {
    "level": "low",
    "reasons": ["normal_motion"],
    "action": "allow",
    "message": "活体检测通过"
  },
  "elapsed_ms": 332.03
}
```

高风险阻断错误：

```json
{
  "detail": {
    "code": "ANTI_SPOOF_HIGH_RISK",
    "message": "疑似翻拍风险",
    "reason": "疑似照片、屏幕或静态画面，请面对摄像头重新完成活体检测"
  }
}
```

## GET /audit/login/recent

每条记录新增可选字段：

```json
{
  "id": "audit-id",
  "success": false,
  "failure_reason": "ANTI_SPOOF_HIGH_RISK",
  "terminal_id": "door-1",
  "liveness_status": "failed",
  "liveness_reason": "ANTI_SPOOF_HIGH_RISK",
  "anti_spoof_risk": {
    "level": "high",
    "reasons": ["static_face_box"],
    "action": "block",
    "message": "疑似翻拍或静态画面，请重新面对摄像头"
  },
  "created_at": "2026-06-16 10:00:00"
}
```

## GET /config/effective and GET /system/status

新增可选策略摘要：

```json
{
  "anti_spoof": {
    "enabled": true,
    "mode": "lightweight-risk-score",
    "default_block_level": "high",
    "medium_action": "review",
    "sample_types": ["real_person", "printed_photo", "phone_screen", "desktop_screen", "video_replay"]
  }
}
```

## Compatibility Rules

- 旧客户端可以忽略 `anti_spoof_risk`。
- `anti_spoof_risk.metrics` 不应包含原始图片、连续帧或 embedding。
- `ANTI_SPOOF_HIGH_RISK` 是新增错误码，不替代 `LIVENESS_CHALLENGE_FAILED`。
- 现有 `liveness_status` 和 `liveness_reason` 字段继续保留。
