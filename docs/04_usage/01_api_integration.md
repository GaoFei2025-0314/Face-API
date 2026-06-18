# 人脸识别 API 前端对接文档

> 最后同步：2026-06-17
> 适用阶段：face_api V2.3 轻量防翻拍阈值治理与中风险重试机制

这是 **联调手册**。  
如果你是前端 / 全栈 / Electron 集成方，优先看这一份。

如果你要直接接摄像头 login/register，优先打开：

- `camera-integration.html`
- `docs/04_usage/02_frontend_business_integration.md`

`camera-integration.html` 只用于本机或内网联调。正式业务前端不要直接持有 face_api 的 `X-API-Key`，应由业务后端保存密钥并代理调用 face_api；浏览器只持有业务系统自己的 session/token。

它只回答 4 类问题：
- 先调哪些接口最顺
- 哪些接口要不要带 `X-API-Key`
- 请求体 / 返回体长什么样
- 错误该怎么处理

不负责：
- 服务怎么启动
- 为什么这么设计
- 模块边界和维护策略

这些看：
- `README.md`
- `docs/05_architecture/01_architecture.md`

---

## 1. 最短联调路径

如果你第一次接这个服务，按下面顺序调，最快出结果：

1. `GET /health`
2. `POST /detect` 或 `POST /detect/base64`
3. `POST /compare`
4. `POST /faces/register` + `POST /search`
5. `POST /auth/face-login`
6. 最后再用：
   - `GET /system/status`
   - `GET /config/effective`
   - `GET /audit/login/recent`
   - `GET /audit/login/summary`

这套顺序的好处是：
- 先验证服务是否活着
- 再验证图片能不能解码
- 再验证识别能力
- 最后再验证人脸库和认证辅助

如果你接的是浏览器摄像头，建议直接按 V1.5 示例页走：

1. 打开 `camera-integration.html`
2. 填 `API Base URL`、`API Key`、`terminal_id`
3. 点击“打开摄像头”
4. 用“摄像头 Register”注册单人脸
5. 用“摄像头 Login”完成活体 challenge 和 `/auth/face-login`

---

## 2. 基础信息

| 项 | 值 |
|---|---|
| 默认地址 | `http://localhost:8000` |
| 局域网地址 | `http://<后端机器IP>:8000` |
| 协议 | HTTP / REST |
| 数据格式 | JSON + `multipart/form-data` |
| 交互式文档 | `http://localhost:8000/docs` |
| OpenAPI | `http://localhost:8000/openapi.json` |

底库中保存的是**人脸记录**，并通过 `user_id` / `username` 关联业务用户体系；后端不维护业务用户主表，也不签发登录态。

V1.5 明确边界：

- `face_api` 返回识别结果和失败原因。
- 业务系统负责用户主表、权限、token/session。
- 普通浏览器页面不应该展示或保存 `embedding`、`FACE_API_KEY`。

---

## 3. 鉴权决策表

这个是联调时最容易卡住的点，先看这个。

| 类别 | 接口 | 是否必须带 `X-API-Key` |
|---|---|---|
| 永远公开 | `/health` | 否 |
| 强制鉴权 | `/extract/base64` | 是 |
| 强制鉴权 | `/system/status` | 是 |
| 强制鉴权 | `/config/effective` | 是 |
| 强制鉴权 | `/policy/tuning-summary` | 是 |
| 强制鉴权 | `/search/benchmark-summary` | 是 |
| 强制鉴权 | `/search/index-status` | 是 |
| 强制鉴权 | `/performance/scale-plan` | 是 |
| 强制鉴权 | `/auth/face-login` | 是 |
| 强制鉴权 | `/audit/login/recent` | 是 |
| 强制鉴权 | `/audit/login/summary` | 是 |
| 强制鉴权 | `/liveness/challenges` | 是 |
| 强制鉴权 | `/liveness/challenges/submit` | 是 |
| 强制鉴权 | `/admin/overview` | 是 |
| 强制鉴权 | `/admin/maintenance` | 是 |
| 强制鉴权 | `/admin/faces/{face_id}/delete` | 是 |
| 强制鉴权 | `/admin/backup` | 是 |
| 强制鉴权 | `/admin/restore` | 是 |
| 条件鉴权 | `/detect` | 取决于后端是否配置 `FACE_API_KEY` |
| 条件鉴权 | `/detect/base64` | 同上 |
| 条件鉴权 | `/compare` | 同上 |
| 条件鉴权 | `/faces/register` | 同上 |
| 条件鉴权 | `/faces` | 同上 |
| 条件鉴权 | `/faces/by-user/{user_id}` | 同上 |
| 条件鉴权 | `/faces/{face_id}` | 同上 |
| 条件鉴权 | `/search` | 同上 |

### 一句话理解
- 你要是调 primitive / config / audit / auth-helper，**默认按要 API Key 理解**
- 你要是调 detect / compare / faces / search，取决于服务端有没有配 `FACE_API_KEY`

### 请求头示例

```javascript
const API_KEY = ""; // 后端启用鉴权时填写

function buildHeaders(extra = {}) {
  return {
    ...extra,
    ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
  };
}
```

V1.1 起，`/faces/register` 和 `/auth/face-login` 都必须传 `terminal_id`。业务系统主动调用 face_api，face_api 只返回识别、活体和失败原因结果，不主动 callback 业务系统。

---

## 4. 图片输入格式

### 文件上传
适用：
- `POST /detect`

```javascript
const fd = new FormData();
fd.append("file", fileObject);
fetch("/detect", { method: "POST", body: fd });
```

### Base64 字符串
适用：
- `POST /detect/base64`
- `POST /extract/base64`
- `POST /compare`
- `POST /faces/register`
- `POST /search`
- `POST /auth/face-login`

支持：
- `data:image/jpeg;base64,...`
- 纯 Base64 字符串

转换函数：

```javascript
function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
```

---

## 5. 通用返回约定

### 5.1 计算型接口
通常会返回：
- `elapsed_ms`

### 5.2 相似度字段
统一命名：
- `similarity`

范围：
- `[-1, 1]`

### 5.3 错误结构
错误统一走 FastAPI `detail` 字段，`detail` 是对象：

```json
{
  "detail": {
    "code": "NO_FACE",
    "message": "未检测到人脸",
    "reason": "图片中没有检测到可用于识别的人脸，请调整光线、角度或距离后重试"
  }
}
```

- `code`：稳定英文错误码，给前端和业务系统判断逻辑使用。
- `message`：短中文提示，适合 toast、弹窗标题。
- `reason`：较完整的中文原因和处理建议，适合详情提示、日志和客服排查。

### 推荐前端错误处理
当前 API 的错误 `detail` 是结构化对象。前端可以额外保留字符串 `detail` 的防御性处理，兼容代理层或旧版本服务返回。

### 5.4 常见错误码中文映射

| code | 用户提示 | 运维/开发处理 |
|---|---|---|
| `AUTH_INVALID_OR_MISSING` | 认证失败，请联系管理员检查配置。 | 确认服务启动时设置 `FACE_API_KEY`，请求头带 `X-API-Key`。 |
| `TERMINAL_ID_REQUIRED` | 终端信息缺失，请刷新页面后重试。 | 为每台摄像头配置固定 `terminal_id`。 |
| `NO_FACE` | 没有检测到人脸，请靠近摄像头并保持正脸。 | 检查光线、角度、摄像头清晰度和图片裁剪。 |
| `MULTIPLE_FACES` | 画面中有多个人，请保持单人入镜。 | 注册和 login 都应要求单人画面。 |
| `FACE_QUALITY_LOW` | 图片质量不够，请调整光线或距离后重试。 | 检查检测置信度、亮度和脸框大小阈值。 |
| `FACE_DET_SCORE_LOW` | 人脸识别不够稳定，请调整角度后重试。 | 检查人脸检测置信度阈值和现场角度。 |
| `FACE_TOO_SMALL` | 人脸太小，请靠近摄像头。 | 检查摄像头距离、裁剪比例和最小人脸面积。 |
| `FACE_TOO_DARK` | 画面太暗，请补光后重试。 | 检查现场光照和曝光。 |
| `FACE_TOO_BRIGHT` | 画面过亮，请避开强光后重试。 | 检查逆光、强反光和曝光。 |
| `FACE_BLURRY` | 画面不清晰，请保持稳定后重试。 | 检查摄像头焦距、码率、运动模糊和清晰度阈值。 |
| `LIVENESS_CHALLENGE_REQUIRED` | 请先完成活体动作。 | login 默认需要 `challenge_id`。 |
| `LIVENESS_CHALLENGE_INVALID` | 活体验证已失效，请重新完成动作。 | 检查 challenge 是否过期、用途/terminal 是否一致、是否已被使用。 |
| `LIVENESS_CHALLENGE_FAILED` | 活体动作未通过，请重新眨眼。 | 检查连续帧数量、用户动作和摄像头帧率。 |
| `LIVENESS_ACTION_WINDOW_EXPIRED` | 活体动作超时，请重新开始。 | 用户必须在 `FACE_CHALLENGE_ACTION_SECONDS` 时间窗口内完成动作。 |
| `LIVENESS_FRAME_COUNT_INVALID` | 采集帧数不足，请重新尝试。 | 按后端配置采集 10 到 30 帧。 |
| `ANTI_SPOOF_HIGH_RISK` | 疑似翻拍风险，请重新面对摄像头。 | 检查是否为照片、屏幕或静态画面，结合 audit 的 `anti_spoof_risk` 复核。 |
| `ANTI_SPOOF_MEDIUM_RETRY_REQUIRED` | 检测到中风险，请重试一次。 | 保存 `detail.retry.risk_retry_token`，重新采集活体和登录图片，下一次 `/auth/face-login` 回传该 token。 |
| `ANTI_SPOOF_MEDIUM_RETRY_EXHAUSTED` | 重试后仍存在中风险，请联系工作人员处理。 | 中风险最多重试 1 次；不要继续无限重试。 |
| `ANTI_SPOOF_RETRY_TOKEN_INVALID` | 重试凭证已失效，请重新开始登录。 | 重新创建 login challenge；检查 token 是否过期、已使用或 terminal 不一致。 |
| `NO_MATCH` | 未匹配到已注册用户。 | 检查用户是否已注册、阈值是否过高、现场图像质量。 |
| `VALIDATION_ERROR` | 请求参数不完整，请刷新后重试。 | 检查必填字段、JSON 格式和字段类型。 |
| `MAINTENANCE_MODE_ACTIVE` | 系统维护中，请稍后再试。 | 等待运维退出维护模式。 |

完整摄像头接入说明见 `docs/04_usage/02_frontend_business_integration.md`。

### 5.5 特征向量返回边界
普通页面不要把 embedding 当作普通展示字段来用。

只有这个接口会返回它：
- `POST /extract/base64`

而且它的定位是：
> 受控集成方 primitive，不建议直接暴露给普通浏览器页面。

---

## 6. 最常用接口样例

## 6.1 `GET /health`

用途：
- 探活
- 联调前确认服务是否可用

示例返回：

```json
{ "status": "ok", "service": "face_api" }
```

CPU/GPU、模型和底库数量等细节请看带鉴权的 `GET /system/status`。

---

## 6.2 `POST /detect`

用途：
- 上传文件，查看图中有哪些脸

示例返回：

```json
{
  "count": 2,
  "faces": [
    {
      "bbox": [120.5, 88.2, 340.1, 380.7],
      "det_score": 0.98,
      "landmarks": [[180, 200], [260, 200]],
      "gender": "M",
      "age": 28
    }
  ],
  "elapsed_ms": 42.3
}
```

---

## 6.3 `POST /extract/base64`

用途：
- 提取单人脸 embedding
- 给桌面端 / 终端 / 受控服务自己做匹配、审计、离线逻辑

请求头：

```text
X-API-Key: <你的密钥>
```

请求：

```json
{ "image": "data:image/jpeg;base64,..." }
```

成功返回：

```json
{
  "count": 1,
  "code": "OK",
  "message": "ok",
  "embedding": [0.1, 0.2],
  "face": {
    "bbox": [120.5, 88.2, 340.1, 380.7],
    "det_score": 0.98,
    "landmarks": [[180, 200], [260, 200]]
  },
  "elapsed_ms": 36.5
}
```

常见失败码：
- `IMAGE_DECODE_FAILED`
- `IMAGE_TOO_LARGE`
- `NO_FACE`
- `MULTIPLE_FACES`
- `INVALID_EMBEDDING_RESPONSE`

---

## 6.4 `POST /compare`

请求：

```json
{ "image1": "...", "image2": "...", "threshold": 0.5 }
```

返回：

```json
{ "similarity": 0.782, "threshold": 0.5, "is_same_person": true, "elapsed_ms": 88.1 }
```

关键规则：
- 两张图都必须检测到至少 1 张脸
- 任一图无人脸时返回结构化失败码 `NO_FACE`
- 多脸场景下取 `det_score` 最高的人脸参与比对

---

## 6.5 `POST /faces/register`

V1.1 起请求体必须包含 `terminal_id`。如果注册启用了活体，还必须携带已通过且未使用的 `challenge_id`。

```json
{
  "user_id": 10001,
  "terminal_id": "door-1",
  "challenge_id": "optional-passed-challenge-id",
  "username": "zhangsan",
  "image": "base64...",
  "metadata": { "department": "研发部" }
}
```

请求：

```json
{
  "user_id": 10001,
  "username": "zhangsan",
  "image": "...",
  "metadata": { "department": "研发部" }
}
```

返回：

```json
{ "id": "550e8400-...", "user_id": 10001, "username": "zhangsan", "message": "注册成功" }
```

关键规则：
- 图片必须且只能包含 1 张脸
- `username` 必填

---

## 6.6 `POST /search`

请求：

```json
{ "image": "...", "top_k": 5, "threshold": 0.5 }
```

返回：

```json
{
  "query_face_count": 1,
  "threshold": 0.5,
  "matches": [
    { "id": "...", "user_id": 10001, "username": "zhangsan", "similarity": 0.823, "metadata": {} }
  ],
  "elapsed_ms": 45.6
}
```

关键规则：
- 至少检测到 1 张脸
- 多脸场景取 `det_score` 最高的人脸做检索
- 未检测到人脸时返回结构化失败码 `NO_FACE`

---

## 6.7 `POST /auth/face-login`

请求头：

```text
X-API-Key: <你的密钥>
```

请求体：

```json
{
  "image": "...",
  "terminal_id": "kiosk-01",
  "challenge_id": "passed-login-challenge-id",
  "state": "trace-001",
  "threshold": 0.6,
  "risk_retry_token": null
}
```

默认情况下 face login 启用活体检测。前端应先调用 `/liveness/challenges` 创建 challenge，再提交连续图片帧到 `/liveness/challenges/submit`。challenge 通过后，把一次性 `challenge_id` 带到 `/auth/face-login`。

challenge 通过时，后端会抽样检测连续帧中的人脸并保存该活体人脸特征。后续 `/auth/face-login` 或启用活体的 `/faces/register` 必须使用同一个人的图片，否则会返回 `LIVENESS_CHALLENGE_INVALID`。

### V1.1 活体 challenge

创建：

```json
POST /liveness/challenges
{ "purpose": "login", "terminal_id": "door-1", "action": "blink" }
```

提交：

```json
POST /liveness/challenges/submit
{
  "challenge_id": "...",
  "purpose": "login",
  "terminal_id": "door-1",
  "frames": ["base64-frame-1", "base64-frame-2"]
}
```

失败返回仍为 HTTP 200，但 `passed=false`。前端应优先展示 `reason` 给现场用户，`result_reason` 用于排障记录：

```json
{
  "challenge_id": "...",
  "status": "failed",
  "passed": false,
  "message": "请面对摄像头并完成眨眼后重试",
  "reason": "活体动作幅度不够，请看着预览画面眨眼，并轻微前后移动或调整光线后重试",
  "result_reason": "brightness_variation=2.17",
  "elapsed_ms": 67.51
}
```

V2.1 起，活体提交和 face login 会返回可选 `anti_spoof_risk`：

```json
{
  "level": "low",
  "reasons": ["normal_motion"],
  "action": "allow",
  "message": "活体检测通过"
}
```

字段含义：

- `level`：`low`、`medium`、`high`。
- `reasons`：稳定原因码，给运维和验收记录使用。
- `action`：`allow`、`review`、`retry`、`block`。
- `message`：简短中文提示，适合页面展示。
- `metrics`：可选诊断指标，前端可以忽略，不要直接展示给普通用户。

相关运维阈值：

- `FACE_LIVENESS_MIN_BRIGHTNESS_VARIATION`：眨眼活体连续帧最低亮度变化阈值，默认 `5.0`。
- `FACE_ANTI_SPOOF_MIN_FRAME_DELTA`：连续帧重复判定的最低帧差阈值，默认 `1.0`。
- `FACE_ANTI_SPOOF_MIN_FRAME_VARIATION`：防翻拍亮度变化阈值，默认 `5.0`。
- `FACE_ANTI_SPOOF_MIN_FACE_MOTION`：抽样人脸框位置或面积变化阈值，默认 `0.015`。
- `FACE_ANTI_SPOOF_MIN_SHARPNESS_VARIATION`：清晰度变化阈值，默认 `1.0`。
- `FACE_ANTI_SPOOF_MIN_TEXTURE_VARIATION`：连续帧差异过于均匀时的纹理变化阈值，默认 `1.0`。

V2.3 起，中风险默认不再直接放行，而是返回一次重试机会。第一次中风险默认返回 HTTP 403：

```json
{
  "detail": {
    "code": "ANTI_SPOOF_MEDIUM_RETRY_REQUIRED",
    "message": "检测到中风险，请重试一次",
    "reason": "当前画面存在轻量防翻拍中风险，请重新面对摄像头完成一次采集",
    "retry": {
      "risk_retry_token": "<opaque-token>",
      "expires_at": "2026-06-17T12:00:00Z",
      "remaining_attempts": 1
    }
  }
}
```

客户端处理规则：

- `risk_retry_token` 是不透明 token，只能原样保存并回传，不要解析、展示或写入报告。
- 第二次重试必须重新创建 login challenge，重新采集连续帧和登录图片，并在 `/auth/face-login` 请求体中同时传新的 `challenge_id` 和上一次返回的 `risk_retry_token`。
- token 由后端强制校验，最多使用 1 次，并绑定 `terminal_id` 和有效期；不要依赖前端 `state` 自己计数。
- 第二次仍为中风险时，后端返回 `ANTI_SPOOF_MEDIUM_RETRY_EXHAUSTED`，前端应提示失败或转人工处理。
- `acceptance.html` 的 JSON/CSV 报告和 audit 页面只记录 retry 状态，不导出原始 token。

高风险 challenge 示例：

```json
{
  "challenge_id": "...",
  "status": "failed",
  "passed": false,
  "message": "请面对摄像头并完成眨眼后重试",
  "reason": "疑似翻拍或静态画面，请重新面对摄像头",
  "result_reason": "anti_spoof_high_risk",
  "anti_spoof_risk": {
    "level": "high",
    "reasons": ["repeated_frames", "static_face_box"],
    "action": "block",
    "message": "疑似翻拍或静态画面，请重新面对摄像头"
  },
  "elapsed_ms": 67.51
}
```

规则：

- `challenge` 有效期 60 秒。
- 动作窗口 10 秒。
- 眨眼 challenge 提交 10 到 30 帧连续图片。
- `challenge_id` 只能使用一次。
- 用途和 `terminal_id` 必须与 login/注册请求一致。
- challenge 通过时的人脸必须与最终 login/注册图片中的人脸一致。
- 如果 challenge 提交失败，请重新创建 challenge；失败的 `challenge_id` 不能继续复用。
- V2.3 中风险重试时，第二次 login 也必须使用新的已通过 `challenge_id`，不能复用第一次 challenge。
- 维护模式下不能创建或提交 challenge。

### V1.1 运维控制台 API

- `GET /admin/overview`：控制台概览。
- `POST /admin/maintenance`：进入或退出维护模式。
- `POST /admin/faces/{face_id}/delete`：二次确认后删除人脸。
- `POST /admin/backup`：备份数据库。
- `POST /admin/restore`：维护模式 + 二次确认后恢复数据库。

`/admin/overview` 只用于控制台概览，返回运行状态、`faces.count`、audit 汇总和维护模式。它不会返回全量人脸列表；需要查看人脸列表时使用 `GET /faces`。

维护模式请求体：

```json
{ "enabled": true }
```

删除人脸请求体：

```json
{ "confirm": true }
```

恢复数据库请求体：

```json
{ "backup_dir": "backups/20260605-120000", "confirm": true }
```

恢复路径只能选择项目 `backups/` 目录下的备份。production 默认不允许在线恢复；多 worker 或生产恢复建议先停止 API 服务，再用恢复脚本执行。

### V1.1 阈值调参说明

`GET /policy/tuning-summary` 只提供建议，不会自动修改阈值。

- false accept：不该通过的人通过了。阈值过低时风险更高。
- false reject：应该通过的人被拒绝。阈值过高、光照差或摄像头角度差时更常见。
- V1.1 建议按 `terminal_id` 绑定策略档案，因为不同摄像头和安装位置的现场条件不同。
- 调整阈值前先看 audit 样本量和相似度分布；样本不足时不要调整。

### V1.1 terminal 上线检查清单

terminal 上线前至少验证：

- `terminal_id` 固定且能在注册、login、audit 中看到。
- 业务系统主动调用 face_api，不等待 face_api callback。
- 注册流程能正确处理 `NO_FACE`、`MULTIPLE_FACES`、`FACE_QUALITY_LOW`。
- face login 流程能先完成活体 challenge，再携带一次性 `challenge_id` 调用 `/auth/face-login`。
- 活体失败时，用户端展示简短操作提示。
- 中风险 `ANTI_SPOOF_MEDIUM_RETRY_REQUIRED` 时，用户端重新采集一次，并把 `risk_retry_token` 只回传给下一次 `/auth/face-login`。
- `NO_MATCH`、`LIVENESS_CHALLENGE_REQUIRED`、`LIVENESS_CHALLENGE_INVALID` 能映射到明确重试动作。
- 现场网络异常时客户端有 timeout 和 retry 限制，避免无限重试。
- 运维人员能在 `/audit/login/recent?terminal_id=<id>` 中看到该 terminal 的记录。

成功返回：

```json
{
  "authenticated": true,
  "message": "认证成功",
  "match": { "face_id": "face-record-id", "user_id": 10001, "username": "zhangsan" },
  "similarity": 0.782,
  "threshold": 0.6,
  "state": "trace-001",
  "anti_spoof_risk": {
    "level": "low",
    "reasons": ["normal_motion"],
    "action": "allow",
    "message": "活体检测通过"
  },
  "elapsed_ms": 45.6
}
```

关键规则：
- 必须启用 API Key
- 图片必须且只能有 1 张脸
- 无人脸 / 多人脸 / 无匹配 / 脏底库记录都走结构化失败语义
- 高风险防翻拍结果返回 `ANTI_SPOOF_HIGH_RISK`，不应继续发起业务登录
- 中风险默认返回 `ANTI_SPOOF_MEDIUM_RETRY_REQUIRED`，不应当作登录成功；第二次仍中风险返回 `ANTI_SPOOF_MEDIUM_RETRY_EXHAUSTED`
- 只返回匹配结果，不负责 token/session 签发

---

## 6.8 `GET /system/status`

用途：
- 看当前 provider、模型、检测尺寸、鉴权状态、底库规模

请求头：

```text
X-API-Key: <你的密钥>
```

示例返回：

```json
{
  "status": "ok",
  "device": "CPU",
  "providers": ["CPUExecutionProvider"],
  "model": "buffalo_l",
  "det_size": [640, 640],
  "auth_enabled": true,
  "force_cpu": true,
  "use_gpu": false,
  "environment": "production",
  "cors_origins": ["http://localhost:3000"],
  "db_path": "faces.db",
  "log_path": "logs/face_api.log",
  "duplicate_policy": "allow",
  "anti_spoof": {
    "enabled": true,
    "mode": "lightweight-risk-score",
    "default_block_level": "high",
    "medium_action": "retry",
    "retry": {
      "medium_max_retries": 1,
      "token_ttl_seconds": 300
    },
    "thresholds": {
      "min_frame_variation": 5.0,
      "min_frame_delta": 1.0,
      "min_face_motion": 0.015,
      "min_sharpness_variation": 1.0,
      "min_texture_variation": 1.0
    }
  },
  "search_cache": {
    "ready": true,
    "dirty": false,
    "record_count": 12
  },
  "faces_count": 12
}
```

---

## 6.9 `GET /config/effective`

用途：
- 看当前生效阈值和运行配置

请求头：

```text
X-API-Key: <你的密钥>
```

示例返回：

```json
{
  "face_login_threshold": 0.55,
  "auth_enabled": true,
  "force_cpu": true,
  "use_gpu": false,
  "environment": "production",
  "cors_origins": ["http://localhost:3000"],
  "log_path": "logs/face_api.log",
  "duplicate_policy": "allow",
  "model": "buffalo_l",
  "det_size": [640, 640],
  "db_path": "faces.db",
  "max_base64_image_chars": 11185068,
  "max_image_bytes": 8388608,
  "max_image_pixels": 4096000,
  "anti_spoof": {
    "enabled": true,
    "mode": "lightweight-risk-score",
    "default_block_level": "high",
    "medium_action": "retry",
    "retry": {
      "medium_max_retries": 1,
      "token_ttl_seconds": 300
    },
    "thresholds": {
      "min_frame_variation": 5.0,
      "min_frame_delta": 1.0,
      "min_face_motion": 0.015,
      "min_sharpness_variation": 1.0,
      "min_texture_variation": 1.0
    }
  }
}
```

---

## 7. 审计接口

### `GET /audit/login/recent`
用途：
- 查看最近登录尝试记录

可选查询参数：

- `limit`：返回条数，范围由后端保护
- `success`：按成功或失败筛选，例如 `true` / `false`
- `terminal_id`：按终端标识筛选

V2.1 起，每条记录可能包含 `anti_spoof_risk`，用于区分普通活体失败、画面质量问题和疑似翻拍高风险。页面只展示风险等级和中文提示，运维可以结合 `reasons` 复核。

V2.2 起，login 用途的活体 challenge 如果在 `/liveness/challenges/submit` 阶段失败，也会写入一条失败 login audit，便于现场验收时在“最近 audit”里看到完整登录失败链路。

V2.3 起，中风险重试会记录 retry 状态、风险等级、原因和处理动作，但不会记录或返回原始 `risk_retry_token`。token 只出现在本次错误响应的 `detail.retry.risk_retry_token` 中。

### `GET /audit/login/summary`
用途：
- 查看最近登录成功/失败汇总
- 支撑阈值调优、失败原因分析、现场排障

这两个接口都要求：
- 显式 `FACE_API_KEY`
- 正确 `X-API-Key`

---

## 8. 对接代码示例

## 8.1 原生 `fetch`

```javascript
const API_BASE = "http://localhost:8000";
const API_KEY = ""; // 后端启用鉴权时填写

async function request(path, options = {}) {
  options.headers = {
    ...(options.headers || {}),
    ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
  };

  const res = await fetch(API_BASE + path, options);
  const data = await res.json();
  if (!res.ok) {
    const detail = data && data.detail;
    const errorMessage =
      (detail && typeof detail === "object" && detail.reason) ||
      (detail && typeof detail === "object" && detail.message) ||
      (typeof detail === "string" && detail) ||
      "请求失败";
    throw new Error(errorMessage);
  }
  return data;
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
```

## 8.2 Next.js API Route 代理

```javascript
const BACKEND = "http://localhost:8000";
const API_KEY = process.env.FACE_API_KEY || "";

export async function POST(request, { params }) {
  const path = params.path.join("/");
  const body = await request.text();

  const res = await fetch(`${BACKEND}/${path}`, {
    method: "POST",
    headers: {
      "Content-Type": request.headers.get("content-type") || "application/json",
      ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
    },
    body,
  });

  return new Response(await res.text(), {
    status: res.status,
    headers: { "Content-Type": res.headers.get("content-type") || "application/json" },
  });
}
```

## 8.3 摄像头业务接入最小示例

`camera-integration.html` 已经包含完整浏览器示例。业务系统自己的页面可以复用以下流程：

```javascript
async function createLoginChallenge(apiBase, apiKey, terminalId) {
  const res = await fetch(`${apiBase}/liveness/challenges`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
    body: JSON.stringify({ purpose: "login", terminal_id: terminalId, action: "blink" })
  });
  return res.json();
}

async function faceLogin(apiBase, apiKey, terminalId, challengeId, imageBase64) {
  const res = await fetch(`${apiBase}/auth/face-login`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
    body: JSON.stringify({
      image: imageBase64,
      terminal_id: terminalId,
      challenge_id: challengeId,
      threshold: 0.6,
      state: "trace-" + Date.now(),
      risk_retry_token: window.pendingRiskRetryToken || undefined
    })
  });
  const data = await res.json();
  if (!res.ok) {
    if (data.detail && data.detail.code === "ANTI_SPOOF_MEDIUM_RETRY_REQUIRED") {
      window.pendingRiskRetryToken = data.detail.retry && data.detail.retry.risk_retry_token;
    }
    throw data;
  }

  // face_api 不签发 token/session。
  // 业务系统应使用 data.match.user_id / data.match.username 查询自己的用户表。
  window.pendingRiskRetryToken = null;
  return data;
}
```

---

## 9. TypeScript 类型

```typescript
export interface FaceInfo {
  bbox: [number, number, number, number];
  det_score: number;
  landmarks: number[][] | null;
  gender: "M" | "F";
  age: number;
}

export interface DetectResp {
  count: number;
  faces: FaceInfo[];
  elapsed_ms: number;
}

export interface CompareResp {
  similarity: number;
  threshold: number;
  is_same_person: boolean;
  elapsed_ms: number;
}

export interface MatchItem {
  id: string;
  user_id: number | null;
  username: string;
  similarity: number;
  metadata: Record<string, any>;
}

export interface SearchResp {
  query_face_count: number;
  threshold: number;
  matches: MatchItem[];
  elapsed_ms: number;
}

export interface RegisteredFace {
  id: string;
  user_id: number | null;
  username: string;
  metadata: Record<string, any>;
  created_at: string;
}

export interface FaceLoginResp {
  authenticated: boolean;
  message: string;
  match: { face_id?: string | null; user_id: number | null; username: string };
  similarity: number;
  threshold: number;
  state?: string | null;
  anti_spoof_risk?: AntiSpoofRisk | null;
  elapsed_ms: number;
}

export interface FaceLoginReq {
  image: string;
  terminal_id: string;
  challenge_id: string;
  threshold?: number;
  state?: string | null;
  risk_retry_token?: string | null;
}

export interface AntiSpoofRisk {
  level: "low" | "medium" | "high";
  reasons: string[];
  action: "allow" | "review" | "retry" | "block";
  message: string;
  metrics?: Record<string, number | string | null>;
}

export interface FaceApiErrorDetail {
  code: string;
  message: string;
  reason: string;
  retry?: {
    risk_retry_token: string;
    expires_at: string;
    remaining_attempts: number;
  };
}
```

---

## 10. 联调建议

### 10.1 性能数据怎么看
文档里的耗时都应按：
- 历史经验值 / 参考值
- 受机器、GPU 是否真实生效、图片尺寸、底库规模影响

V1.6 起新增三个只读性能接口，均需要 `X-API-Key`：

- `GET /search/benchmark-summary`：查看 5 万人脸 benchmark 目标、报告字段和当前搜索模式。
- `GET /search/index-status`：查看 index 是否启用、是否 fresh、进入条件和 exact 回退策略。
- `GET /performance/scale-plan`：查看 benchmark、index 和批量清单流程的总方案。

默认搜索模式仍然是 `exact`，不会因为新增这些接口而自动启用 ANN/Faiss。

### 10.1.1 Benchmark 报告格式

`scripts/benchmark-scale.py` 默认输出：

```text
reports/performance/benchmark-scale.json
```

核心字段：

```json
{
  "version": "1.0",
  "target_record_count": 50000,
  "target_latency_ms": 1000,
  "record_count": 50000,
  "runtime": {
    "python": "3.10.x",
    "platform": "Windows",
    "db_path": "faces.db"
  },
  "search": {
    "samples": 100,
    "avg_ms": 120.5,
    "p95_ms": 300.2,
    "failure_count": 0,
    "failure_reasons": {}
  },
  "index_decision": {
    "current_mode": "exact",
    "should_evaluate_index": false,
    "fallback_required": true
  },
  "conclusion": "pass"
}
```

### 10.1.2 批量清单流程

导出底库清单：

```powershell
D:\anaconda3\envs\face_api\python.exe scripts\bulk-manifest.py export --db-path faces.db --output exports\faces-manifest.jsonl
```

导出字段：

```text
id, user_id, username, metadata, created_at
```

导出清单不包含 `embedding`。

校验导入清单：

```powershell
D:\anaconda3\envs\face_api\python.exe scripts\bulk-manifest.py validate-import imports\faces.csv --output reports\bulk-import-validate.json
```

导入清单必填：

```text
image_path, username
```

导入清单可选：

```text
user_id, terminal_id, metadata
```

### 10.2 前端建议
- 上传前尽量压缩到 1000px 以内
- 前端超时建议设 30 秒
- 优先观察接口返回里的 `elapsed_ms`
- 鉴权统一在请求封装层注入 `X-API-Key`
- 摄像头页面提交期间禁用按钮，避免重复注册或重复消费 challenge
- `terminal_id` 必须稳定，不要每次刷新页面随机生成
- `API Key` 用密码框输入或由服务端代理注入，不要打印到页面结果区

### 10.3 联调顺序建议
1. `/health`
2. `/detect` 或 `/detect/base64`
3. `/compare`
4. `/faces/register` + `/search`
5. `/auth/face-login`
6. `/system/status` / `/config/effective` / 审计接口

### 10.4 V1.5 上线检查清单

- [ ] 后端服务能访问 `GET /health`。
- [ ] 受保护接口请求头包含正确 `X-API-Key`。
- [ ] 每台摄像头配置固定 `terminal_id`。
- [ ] login 流程先完成活体 challenge，再调用 `/auth/face-login`。
- [ ] 注册流程传入 `user_id`、`username`、`terminal_id` 和单人脸图片。
- [ ] 前端不会打印或保存 `API Key`、`embedding`。
- [ ] 常见错误码有中文用户提示和运维处理建议。
- [ ] 业务系统明确由自己签发 token/session。
- [ ] 网络超时、后端未启动、摄像头权限失败都有提示。
- [ ] 可在 `/audit/login/recent` 查询指定 `terminal_id` 的登录记录。
