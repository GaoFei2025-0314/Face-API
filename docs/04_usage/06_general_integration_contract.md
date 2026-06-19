# Face API 通用接入契约

> 最后同步：2026-06-19
> 适用阶段：V2.5 通用接入契约与服务化基线

这份文档回答一个问题：

> 一个新项目应该怎样接入 `face_api`？

它不替代完整 API 文档。请求体、返回体和错误码细节继续看：

- `docs/04_usage/01_api_integration.md`
- `docs/04_usage/05_spring_boot_integration_notes.md`
- `docs/03_deployment/01_runbook.md`

## 1. 核心定位

`face_api` 是本地或边缘人脸识别 REST API 服务。它负责识别能力和运行证据，不负责业务系统本身。

它负责：

- 人脸检测、注册、搜索、比对。
- login 活体 challenge。
- 轻量防翻拍风险结果。
- `/auth/face-login` 登录辅助。
- 中文错误原因。
- audit、运行状态、配置状态。
- Windows 工作站启动、停止、监控、备份恢复说明。

它不负责：

- 业务用户主表。
- 权限、角色、菜单、岗位。
- session、JWT、SSO。
- WMS 或其他项目的业务流程。
- 多租户、配额、中心管理平台。

## 2. 三种接入模式

| 模式 | 适用对象 | API Key 位置 | 推荐程度 |
|---|---|---|---|
| 业务后端代理 | 普通 Web、Java / Spring Boot、外部业务系统 | 业务后端配置 | 默认推荐 |
| 受控终端直连 | Electron、一体机、闸机、Windows 客户端 | 受控终端配置 | 受控内网可用 |
| 本地运维验收 | `admin.html`、`camera-integration.html`、`acceptance.html` | 页面临时填写 | 只用于调试验收 |

### 2.1 业务后端代理模式

普通 Web 项目默认使用这个模式。

```text
浏览器
-> 业务后端
-> face_api
-> 业务后端查用户表
-> 业务后端签发 session/JWT/SSO
-> 浏览器进入业务系统
```

规则：

- 浏览器不保存、不展示、不打印 `X-API-Key`。
- 业务后端保存 `FACE_API_KEY`。
- 业务后端代理调用 `face_api`。
- 业务后端解析 `detail.code/message/reason`。
- 登录成功后，业务后端用 `match.user_id` 或 `match.username` 查询自己的用户表。
- 业务后端签发自己的 session/JWT/SSO。

### 2.2 受控终端直连模式

Electron、一体机、闸机、Windows 客户端可以使用这个模式。

```text
受控终端摄像头
-> face_api
-> 终端拿到 match 和风险结果
-> 业务后端校验用户状态
-> 业务系统完成登录或放行
```

前提：

- 设备由项目方管理。
- API Key 可以安全配置在终端环境中。
- 每台设备有稳定 `terminal_id`。
- 失败结果能进入终端日志、业务 audit 或 Face API audit。
- 终端有 timeout 和重试上限，不能无限请求。

WMS 后续接入时，应该先按这个通用模式评估，而不是要求 `face_api` 增加 WMS 专用接口。

### 2.3 本地运维验收模式

这些页面属于本地或内网验收工具：

- `admin.html`
- `camera-integration.html`
- `acceptance.html`

它们可以临时填写 API Key，用来做服务检查、摄像头验收、audit 排查和现场报告。它们不是正式互联网业务前端模式。

## 3. 标准 login 链路

1. 创建 login challenge：

```text
POST /liveness/challenges
```

2. 提交连续帧：

```text
POST /liveness/challenges/submit
```

3. 使用通过后的 `challenge_id` 登录：

```text
POST /auth/face-login
```

4. 登录成功后，业务系统处理：

```text
match.user_id / match.username
-> 查询业务用户表
-> 检查用户状态、权限、岗位、业务条件
-> 签发业务 session/JWT/SSO
```

`face_api` 不签发业务 token。

## 4. 中风险重试契约

第一次 `/auth/face-login` 返回：

```json
{
  "detail": {
    "code": "ANTI_SPOOF_MEDIUM_RETRY_REQUIRED",
    "message": "检测到中风险，请重试一次",
    "reason": "当前画面存在轻量防翻拍中风险，请重新面对摄像头完成一次采集",
    "retry": {
      "risk_retry_token": "<opaque-token>",
      "expires_at": "2026-06-19T12:00:00Z",
      "remaining_attempts": 1
    }
  }
}
```

客户端规则：

- `risk_retry_token` 是不透明 token。
- 只能原样保存并回传。
- 不要解析 token。
- 不要展示 token。
- 不要把 token 明文写入日志、audit 或验收报告。
- 第二次必须重新创建 login challenge。
- 第二次必须重新采集连续帧和登录图片。
- 第二次 `/auth/face-login` 同时传新的 `challenge_id` 和上一次的 `risk_retry_token`。
- 第二次仍中风险时，按失败或人工处理，不要无限重试。

## 5. 错误处理契约

接入方以 `detail.code` 做程序分支，以 `detail.message` / `detail.reason` 做中文展示和排障说明。

| 错误 | 接入方处理 |
|---|---|
| `AUTH_INVALID_OR_MISSING` | 检查 `FACE_API_KEY`、`X-API-Key` 和代理层配置 |
| `NO_FACE` | 提示用户靠近摄像头、保持正脸、调整光线 |
| `MULTIPLE_FACES` | 提示保持单人入镜 |
| `FACE_QUALITY_LOW` | 提示重新采集，检查光线、距离、清晰度 |
| `LIVENESS_CHALLENGE_REQUIRED` | 先创建并提交 login challenge |
| `LIVENESS_CHALLENGE_INVALID` | 重新创建 challenge，不复用旧 challenge |
| `LIVENESS_CHALLENGE_FAILED` | 提示重新眨眼或调整采集条件 |
| `ANTI_SPOOF_MEDIUM_RETRY_REQUIRED` | 重新采集一次并回传 `risk_retry_token` |
| `ANTI_SPOOF_MEDIUM_RETRY_EXHAUSTED` | 本次失败，转人工或业务失败处理 |
| `ANTI_SPOOF_HIGH_RISK` | 本次失败，不继续业务登录 |
| `NO_MATCH` | 检查是否已注册、阈值、图片质量 |
| `MAINTENANCE_MODE_ACTIVE` | 提示系统维护中 |

完整错误码见 `docs/04_usage/01_api_integration.md`。

## 6. timeout 和重试

建议：

- 普通接口超时：10 到 30 秒。
- 摄像头 login 整体流程：前端或终端应有提交中状态。
- 网络失败可以允许用户手动重试。
- 中风险重试只能按后端 token 规则重试一次。
- 不要在客户端写无限循环重试。

## 7. audit 和排障

常用入口：

```text
GET /health
GET /system/status
GET /config/effective
GET /audit/login/recent
GET /audit/login/summary
```

排障顺序：

1. `/health` 看服务是否可达。
2. `/system/status` 看 CPU/GPU、模型、底库数量、auth 状态。
3. `/config/effective` 看阈值、CORS、活体和防翻拍配置。
4. `/audit/login/recent?terminal_id=<id>` 看最近失败原因。
5. 查启动窗口、日志、终端采集日志或业务后端日志。

## 8. Windows 服务化运行

首次运行：

```bat
set FACE_API_KEY=your-secret
run.bat
```

生产类运行：

```bat
set FACE_API_KEY=your-secret
run-prod.bat
```

强制 CPU：

```bat
set FACE_FORCE_CPU=1
set FACE_USE_GPU=0
```

启用 GPU：

```bat
set FACE_FORCE_CPU=0
set FACE_USE_GPU=1
```

规则：

- 默认优先 CPU，适合 Windows 工作站稳定运行。
- 需要 GPU 时显式设置 `FACE_USE_GPU=1`。
- 临时强制 CPU 时设置 `FACE_FORCE_CPU=1`；它会覆盖 GPU 开关。

备份恢复、Task Scheduler 和 NSSM 见：

- `docs/03_deployment/01_runbook.md`

## 9. 后续演进边界

短期：

- 一个项目一个 Face API 实例。
- 用统一文档和验收清单降低接入成本。

中期：

- 多项目共用实例时，再评估 `app_id`、`client_id`、namespace 和项目级 audit。

长期：

- 外部客户规模扩大后，再评估 SDK、中心管理、配额和统一审计。

V2.5 不实现这些能力。
