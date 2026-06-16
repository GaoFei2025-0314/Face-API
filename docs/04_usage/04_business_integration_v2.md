# V2.0 业务系统接入说明

> 适用范围：业务前端、业务后端、受控终端接入 `face_api` 的标准流程。

## 1. 接入原则

`face_api` 只做人脸识别服务，不做业务用户系统。正式业务系统必须自己管理：

- 用户主表。
- 登录态、session、JWT 或 SSO。
- 权限和角色。
- 业务登录 audit。
- 最终是否允许登录、开门、签到或执行业务动作。

`face_api` 返回的是识别证据，包括 `user_id`、`username`、`similarity`、`threshold`、活体状态和失败原因。业务系统根据这些证据做最终判断。

## 2. Web 业务系统推荐链路

正式 Web 链路：

```text
业务浏览器页面
  -> 业务后端
  -> face_api
```

这样做的原因：

- 浏览器不直接持有 `face_api` 的 `X-API-Key`。
- 业务后端可以统一处理用户状态、登录态、权限和 audit。
- 真实 Java / Spring Boot 后端可以替换 V2.0 的 `business-demo`。

V2.0 demo 中：

```text
http://localhost:8010
```

是业务接入页面入口。它只调用 `business-demo`，不直接调用 `face_api`。
页面包含摄像头预览、业务用户列表、绑定、解绑、换脸、Web 活体登录和业务 audit 面板。

V2.0 还规划一个受控终端页面：

```text
http://localhost:8010/terminal.html
```

该页面用于演示一体机、闸机、Windows 客户端等受控终端直接调用 `face_api` 的模式。它可以填写 `X-API-Key`，但只适用于受控内网终端，不适用于普通 Web 业务页面。

## 3. 业务用户和人脸绑定

推荐流程：

```text
业务系统先有用户
  -> 选择用户
  -> 采集人脸
  -> 业务后端调用 face_api /faces/register
  -> 业务后端保存 user_id 和 face_id 绑定
```

约束：

- 一个业务用户只允许一个有效人脸绑定。
- 已绑定用户再次绑定时，应提示先解绑或执行换脸。
- 换脸建议采用补偿式流程：“注册新 face_id -> 切换有效绑定 -> 删除或标记清理旧 face_id”。这样新脸注册失败时，旧绑定不会被提前破坏。
- 业务用户资料不要写入 `face_api`，只传必要的 `user_id`、`username` 和 metadata。

绑定活体由 `business-demo` 配置控制：

```text
BUSINESS_DEMO_BINDING_LIVENESS_REQUIRED=0
```

默认关闭，便于现场快速绑定。正式现场如果担心照片代绑，可以开启；开启后绑定流程必须先完成 register challenge。

生产类演示部署时，`business-demo` 还需要替换默认 token 签名密钥：

```text
BUSINESS_DEMO_ENV=production
BUSINESS_DEMO_TOKEN_SECRET=<随机长密钥>
```

默认 `business-demo-dev-secret` 只用于本机开发。设置 `BUSINESS_DEMO_ENV=production` 后，如果仍使用默认密钥，服务会拒绝启动。

## 4. Web 人脸登录

推荐流程：

```text
业务页面请求创建 login challenge
  -> 业务后端调用 face_api /liveness/challenges
  -> 页面采集连续帧
  -> 业务后端调用 face_api /liveness/challenges/submit
  -> 页面采集登录图片
  -> 业务后端调用 face_api /auth/face-login
  -> 业务后端查询自己的用户表
  -> 业务后端签发自己的 token/session
```

登录规则：

- 登录必须启用活体。
- `face_api` 不签发业务 token。
- `matched_user_id` 必须回到业务用户表校验。
- 用户不存在、禁用、未绑定或绑定不一致时，业务后端必须拒绝登录。

## 5. 受控终端链路

受控终端包括一体机、闸机、Windows 客户端、自助机等。它们由项目方管理，可以配置 `face_api` 的 `X-API-Key`。

V2.0 同时规划两种终端 demo：

- `http://localhost:8010/terminal.html`：页面模式，适合现场演示。
- `scripts/terminal-demo.py`：命令行模式，适合验收和排障。

推荐流程：

```text
受控终端
  -> 直接调用 face_api 完成活体和 face login
  -> 得到 matched_user_id / similarity / terminal_id
  -> 上报业务后端
  -> 业务后端确认用户状态并写业务 audit
```

终端要求：

- 每台终端使用稳定 `terminal_id`。
- 每次上报使用稳定唯一的 `event_id`，用于重试幂等处理。
- 上报 `recognized_at_epoch`，业务后端拒绝过期识别结果。
- 终端不要把 API Key 打印到界面、日志或错误信息里。
- 终端失败时展示中文原因。
- 终端上报业务后端时要带上 trace/state，便于排障。

`terminal.html` 会先打开摄像头预览，采集连续帧提交 `/liveness/challenges/submit`，再把通过后的 `challenge_id` 带入 `/auth/face-login`。

`terminal-demo.py` 支持三种方式：

```bat
python scripts\terminal-demo.py --terminal-id gate-01 --event-id event-001 --camera-index 0 --api-key your-secret
python scripts\terminal-demo.py --terminal-id gate-01 --event-id event-002 --image login.jpg --liveness-frame frame01.jpg --liveness-frame frame02.jpg --liveness-frame frame03.jpg --liveness-frame frame04.jpg --liveness-frame frame05.jpg --liveness-frame frame06.jpg --liveness-frame frame07.jpg --liveness-frame frame08.jpg --liveness-frame frame09.jpg --liveness-frame frame10.jpg --api-key your-secret
python scripts\terminal-demo.py --terminal-id gate-01 --event-id event-003 --image login.jpg --challenge-id passed-login-challenge-id --api-key your-secret
```

文件帧模式至少传 10 帧。现场验收更推荐摄像头模式，因为它能连续采集活体帧和登录图片。

只有当 `face_api` 明确关闭 login 活体时，才使用：

```bat
python scripts\terminal-demo.py --terminal-id gate-01 --image login.jpg --skip-liveness --api-key your-secret
```

## 6. business-demo API 契约

这些接口属于 `business-demo`，不属于 `face_api`。

| 接口 | 请求核心字段 | 响应核心字段 |
|---|---|---|
| `GET /api/users` | `status?` | `users[]` |
| `POST /api/users` | `user_id`、`username`、`display_name?`、`department?` | `user` |
| `POST /api/users/{user_id}/face-binding` | `image`、`terminal_id`、`challenge_id?` | `binding.user_id`、`binding.face_id` |
| `DELETE /api/users/{user_id}/face-binding` | `confirm=true` | `ok`、`removed_face_id` |
| `POST /api/users/{user_id}/face-binding/replace` | `image`、`terminal_id`、`challenge_id?` | `binding`、`old_face_id` |
| `POST /api/auth/liveness/challenge` | `purpose=login`、`terminal_id` | `challenge_id`、`action`、`status` |
| `POST /api/auth/liveness/submit` | `challenge_id`、`terminal_id`、`frames[]` | `passed`、`reason`、`result_reason` |
| `POST /api/auth/face-login` | `image`、`terminal_id`、`challenge_id`、`state?` | `authenticated`、`token`、`user`、`face`、`audit_id` |
| `GET /api/auth/me` | `Authorization: Bearer <demo-token>` | `authenticated`、`user` |
| `POST /api/terminal/login-events` | `event_id`、`terminal_id`、`matched_user_id`、`similarity`、`recognized_at_epoch`、`state?`、`face_api_result` | `accepted`、`duplicate?`、`user?`、`failure_reason?`、`audit_id` |
| `GET /api/audit/login` | `limit?`、`terminal_id?`、`success?` | `items[]`、`count` |

终端上报时，`business-demo` 会校验 `face_api_result.authenticated=true`，并确认 `face_api_result.match.user_id` 等于 `matched_user_id`。如果 `face_api_result.match.face_id` 存在，还会确认它等于当前业务有效绑定的 `face_id`。

统一错误响应：

```json
{
  "detail": {
    "code": "FACE_NOT_BOUND",
    "message": "业务用户未绑定人脸",
    "reason": "该业务用户还没有绑定人脸，请先完成绑定后再登录"
  }
}
```

## 7. 业务层错误码建议

| code | 中文原因 |
|---|---|
| `BUSINESS_USER_NOT_FOUND` | 业务用户不存在，请先在业务系统中创建用户 |
| `USER_DISABLED` | 该业务用户已禁用，不能登录 |
| `FACE_ALREADY_BOUND` | 该业务用户已经绑定过人脸，请先解绑或执行换脸 |
| `FACE_NOT_BOUND` | 该业务用户还没有绑定人脸 |
| `TOKEN_INVALID` | 登录凭证无效或已过期，请重新登录 |
| `FACE_API_UNAVAILABLE` | 人脸识别服务不可用，请检查 face_api 是否启动 |
| `FACE_API_AUTH_FAILED` | 人脸识别服务认证失败，请检查服务端 API Key 配置 |
| `FACE_API_REQUEST_FAILED` | 人脸识别服务拒绝了本次请求 |
| `FACE_API_LOGIN_REJECTED` | 人脸识别服务没有返回认证成功 |
| `FACE_API_MATCH_MISMATCH` | 人脸识别返回的用户或人脸记录与业务绑定不一致 |
| `LIVENESS_CHALLENGE_REQUIRED` | 当前流程需要先完成活体 challenge |
| `VALIDATION_ERROR` | 请求参数格式或取值不符合业务 demo 接口要求 |
| `TERMINAL_EVENT_EXPIRED` | 终端识别结果已过期，请重新识别后再上报 |
| `TERMINAL_EVENT_TIME_INVALID` | 终端识别时间不在允许窗口内 |
| `DUPLICATE_TERMINAL_EVENT` | 终端事件已经处理过，本次重试不会重复写入 audit |

业务页面应优先展示业务层中文原因；如果错误来自 `face_api`，展示 `detail.reason`。

## 8. 上线检查清单

- [ ] 浏览器不直接访问 `face_api` 受保护接口。
- [ ] 浏览器不保存、不展示、不打印 `face_api` 的 `X-API-Key`。
- [ ] 对 `business_demo/static/index.html` 做静态扫描，确认没有 `X-API-Key`、`FACE_API_KEY` 或 `faceApiKey`。
- [ ] 业务后端能访问 `face_api /health`。
- [ ] 业务后端已配置 `face_api` 地址和 API Key。
- [ ] 业务用户先存在，再绑定人脸。
- [ ] 一个业务用户只有一个有效人脸绑定。
- [ ] 登录必须完成活体 challenge。
- [ ] 登录成功后由业务系统签发 token/session。
- [ ] 业务登录成功和失败都写入业务 audit。
- [ ] 终端使用稳定 `terminal_id`。
- [ ] 终端上报使用唯一 `event_id` 并传入 `recognized_at_epoch`。
- [ ] 终端密钥只放在受控设备配置中。
- [ ] `terminal.html` 和 `terminal-demo.py` 都只用于受控终端或验收场景。
- [ ] Java / Spring Boot 生产接入已替换 demo JWT。
