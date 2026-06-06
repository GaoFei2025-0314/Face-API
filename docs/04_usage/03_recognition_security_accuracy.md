# V1.4 识别安全与准确率说明

本文说明 V1.4 对质量评分、失败原因、terminal 策略、调参摘要和活体边界的约定。

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
