# V1.5-V1.7.1 前端与业务接入指南

> 适用范围：摄像头 login/register、错误码映射、业务系统调用示例、上线检查清单。

## 1. 接入目标

V1.5 的目标不是做一个完整业务前端，而是让前端和业务系统能按固定流程接入 `face_api`：

- 摄像头页面负责采集图片和连续帧。
- `face_api` 负责人脸检测、活体 challenge、注册和 face login 认证辅助。
- 业务系统负责用户主表、权限、token/session 和最终登录态。

示例页面：

```text
camera-integration.html
```

浏览器直接打开即可。V1.7.1 起该页面同时作为现场验收页，用来跑通“配置 -> 摄像头 -> 注册 -> 登录 -> 最近 audit”的闭环。该页面仅用于本机或内网联调，页面需要填写：

- `API Base URL`：默认 `http://localhost:8000`
- `API Key`：服务启动时 `FACE_API_KEY` 的值
- `terminal_id`：固定终端标识，例如 `front-door-camera-01`

页面不会把 `API Key` 或 `embedding` 输出到结果区。

页面在 login 完成后会自动刷新最近 login audit，同时保留手动刷新入口。audit 用于查看最近登录成功、失败、相似度、失败原因和 terminal_id。

正式上线时不要让浏览器直接持有 face_api 的 `X-API-Key`。推荐由业务后端保存密钥并代理调用 face_api，浏览器只持有业务系统自己的 session/token。

## 2. 摄像头 login 标准流程

1. 打开摄像头并获取用户授权。
2. 调用 `POST /liveness/challenges` 创建 login challenge。
3. 在动作窗口内连续采集 10 到 30 帧。
4. 调用 `POST /liveness/challenges/submit` 提交连续帧。
5. challenge 通过后采集登录图片。
6. 调用 `POST /auth/face-login`，带上 `terminal_id` 和一次性 `challenge_id`。
7. 业务系统使用返回的 `match.user_id` / `match.username` 查询自己的用户表，再签发自己的 token/session。

关键请求：

```json
{
  "purpose": "login",
  "terminal_id": "web-camera-01",
  "action": "blink"
}
```

```json
{
  "challenge_id": "passed-challenge-id",
  "purpose": "login",
  "terminal_id": "web-camera-01",
  "frames": ["data:image/jpeg;base64,..."]
}
```

```json
{
  "image": "data:image/jpeg;base64,...",
  "terminal_id": "web-camera-01",
  "challenge_id": "passed-challenge-id",
  "threshold": 0.6,
  "state": "trace-001"
}
```

## 3. 摄像头 register 标准流程

1. 打开摄像头。
2. 业务系统确认当前要注册的 `user_id` / `username`。
3. 如果后端启用了注册活体，先完成 register challenge。
4. 采集单人脸图片。
5. 调用 `POST /faces/register`，必须传 `terminal_id`。
6. 保存返回的 `face_id`，业务侧可把它和自己的用户记录做关联。

请求示例：

```json
{
  "user_id": 10001,
  "username": "zhangsan",
  "terminal_id": "web-camera-01",
  "challenge_id": "optional-passed-register-challenge-id",
  "image": "data:image/jpeg;base64,...",
  "metadata": {
    "source": "camera",
    "department": "研发部"
  }
}
```

注册图片必须只包含一个人。无人脸、多脸、质量低都应该提示用户重新采集。

## 4. 错误码映射表

| code | 用户提示 | 运维/开发处理 |
|---|---|---|
| `AUTH_INVALID_OR_MISSING` | 认证失败，请联系管理员检查配置。 | 确认服务启动时设置 `FACE_API_KEY`，请求头带 `X-API-Key`。 |
| `TERMINAL_ID_REQUIRED` | 终端信息缺失，请刷新页面后重试。 | 为每台摄像头配置固定 `terminal_id`，不要每次随机生成。 |
| `NO_FACE` | 没有检测到人脸，请靠近摄像头并保持正脸。 | 检查光线、角度、摄像头清晰度和图片裁剪。 |
| `MULTIPLE_FACES` | 画面中有多个人，请保持单人入镜。 | 注册和 login 都应要求单人画面。 |
| `FACE_QUALITY_LOW` | 图片质量不够，请调整光线或距离后重试。 | 检查检测置信度、亮度和脸框大小阈值。 |
| `LIVENESS_CHALLENGE_REQUIRED` | 请先完成活体动作。 | login 默认需要 `challenge_id`，注册是否需要取决于后端配置。 |
| `LIVENESS_CHALLENGE_INVALID` | 活体验证已失效，请重新完成动作。 | 检查 challenge 是否过期、用途/terminal 是否一致、是否已被使用。 |
| `LIVENESS_CHALLENGE_FAILED` | 活体动作未通过，请重新眨眼。 | 检查连续帧数量、用户动作和摄像头帧率。 |
| `LIVENESS_FRAME_COUNT_INVALID` | 采集帧数不足，请重新尝试。 | 按后端配置采集 10 到 30 帧。 |
| `NO_MATCH` | 未匹配到已注册用户。 | 检查用户是否已注册、阈值是否过高、现场图像质量。 |
| `VALIDATION_ERROR` | 请求参数不完整，请刷新后重试。 | 检查必填字段、JSON 格式和字段类型。 |
| `MAINTENANCE_MODE_ACTIVE` | 系统维护中，请稍后再试。 | 等待运维退出维护模式。 |

前端处理建议：

```javascript
function mapFaceApiError(payload) {
  const detail = payload && payload.detail;
  const code = detail && typeof detail === "object" ? detail.code : "UNKNOWN";
  const fallback = {
    userMessage: "请求失败，请稍后重试",
    operatorAction: "查看服务日志和接口返回 detail"
  };
  return ERROR_MAP[code] || fallback;
}
```

## 5. 业务系统调用示例

### 5.1 原生 fetch 封装

```javascript
const FACE_API_BASE = process.env.FACE_API_BASE || "http://localhost:8000";
const FACE_API_KEY = process.env.FACE_API_KEY || "";
const TERMINAL_ID = "web-camera-01";

async function faceApi(path, options = {}) {
  const res = await fetch(FACE_API_BASE + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(FACE_API_KEY ? { "X-API-Key": FACE_API_KEY } : {}),
      ...(options.headers || {})
    }
  });
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail || {};
    throw new Error(detail.reason || detail.message || "face_api request failed");
  }
  return data;
}
```

### 5.2 健康检查

```javascript
async function checkFaceApi() {
  return fetch(FACE_API_BASE + "/health").then(res => res.json());
}
```

### 5.3 注册

```javascript
async function registerFace({ userId, username, imageBase64, challengeId }) {
  return faceApi("/faces/register", {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      username,
      terminal_id: TERMINAL_ID,
      challenge_id: challengeId || null,
      image: imageBase64,
      metadata: { source: "business-web" }
    })
  });
}
```

### 5.4 Login

```javascript
async function faceLogin({ imageBase64, challengeId, traceId }) {
  const result = await faceApi("/auth/face-login", {
    method: "POST",
    body: JSON.stringify({
      image: imageBase64,
      terminal_id: TERMINAL_ID,
      challenge_id: challengeId,
      threshold: 0.6,
      state: traceId
    })
  });

  // face_api 不签发 token/session。
  // 业务系统应使用 result.match.user_id / result.match.username 查询自己的用户表。
  return result;
}
```

### 5.5 Audit 查询

```javascript
async function recentLoginAudit() {
  return faceApi(`/audit/login/recent?limit=20&terminal_id=${encodeURIComponent(TERMINAL_ID)}`);
}
```

## 6. Timeout、retry 和重复提交

- 摄像头采集前先禁用按钮，接口完成或失败后再恢复，避免重复提交。
- 前端请求超时建议 30 秒。
- `GET /health` 可以自动 retry。
- 注册、删除、恢复、face login 不建议自动无限 retry，避免重复写入或重复消费 challenge。
- challenge 失败或过期后重新创建，不复用旧 `challenge_id`。
- `terminal_id` 必须稳定，不能每次刷新页面随机生成。

## 7. 上线检查清单

- [ ] 后端服务能访问 `GET /health`。
- [ ] 受保护接口请求头包含正确 `X-API-Key`。
- [ ] 每台摄像头配置固定 `terminal_id`。
- [ ] login 流程先完成活体 challenge，再调用 `/auth/face-login`。
- [ ] 注册流程传入 `user_id`、`username`、`terminal_id` 和单人脸图片。
- [ ] 前端不会打印或保存 `API Key`、`embedding`。
- [ ] 常见错误码有中文用户提示和运维处理建议。
- [ ] 业务系统明确由自己签发 token/session。
- [ ] 网络超时、后端未启动、摄像头权限失败都有提示。
- [ ] `camera-integration.html` 能完成注册 + login 闭环。
- [ ] login 后页面自动刷新最近 audit。
- [ ] 可在 `/audit/login/recent` 查询指定 `terminal_id` 的登录记录。
