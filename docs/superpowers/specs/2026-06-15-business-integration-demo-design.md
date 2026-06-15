# V2.0 业务接入 Demo 套件设计

## 1. 版本定位

V2.0 定位为“业务系统正式接入示范版”。目标是让 `face_api` 从“自己能跑通的人脸识别服务”，推进到“真实业务系统可以照着接入的人脸识别底座”。

`face_api` 继续只做人脸识别、人脸库、活体和识别 audit，不接管业务用户、登录态、权限和组织架构。新增的业务能力放在独立 `business-demo` 服务里，用来模拟真实 Java / Spring Boot 业务系统。

## 2. 范围边界

V2.0 做：

- 新增独立 `business-demo`，模拟真实业务后端。
- `business-demo` 使用 FastAPI + SQLite，运行在 `http://localhost:8010`。
- 浏览器只访问 `business-demo`，不直接持有 `face_api` 的 `X-API-Key`。
- 同时规划 Web 业务系统链路和受控终端链路。
- Demo 实现最小 JWT，用来模拟真实业务登录态。
- 文档提供 Java / Spring Boot 接入伪代码。

V2.0 不做：

- 不把 `face_api` 改成用户系统。
- 不新增 `face_api` 公开接口。
- 不做完整权限系统、SSO、组织架构、复杂角色管理。
- 不做完整 Spring Boot demo 项目。
- 不引入前端框架。

## 3. 架构设计

推荐目录：

```text
face_api/
├─ business_demo/
│  ├─ app.py
│  ├─ storage.py
│  ├─ schemas.py
│  ├─ face_api_client.py
│  ├─ static/
│  │  ├─ index.html
│  │  └─ terminal.html
│  └─ README.md
├─ scripts/
│  ├─ run-business-demo.bat
│  └─ terminal-demo.py
└─ docs/
   └─ 04_usage/
      ├─ 04_business_integration_v2.md
      └─ 05_spring_boot_integration_notes.md
```

Web 链路：

```text
业务浏览器页面 -> business-demo:8010 -> face_api:8000
```

终端链路：

```text
terminal-demo.py / terminal.html / 受控终端 -> face_api:8000 -> business-demo:8010
```

## 4. 核心流程

业务用户先存在于 `business-demo` 的业务用户表。绑定人脸时，`business-demo` 调用 `face_api /faces/register`，把返回的 `face_id` 和业务 `user_id` 保存成一对一绑定。

Web 人脸登录必须走活体。`business-demo` 代理创建和提交 login challenge，再调用 `face_api /auth/face-login`。识别成功后，`business-demo` 查询自己的业务用户表，确认用户可用并签发 demo JWT。

受控终端允许持有 `face_api` 的 `X-API-Key`。终端页面和命令行脚本直接完成活体和 face login 后，把识别结果上报到 `business-demo`，由业务后端决定是否允许业务动作并写业务 audit。

## 5. 数据模型

`business-demo` 自己维护：

- `business_users`：业务用户主表。
- `face_bindings`：业务用户和 `face_api face_id` 的一对一绑定关系。
- `business_login_audits`：业务登录审计。

`face_api` 仍然只保存人脸记录、embedding 和识别 audit。业务用户资料不进入 `face_api`。

## 6. 错误处理

错误分两层：

- `face_api` 错误：`NO_FACE`、`MULTIPLE_FACES`、`LIVENESS_CHALLENGE_FAILED`、`NO_MATCH`。
- `business-demo` 错误：`BUSINESS_USER_NOT_FOUND`、`USER_DISABLED`、`FACE_ALREADY_BOUND`、`FACE_NOT_BOUND`、`TOKEN_INVALID`。

页面展示中文原因，业务 audit 记录机器可读错误码。

## 7. 验收标准

V2.0 后续实现完成时，应能验证：

- `face_api:8000` 和 `business-demo:8010` 能同时启动。
- `http://localhost:8010` 能展示统一业务接入 demo 页面。
- `http://localhost:8010/terminal.html` 能展示受控终端 demo 页面。
- 页面能列出示例业务用户并新增用户。
- 用户能绑定、解绑、换脸。
- 已绑定且启用的用户能通过活体 + 人脸登录拿到 demo JWT。
- 未绑定、禁用、识别失败、活体失败时能显示中文原因。
- `terminal-demo.py` 能模拟终端识别并上报业务登录事件。
- 文档包含 Java / Spring Boot 接入伪代码。
- 不新增 `face_api` 公开接口。
