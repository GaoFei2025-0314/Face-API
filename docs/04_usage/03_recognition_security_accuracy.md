# 识别安全与准确率说明

本文说明质量评分、失败原因、terminal 策略、调参摘要、活体边界，以及 V2.3 轻量防翻拍治理的约定。

## 1. 质量指标

注册和 face login 会计算可解释质量指标：

- `det_score`：人脸检测置信度。
- `face_width` / `face_height` / `face_pixels`：人脸框大小。
- `face_area_ratio`：人脸区域占整张图比例。
- `brightness`：图片平均亮度。
- `sharpness`：基于 Laplacian 方差的清晰度指标。

质量失败会返回结构化错误：

- `FACE_DET_SCORE_LOW`：检测置信度过低。
- `FACE_TOO_SMALL`：人脸区域过小。
- `FACE_TOO_DARK`：画面过暗。
- `FACE_TOO_BRIGHT`：画面过亮。
- `FACE_BLURRY`：画面清晰度不足。

前端应展示短中文提示，运维应结合 `reason`、`quality_metrics` 和现场摄像头状态排查。

## 2. 登录审计

`/auth/face-login` 会把以下信息写入 login audit：

- 是否成功。
- `terminal_id`。
- 阈值和相似度。
- 失败原因。
- 活体状态和原因。
- 质量指标。

运维可通过 `/audit/login/recent` 和 `/audit/login/summary` 查看近期数据。

## 3. terminal 策略

`GET /policy/tuning-summary` 返回只读调参摘要，不会自动修改阈值。

当前策略原则：

- `strict` 阈值高于默认档。
- `balanced` 介于严格和默认之间。
- `permissive` 不低于默认安全线。
- 系统不会根据少量样本自动降低阈值。
- 样本不足时只提示继续观察。

如果某个 terminal 经常失败，优先检查摄像头安装、光照、焦距、底库照片质量和活体动作引导。

## 4. false accept / false reject

- false accept：不该通过的人通过了，通常和阈值过低、底库照片异常、活体能力不足有关。
- false reject：应该通过的人被拒绝，通常和阈值过高、现场图像质量差、摄像头角度差有关。

调参时必须先积累足够 audit 样本，再人工复核成功/失败样本的相似度分布和质量指标。

## 5. 活体能力边界

当前稳定活体动作是 `blink`，属于基础动作型活体。

它可以帮助过滤部分静态照片和无动作输入，但不承诺覆盖：

- 高清屏幕翻拍。
- 深度伪造视频。
- 复杂面具或专业攻击。
- 摄像头被替换或上游视频流被伪造。

高风险场景应增加更强活体模型、深度摄像头、红外摄像头或人工复核流程。

V1.4 起 `FACE_CHALLENGE_ACTION_SECONDS` 会真正限制动作完成窗口。超时后返回 `LIVENESS_ACTION_WINDOW_EXPIRED`，前端必须重新创建 challenge。

## 6. V2.1 轻量防翻拍风险

V2.1 在基础活体 challenge 上增加轻量防翻拍风险评分，返回可选 `anti_spoof_risk`：

- `level=low`：正常通过，不默认增加复杂动作。
- `level=medium`：记录 audit，提示调整光线、脸部位置或重新采集。
- `level=high`：默认阻断本次 login 或注册，返回 `ANTI_SPOOF_HIGH_RISK`。

当前轻量信号包括：

- 连续帧亮度变化。
- 连续帧重复程度。
- 连续帧整体亮度均匀变化，作为疑似屏幕或照片平移的 `uniform_frame_delta` 信号。
- 抽样人脸框位置和面积变化。
- 清晰度变化。
- 采集信号不足或画面质量不足。

这些信号会写入 audit 的 `anti_spoof_risk.reasons`，用于运维复核。普通用户页面只展示短中文提示，不展示 `metrics`。

相关阈值可以通过环境变量微调：

| 环境变量 | 默认值 | 作用 |
|---|---:|---|
| `FACE_LIVENESS_MIN_BRIGHTNESS_VARIATION` | `5.0` | 眨眼活体连续帧最低亮度变化阈值 |
| `FACE_ANTI_SPOOF_MIN_FRAME_VARIATION` | `5.0` | 防翻拍亮度变化阈值 |
| `FACE_ANTI_SPOOF_MIN_FRAME_DELTA` | `1.0` | 连续帧重复判定的最低帧差阈值 |
| `FACE_ANTI_SPOOF_MIN_FACE_MOTION` | `0.015` | 抽样人脸框位置或面积变化阈值 |
| `FACE_ANTI_SPOOF_MIN_SHARPNESS_VARIATION` | `1.0` | 清晰度变化阈值 |

V2.1 不承诺覆盖：

- 高清屏幕视频重放。
- 深度伪造或换脸视频。
- 虚拟摄像头流。
- 专业攻击设备。
- 针对规则阈值反复调试后的攻击样例。

现场验收应至少覆盖真人正脸、打印照片、手机屏幕照片、电脑屏幕照片和手机播放眨眼视频。若业务安全级别更高，应评估专用 anti-spoofing 模型、红外/深度摄像头或人工复核流程。

## 7. V2.2 现场算法验收

V2.2 新增 `acceptance.html` 作为现场算法验收台。它使用同一个已注册测试用户，固定验证真人正脸、打印照片、手机屏幕照片、电脑屏幕照片和手机播放眨眼视频五类样例，每类默认采集 3 次。

页面会走完整登录链路，并在本地生成 JSON/CSV 报告。报告只包含结果、相似度、风险等级、中文原因和关键质量指标，不包含 API Key、原图、连续帧或 embedding。

注册或重绑测试用户时，`user_id` 使用数字或留空。如果后端开启注册活体，页面会先完成 `register` challenge；如果登录活体 challenge 返回失败，页面只记录该次失败和防翻拍风险，不继续调用 face login。

调参建议分两层：默认给现场人员检查光线、距离、摄像头角度和样例一致性；展开后给开发/运维关注 `FACE_LIVENESS_MIN_BRIGHTNESS_VARIATION`、`FACE_ANTI_SPOOF_MIN_FRAME_VARIATION`、`FACE_ANTI_SPOOF_MIN_FRAME_DELTA`、`FACE_ANTI_SPOOF_MIN_FACE_MOTION`、`FACE_ANTI_SPOOF_MIN_SHARPNESS_VARIATION` 等阈值方向。

页面建议只用于本地工作站或受控内网验收。若通过 `http://localhost:8122/acceptance.html` 打开，并且服务以生产模式运行，需要把 `http://localhost:8122` 加入 `FACE_CORS_ORIGINS`。普通互联网业务前端仍不应直接持有 `X-API-Key`。

## 8. V2.3 轻量防翻拍治理

V2.3 基于 V2.2 的现场验收结果收紧轻量评分和中风险处理。目标是减少打印照片、手机屏幕、电脑屏幕和播放视频在低风险下静默登录成功，同时避免把真实用户体验做得过重。

默认策略：

- `level=low`：允许继续登录匹配。
- `level=medium`：默认返回 `ANTI_SPOOF_MEDIUM_RETRY_REQUIRED`，提示重新面对摄像头采集一次，不返回登录成功。
- `level=high`：返回 `ANTI_SPOOF_HIGH_RISK`，拒绝本次登录。

中风险重试由后端强制：

- 第一次中风险由后端签发一次性 `risk_retry_token`。
- 第二次 `/auth/face-login` 必须使用新的 `challenge_id`，并回传该 token。
- token 只保存 hash 或不可逆摘要，绑定 `terminal_id` 和有效期，不能靠前端 `state` 或业务端自报次数绕过。
- V2.3 最大重试次数固定为 1，不提供 `FACE_ANTI_SPOOF_MEDIUM_MAX_RETRIES`。

相关配置：

| 环境变量 | 默认值 | 作用 |
|---|---:|---|
| `FACE_ANTI_SPOOF_MEDIUM_ACTION` | `retry` | 中风险处理策略，可选 `retry`、`review`、`block` |
| `FACE_ANTI_SPOOF_RETRY_TOKEN_TTL_SECONDS` | `300` | 中风险重试 token 有效期 |

验收判断：

- 真人正脸至少 2/3 成功。
- 翻拍样例不得低风险静默成功。
- 中风险必须能在 audit 和验收报告中看出原因、动作和 retry 状态。
- `acceptance.html` 导出的 JSON/CSV 不包含 API Key、原图、连续帧、embedding 或原始 `risk_retry_token`。

部署前提：

- V2.3 默认按固定摄像头验收。摄像头应固定在 Windows 工作站、闸机或一体机上，不应让用户拿起摄像头制造前后运动。
- 如果摄像头是手持或可移动设备，移动摄像头本身可能制造 `normal_motion` 信号，让照片或屏幕翻拍更容易通过轻量评分。这种场景需要后续版本引入更强 anti-spoofing 模型、设备固定检测或人工复核。

能力边界不变：V2.3 仍是轻量治理，不承诺覆盖虚拟摄像头、深度伪造、专业重放攻击或高质量攻击设备。更高安全场景应评估专用 anti-spoofing 模型、红外/深度摄像头或人工复核。
