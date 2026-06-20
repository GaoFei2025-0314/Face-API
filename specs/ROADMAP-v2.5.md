# face_api Roadmap v2.5

> 创建时间：2026-06-19
> 用途：定义 V2.5 通用接入契约与服务化基线的范围、边界和执行入口
> 状态：已完成

## 1. 版本定位

V2.5 的目标是把 `face_api` 从“某个项目可用的人脸识别服务”收敛成“多个项目都能按统一方式接入的本地或边缘 REST API 服务”。

本版本不继续扩展 WMS 专用适配，也不急着做 SDK。WMS、普通 Web、Java / Spring Boot、Electron、受控终端和外部项目都应先遵守同一套通用接入契约。

> V2.5 = 通用接入契约与服务化基线。

## 2. 交付范围

| 范围 | Spec | 主题 | 目标 |
|---|---|---|---|
| 服务定位 | `specs/026-general-integration-service-baseline` | 通用服务定位 | 明确 `face_api` 做什么、不做什么，以及接入方职责边界 |
| 接入模式 | `specs/026-general-integration-service-baseline` | 三类接入模式 | 固化业务后端代理、受控终端直连、本地运维验收三种模式 |
| 契约规则 | `specs/026-general-integration-service-baseline` | 接口与错误契约 | 梳理核心 API、鉴权、错误码、中风险重试、audit 和 timeout 规则 |
| 运行基线 | `specs/026-general-integration-service-baseline` | 服务化运行基线 | 梳理 Windows 启停、监控、CPU/GPU、备份恢复和现场排障入口 |
| 文档同步 | `specs/026-general-integration-service-baseline` | 文档索引同步 | 更新 README、文档入口、季度计划、specs 索引和 agent 当前计划指针 |

## 3. 已确认决策

- V2.5 先做通用接入契约与服务化文档基线。
- V2.5 不新增公开 API，不改 `main.py` 路由行为。
- V2.5 不新增数据库表，不新增环境变量。
- V2.5 不实现 Java SDK、JavaScript SDK 或 WMS adapter。
- 普通 Web 项目默认使用业务后端代理模式，浏览器不持有 `X-API-Key`。
- Electron、一体机、闸机、Windows 客户端等受控设备可以使用受控终端直连模式。
- `admin.html`、`camera-integration.html`、`acceptance.html` 属于本地运维验收模式，不等于正式业务前端模式。
- 登录成功后由业务系统签发 session/JWT/SSO，`face_api` 只返回识别结果和失败原因。
- WMS 未来接入时按通用接入契约执行，不单独让 `face_api` 长出 WMS 专用接口。

## 4. 明确不做

- 不新增公开 API。
- 不新增 SDK。
- 不修改 WMS 代码。
- 不修改算法阈值。
- 不新增多租户、`app_id`、`client_id` 或 namespace 的真实实现。
- 不做中心化管理平台、配额系统或统一账号系统。
- 不改变 `FACE_API_KEY` / `X-API-Key` 鉴权规则。
- 不把业务用户、权限、菜单、岗位、仓库流程放进 `face_api`。

## 5. 推荐执行入口

```text
/goal Implement face_api Roadmap V2.5 - General Integration Service Baseline
```

实施前先阅读：

```text
docs/superpowers/specs/2026-06-19-v2.5-general-integration-service-baseline-design.md
specs/026-general-integration-service-baseline/spec.md
specs/026-general-integration-service-baseline/plan.md
specs/026-general-integration-service-baseline/tasks.md
specs/026-general-integration-service-baseline/quickstart.md
docs/04_usage/06_general_integration_contract.md
```

## 6. 验收总则

- [x] 新接入方能从文档判断自己属于哪种接入模式。
- [x] 普通 Web、Java / Spring Boot、Electron / 终端、WMS 后续接入都有统一入口说明。
- [x] API Key、timeout、错误码、中风险重试和 audit 查询规则表达一致。
- [x] README、文档入口、季度计划和 specs 索引都指向 V2.5。
- [x] 文档明确 V2.5 不新增公开 API、不新增 SDK、不改 WMS 代码。
- [x] `git diff --check` 通过。
