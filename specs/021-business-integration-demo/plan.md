# 实施计划：业务接入 Demo 套件

## 范围

V2.0 建立一个完整但轻量的业务接入 demo，让真实业务系统可以参考它接入 `face_api`。本计划不改变 `face_api` 公开接口，重点是在 `face_api` 外围新增独立业务 demo、终端 demo、文档和验收脚本。

本计划覆盖：

- 独立 `business-demo` 服务。
- 业务用户、绑定关系和业务登录 audit。
- Web 业务接入页面。
- 最小 demo JWT。
- 终端命令行 demo。
- Java / Spring Boot 接入说明。
- V2.0 文档、Roadmap 和验收入口。

## 技术上下文

**语言/版本**：Python 3.10.x；文档同时说明 Java / Spring Boot 接入方式。

**主要依赖**：FastAPI、SQLite、requests 或标准 HTTP client、原生 HTML/CSS/JS。

**存储**：`business-demo` 使用独立 SQLite 文件；`face_api` 继续使用现有 `faces.db`。

**测试**：继续使用 `python -m unittest discover -s tests -v`；新增 business demo 单元测试、脚本 smoke test 和 HTML 静态检查。

**目标平台**：本地 Windows 工作站。

**项目类型**：本地 REST API + 独立 mock 业务后端 + 本地 demo 页面。

**性能目标**：demo 以正确性和可解释性优先；Web 登录和终端上报应能在现场演示中稳定完成。

**约束**：

- 不新增 `face_api` 公开接口。
- 浏览器不得直接持有 `face_api` 的 `X-API-Key`。
- 终端 demo 必须使用稳定 `terminal_id`。
- 不引入前端框架。
- 不把完整用户系统塞进 `face_api`。

## 设计决策

- 新增 `business_demo/` 目录，和 `main.py` 所在的 `face_api` 主服务分离。
- `business-demo` 服务端持有 `face_api` 地址和 API Key。
- `business-demo` 页面由 `business-demo` 服务提供，入口为 `http://localhost:8010`。
- 业务用户表和人脸绑定表由 `business-demo` 管理。
- 一个业务用户只有一个有效绑定。
- Web 登录由 `business-demo` 代理完成活体和 face login，再签发 demo JWT。
- 终端 demo 直接调用 `face_api`，再向 `business-demo` 上报业务登录事件。
- Java / Spring Boot 文档说明如何替换 `business-demo`，不提供完整 Java 项目。

## 目标目录结构

```text
business_demo/
├── app.py
├── storage.py
├── schemas.py
├── face_api_client.py
├── static/
│   └── index.html
└── README.md

scripts/
├── run-business-demo.bat
└── terminal-demo.py

docs/04_usage/
├── 04_business_integration_v2.md
└── 05_spring_boot_integration_notes.md

specs/021-business-integration-demo/
├── spec.md
├── plan.md
├── tasks.md
└── checklists/
    └── requirements.md
```

## 业务 API 规划

`business-demo` 规划接口：

- `GET /api/users`
- `POST /api/users`
- `POST /api/users/{user_id}/face-binding`
- `DELETE /api/users/{user_id}/face-binding`
- `POST /api/users/{user_id}/face-binding/replace`
- `POST /api/auth/liveness/challenge`
- `POST /api/auth/liveness/submit`
- `POST /api/auth/face-login`
- `GET /api/auth/me`
- `POST /api/terminal/login-events`
- `GET /api/audit/login`

这些接口只属于 `business-demo`，不属于 `face_api` 公开接口。

## 验证

V2.0 实施时必须执行：

```powershell
D:\anaconda3\envs\face_api\python.exe -m unittest discover -s tests -v
git diff --check
```

并补充：

```powershell
Select-String -Path "H:\AI_test\face_api\business_demo\static\index.html" -Pattern "cdn|script src|link rel=.*stylesheet|import |require\("
```

手工验收必须覆盖：

- `face_api:8000` 启动。
- `business-demo:8010` 启动。
- 示例业务用户可见。
- 新增业务用户。
- 绑定人脸。
- 活体 + face login 成功并返回 demo JWT。
- 未绑定、禁用、活体失败和识别失败能显示中文原因。
- 解绑后登录失败。
- 重新绑定后登录成功。
- 终端 demo 上报业务登录事件。
- 业务 audit 可查询。
