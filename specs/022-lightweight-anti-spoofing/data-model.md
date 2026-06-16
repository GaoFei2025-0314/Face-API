# Data Model: 轻量防翻拍活体增强

## AntiSpoofRisk

表示一次活体或登录流程中的轻量防翻拍风险结果。

字段：

- `level`: 风险等级，取值为 `low`、`medium`、`high`。
- `reasons`: 风险原因列表，用于运维复核。示例：`low_frame_variation`、`repeated_frames`、`static_face_box`、`screen_like_artifact`、`poor_capture_quality`。
- `action`: 建议处理动作，取值为 `allow`、`review`、`retry`、`block`。
- `message`: 简短中文提示，用户可见。
- `metrics`: 可选诊断指标，只给运维和 audit 使用，不面向普通用户解释。

验证规则：

- `level=low` 时默认 `action=allow`。
- `level=medium` 时默认 `action=review` 或 `retry`，不默认阻断。
- `level=high` 时默认 `action=block`。
- `reasons` 不得为空；无法判断时使用 `insufficient_signal`。

## AntiSpoofSignal

表示用于判断风险的单项信号。

字段：

- `name`: 信号名称。
- `value`: 实际观测值。
- `threshold`: 触发阈值或参考值。
- `severity`: 信号严重程度，取值为 `info`、`warning`、`critical`。

验证规则：

- 只保存可复核、非敏感指标。
- 不保存原始图片帧。
- 不保存人脸 embedding。

## LivenessChallengeResult

现有活体 challenge 结果的扩展。

新增关系：

- 可关联一个 `AntiSpoofRisk`。

状态影响：

- `anti_spoof_risk.level=high` 时，challenge 可以返回失败或要求重新采集。
- `anti_spoof_risk.level=medium` 时，challenge 可以通过但记录风险，也可以按配置提示重试。
- `anti_spoof_risk.level=low` 时，保持现有通过流程。

## FaceLoginAudit

现有登录审计记录的扩展。

新增关系：

- 可关联一个 `AntiSpoofRisk`。

记录要求：

- 成功、失败、中风险和高风险都应保留风险等级。
- 高风险阻断时，`failure_reason` 应能区分为防翻拍高风险，而不是普通未匹配。
- audit 不记录原始图片、连续帧或 embedding。

## AcceptanceSample

用于 V2.1 验收报告的样例记录。

字段：

- `sample_type`: `real_person`、`printed_photo`、`phone_screen`、`desktop_screen`、`video_replay`。
- `expected_result`: 预期结果，如通过、非低风险、拒绝或需复核。
- `actual_result`: 实际结果。
- `risk_level`: 本次样例风险等级。
- `notes`: 现场备注，如光照、屏幕亮度、摄像头距离。

验证规则：

- 每类样例至少一条记录。
- 真人样例必须记录是否误拒。
- 翻拍样例必须记录是否被静默低风险通过。
