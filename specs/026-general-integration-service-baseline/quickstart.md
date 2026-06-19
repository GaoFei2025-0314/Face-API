# Quickstart：V2.5 通用接入契约与服务化基线

> 目标：让新接入方用最短路径判断自己怎么接 `face_api`。

## 1. 先判断接入模式

| 接入方 | 推荐模式 | API Key 放哪里 |
|---|---|---|
| 普通 Web 前端 | 业务后端代理 | 业务后端配置 |
| Java / Spring Boot 系统 | 业务后端代理 | Java 后端配置 |
| Electron / Windows 客户端 | 受控终端直连 | 受控终端配置 |
| 一体机 / 闸机 / 自助机 | 受控终端直连 | 受控终端配置 |
| 本机验收页面 | 本地运维验收 | 页面临时填写 |
| WMS 后续接入 | 受控终端直连或业务后端代理 | 按 WMS 部署形态决定 |

普通互联网浏览器不要保存 `X-API-Key`。

## 2. 最小服务检查

```powershell
curl http://localhost:8000/health
```

启用 API Key 后检查运行状态：

```powershell
curl -H "X-API-Key: 123456" http://localhost:8000/system/status
curl -H "X-API-Key: 123456" http://localhost:8000/config/effective
```

## 3. 最小登录链路

1. 创建 login challenge：`POST /liveness/challenges`。
2. 提交连续帧：`POST /liveness/challenges/submit`。
3. 使用通过后的 `challenge_id` 调用：`POST /auth/face-login`。
4. 登录成功后，业务系统根据 `match.user_id` 或 `match.username` 查询自己的用户表。
5. 业务系统签发自己的 session/JWT/SSO。

## 4. 中风险重试

第一次 `/auth/face-login` 返回 `ANTI_SPOOF_MEDIUM_RETRY_REQUIRED` 时：

1. 客户端只保存 `detail.retry.risk_retry_token`，不要展示、解析或写入日志明文。
2. 重新创建 login challenge。
3. 重新采集连续帧和登录图片。
4. 第二次 `/auth/face-login` 同时传新的 `challenge_id` 和上一次的 `risk_retry_token`。
5. 第二次仍失败时，不要无限重试，按业务失败或人工处理。

## 5. 排障入口

| 问题 | 优先检查 |
|---|---|
| 服务不可用 | `GET /health`、启动窗口、端口占用 |
| 401 / 403 | `FACE_API_KEY`、请求头 `X-API-Key`、代理层配置 |
| 摄像头无画面 | 浏览器权限、摄像头占用、终端采集日志 |
| 活体失败 | 连续帧数量、光线、眨眼动作、`terminal_id` |
| 中风险重试失败 | token 是否过期、是否复用旧 challenge、terminal 是否一致 |
| 登录无匹配 | 用户是否注册、阈值、图片质量、audit |
| 现场慢 | `elapsed_ms`、CPU/GPU 状态、图片尺寸、底库规模 |

## 6. 继续阅读

- 通用契约：`docs/04_usage/06_general_integration_contract.md`
- 接口细节：`docs/04_usage/01_api_integration.md`
- Java 接入：`docs/04_usage/05_spring_boot_integration_notes.md`
- 运维运行：`docs/03_deployment/01_runbook.md`
- V2.5 任务：`specs/026-general-integration-service-baseline/tasks.md`

