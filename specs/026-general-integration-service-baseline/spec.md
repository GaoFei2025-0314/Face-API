# 功能规格：通用接入契约与服务化基线

**功能分支**：`026-general-integration-service-baseline`

**创建时间**：2026-06-19

**状态**：已完成

**输入**：V2.4 已澄清 WMS 当前是内置算法直接识别登录，`face_api` 后续不应只服务 WMS，而应作为多项目复用的本地或边缘 REST API 服务。

## Clarifications

### Session 2026-06-19

- Q: V2.5 是 WMS 专用接入版本吗？ → A: 不是。V2.5 以 `face_api` 通用服务化为中心，WMS 只是未来消费者之一。
- Q: V2.5 是否新增公开 API？ → A: 不新增。先固化接入契约和服务边界。
- Q: V2.5 是否做 SDK？ → A: 不做。SDK、adapter 和多租户能力后续单独评估。
- Q: 普通浏览器能否直接保存 `X-API-Key`？ → A: 不能。普通 Web 项目默认走业务后端代理。
- Q: 受控终端能否直连？ → A: 可以，但必须由项目方管理设备、保存密钥、使用稳定 `terminal_id`，并能记录失败证据。

## 范围边界

V2.5 只建立通用接入契约与服务化文档基线：roadmap、spec、plan、tasks、quickstart、通用接入契约文档、索引和季度计划。不改 `face_api` 公开接口，不改 WMS 代码，不改算法策略。

## 用户场景与测试

### 用户故事 1 - 新项目负责人能判断接入模式（P1）

项目负责人需要知道普通 Web、Java 后端、Electron 终端、WMS 或外部系统应该按哪种模式接入 `face_api`。

**独立测试**：只阅读通用接入契约文档，能把一个接入方归到业务后端代理、受控终端直连或本地运维验收模式。

**验收场景**：

1. **假如** 接入方是浏览器业务系统，**当** 负责人查看接入契约，**那么** 能确定浏览器不持有 `X-API-Key`，应由业务后端代理。
2. **假如** 接入方是 Electron 或一体机，**当** 负责人查看接入契约，**那么** 能确定它可以作为受控终端直连，但必须配置稳定 `terminal_id`。

### 用户故事 2 - Java / Spring Boot 团队能按标准代理调用（P1）

Java 团队需要知道哪些字段由业务系统负责，哪些字段由 `face_api` 返回，避免把业务登录状态误放进 `face_api`。

**独立测试**：只阅读通用接入契约和现有 Spring Boot 文档，能画出浏览器、Java 后端、`face_api` 和业务用户表之间的数据流。

**验收场景**：

1. **假如** `/auth/face-login` 返回成功，**当** Java 后端处理结果，**那么** 它只使用 `match.user_id` 或 `match.username` 查询业务用户表，再签发自己的 session/JWT/SSO。
2. **假如** `/auth/face-login` 返回结构化错误，**当** Java 后端处理错误，**那么** 它按 `detail.code` 分支，展示 `detail.message` 或 `detail.reason`，不解析不透明 token。

### 用户故事 3 - 终端开发者能安全直连（P1）

受控终端开发者需要知道什么情况下可以把 API Key 放在终端侧，以及怎样处理活体、中风险重试和 audit。

**独立测试**：只阅读通用接入契约，终端开发者能列出直连前的设备管理、密钥、`terminal_id`、timeout、audit 检查要求。

**验收场景**：

1. **假如** 终端触发中风险重试，**当** 终端重新采集登录，**那么** 它必须重新创建 login challenge，并原样回传 `risk_retry_token`。
2. **假如** 终端登录失败，**当** 开发者排障，**那么** 能到 `/audit/login/recent?terminal_id=<id>` 查到最近失败原因。

### 用户故事 4 - 运维人员能按服务化基线检查现场状态（P2）

运维人员需要知道服务启动、停止、监控、CPU/GPU 切换、备份恢复和常见 401/403 排查入口。

**独立测试**：只阅读 README、runbook 和通用契约入口，能完成 `/health`、`/system/status`、`/config/effective`、audit 和备份恢复入口检查。

### 用户故事 5 - 后续 `/goal` 能直接执行 V2.5（P2）

后续开发者需要从 roadmap、spec、plan、tasks 和文档索引直接进入 V2.5，不重新翻聊天记录。

**独立测试**：从 `specs/README.md`、`docs/01_document_index.md` 和 `docs/02_product/02_quarterly_plan.md` 能找到 V2.5 执行入口、边界和验收标准。

## 边界情况

- 接入方要求浏览器直连生产服务并保存 API Key：文档必须明确拒绝，改走业务后端代理。
- 接入方要求 `face_api` 签发业务 token：文档必须明确这是业务系统职责。
- 接入方要求 WMS 专用接口：文档必须引导先遵守通用接入契约，专用 adapter 后续单独评估。
- 接入方希望多个业务系统共用一个实例：V2.5 只给出短中长期路线，不实现多租户。
- 接入方遇到 401/403：优先检查 `FACE_API_KEY`、`X-API-Key`、代理层和终端配置一致性。

## 功能需求

- **FR-001**：必须新增 V2.5 roadmap，说明通用接入契约与服务化基线的版本定位、范围、不做事项和推荐 `/goal`。
- **FR-002**：必须新增 `026-general-integration-service-baseline` spec-kit 目录，包含 `spec.md`、`plan.md`、`tasks.md` 和 `quickstart.md`。
- **FR-003**：必须新增通用接入契约文档，覆盖业务后端代理、受控终端直连、本地运维验收三种模式。
- **FR-004**：通用接入契约必须明确 `face_api` 不负责业务用户主表、权限、session/JWT/SSO、菜单、岗位或 WMS 业务流程。
- **FR-005**：通用接入契约必须说明普通 Web 浏览器不能保存或展示 `X-API-Key`。
- **FR-006**：通用接入契约必须说明受控终端直连的前提：设备受控、密钥受控、稳定 `terminal_id`、失败可审计。
- **FR-007**：通用接入契约必须包含中风险重试处理规则，明确 `risk_retry_token` 不可解析、不可展示、不可写入日志明文。
- **FR-008**：通用接入契约必须包含 401/403、timeout、`NO_FACE`、`MULTIPLE_FACES`、`NO_MATCH`、活体失败和高风险失败的处理入口。
- **FR-009**：必须同步 `README.md`、`docs/01_document_index.md`、`docs/02_product/02_quarterly_plan.md`、`specs/README.md`、`.specify/feature.json` 和 `AGENTS.md` 的当前计划指针。
- **FR-010**：必须提供静态检查命令，确认新增文档无未完成标记、版本号一致、路径存在、`git diff --check` 通过。
- **FR-011**：必须明确后续演进路线：短期一项目一实例，中期再评估 `app_id` / `client_id` / namespace，长期再评估中心化管理和 SDK。

## 关键实体

- **接入模式**：业务后端代理、受控终端直连、本地运维验收三类标准接入方式。
- **接入方**：普通 Web、Java / Spring Boot、Electron、WMS、终端设备或外部项目。
- **服务契约**：鉴权、核心 API、错误结构、中风险重试、audit、timeout 和运行检查的稳定约定。
- **职责边界**：`face_api` 与业务系统之间的责任划分。

## 成功标准

- **SC-001**：新项目负责人能在 5 分钟内判断自己的项目应使用哪种接入模式。
- **SC-002**：Java / Spring Boot 团队能从文档说明中确认业务 token 由业务后端签发，`face_api` 不接管登录态。
- **SC-003**：终端开发者能列出直连前必须满足的密钥、设备、`terminal_id` 和 audit 要求。
- **SC-004**：普通 Web 接入文档不再让浏览器持有 `X-API-Key`。
- **SC-005**：V2.5 文档明确不新增公开 API、不新增 SDK、不改 WMS 代码。
- **SC-006**：`specs/README.md`、`docs/01_document_index.md`、`docs/02_product/02_quarterly_plan.md` 和 README 都能指向 V2.5。
- **SC-007**：`git diff --check` 通过；未完成标记扫描无输出。

## 假设

- 当前主服务仍运行在 Windows 工作站，默认端口 `8000`。
- `FACE_API_KEY` / `X-API-Key` 仍是当前鉴权机制。
- V2.5 不改变现有 API 行为，只统一文档口径和后续实施入口。
- 外部项目初期按“一项目一 Face API 实例”部署。
