# 人脸识别 API 前端对接文档

> 最后同步：2026-05-27  
> 适用阶段：face_api modularization phase-1

这是 **联调手册**。  
如果你是前端 / 全栈 / Electron 集成方，优先看这一份。

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
- `docs/architecture/ARCHITECTURE.md`

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

---

## 3. 鉴权决策表

这个是联调时最容易卡住的点，先看这个。

| 类别 | 接口 | 是否必须带 `X-API-Key` |
|---|---|---|
| 永远公开 | `/health` | 否 |
| 强制鉴权 | `/extract/base64` | 是 |
| 强制鉴权 | `/system/status` | 是 |
| 强制鉴权 | `/config/effective` | 是 |
| 强制鉴权 | `/auth/face-login` | 是 |
| 强制鉴权 | `/audit/login/recent` | 是 |
| 强制鉴权 | `/audit/login/summary` | 是 |
| 强制鉴权 | `/liveness/challenges` | 是 |
| 强制鉴权 | `/liveness/challenges/submit` | 是 |
| 强制鉴权 | `/admin/overview` | 是 |
| 强制鉴权 | `/admin/backup` | 是 |
| 强制鉴权 | `/admin/restore` | 是 |
| 条件鉴权 | `/detect` | 取决于后端是否配置 `FACE_API_KEY` |
| 条件鉴权 | `/detect/base64` | 同上 |
| 条件鉴权 | `/compare` | 同上 |
| 条件鉴权 | `/faces/register` | 同上 |
| 条件鉴权 | `/faces` | 同上 |
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

### 5.4 特征向量返回边界
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
{ "status": "ok", "device": "CPU", "faces": 12 }
```

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
  "threshold": 0.6
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

规则：

- `challenge` 有效期 60 秒。
- 动作窗口 10 秒。
- 眨眼 challenge 提交 10 到 30 帧连续图片。
- `challenge_id` 只能使用一次。
- 用途和 `terminal_id` 必须与 login/注册请求一致。
- challenge 通过时的人脸必须与最终 login/注册图片中的人脸一致。
- 如果 challenge 提交失败，请重新创建 challenge；失败的 `challenge_id` 不能继续复用。
- 维护模式下不能创建或提交 challenge。

### V1.1 运维控制台 API

- `GET /admin/overview`：控制台概览。
- `POST /admin/maintenance`：进入或退出维护模式。
- `POST /admin/faces/{face_id}/delete`：二次确认后删除人脸。
- `POST /admin/backup`：备份数据库。
- `POST /admin/restore`：维护模式 + 二次确认后恢复数据库。

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
- `NO_MATCH`、`LIVENESS_CHALLENGE_REQUIRED`、`LIVENESS_CHALLENGE_INVALID` 能映射到明确重试动作。
- 现场网络异常时客户端有 timeout 和 retry 限制，避免无限重试。
- 运维人员能在 `/audit/login/recent?terminal_id=<id>` 中看到该 terminal 的记录。

成功返回：

```json
{
  "authenticated": true,
  "message": "认证成功",
  "match": { "user_id": 10001, "username": "zhangsan" },
  "state": "trace-001",
  "elapsed_ms": 45.6
}
```

关键规则：
- 必须启用 API Key
- 图片必须且只能有 1 张脸
- 无人脸 / 多人脸 / 无匹配 / 脏底库记录都走结构化失败语义
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
  "max_image_pixels": 4096000
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
  match: { user_id: number | null; username: string };
  state?: string | null;
  elapsed_ms: number;
}
```

---

## 10. 联调建议

### 10.1 性能数据怎么看
文档里的耗时都应按：
- 历史经验值 / 参考值
- 受机器、GPU 是否真实生效、图片尺寸、底库规模影响

### 10.2 前端建议
- 上传前尽量压缩到 1000px 以内
- 前端超时建议设 30 秒
- 优先观察接口返回里的 `elapsed_ms`
- 鉴权统一在请求封装层注入 `X-API-Key`

### 10.3 联调顺序建议
1. `/health`
2. `/detect` 或 `/detect/base64`
3. `/compare`
4. `/faces/register` + `/search`
5. `/auth/face-login`
6. `/system/status` / `/config/effective` / 审计接口
