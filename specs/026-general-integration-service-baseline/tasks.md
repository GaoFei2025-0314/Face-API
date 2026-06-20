# Tasks: 通用接入契约与服务化基线

**Input**: `spec.md`, `plan.md`, `quickstart.md`, `docs/superpowers/specs/2026-06-19-v2.5-general-integration-service-baseline-design.md`

**Tests**: 本版本以文档和契约基线为主；默认不改代码。文档变更必须先定义可验证检查，再创建或修改文档。

## Phase 1: Setup

- [X] T001 检查 Face API 工作区状态和分支策略：`git status --short`、`git branch --show-current`；原生 spec-kit 流程需切换到 `026-general-integration-service-baseline` 分支，`/goal` 流程使用显式路径
- [X] T002 读取 `docs/superpowers/specs/2026-06-19-v2.5-general-integration-service-baseline-design.md`
- [X] T003 读取现有接入文档：`docs/04_usage/01_api_integration.md`、`docs/04_usage/04_business_integration_v2.md`、`docs/04_usage/05_spring_boot_integration_notes.md`

## Phase 2: Foundational

- [X] T004 [P] 确认 `docs/04_usage/06_general_integration_contract.md` 尚未存在或已准备更新
- [X] T005 [P] 确认 `README.md`、`docs/01_document_index.md`、`specs/README.md`、`docs/02_product/02_quarterly_plan.md` 都需要同步 V2.5 入口
- [X] T006 [P] 确认 `.specify/feature.json`、`AGENTS.md` 和 `CLAUDE.md` 当前计划指针需要指向 `026-general-integration-service-baseline`

## Phase 3: User Story 1 - 新项目负责人能判断接入模式 (P1)

**Goal**: 创建通用接入模式说明。

**Independent Test**: 只阅读通用接入契约文档，能把接入方归到业务后端代理、受控终端直连或本地运维验收模式。

- [X] T007 [US1] 创建或更新 `docs/04_usage/06_general_integration_contract.md`
- [X] T008 [US1] 在通用契约中写清三种接入模式、适用对象、API Key 存放位置和禁止事项
- [X] T009 [US1] 在通用契约中明确 WMS 只是未来消费者之一，不是 `face_api` 专用设计中心

## Phase 4: User Story 2 - Java / Spring Boot 团队能按标准代理调用 (P1)

**Goal**: 把业务后端代理模式写成稳定契约。

**Independent Test**: Java 团队能从文档确认浏览器、业务后端、`face_api` 和业务用户表之间的数据流。

- [X] T010 [US2] 在通用契约中增加 Web 业务登录数据流，明确浏览器不持有 `X-API-Key`
- [X] T011 [US2] 在通用契约中增加 Java / Spring Boot 代理职责：保存 API Key、代理 Face API、查询业务用户表、签发业务 session/JWT/SSO
- [X] T012 [US2] 复核 `docs/04_usage/05_spring_boot_integration_notes.md`，确保其与通用契约不矛盾

## Phase 5: User Story 3 - 终端开发者能安全直连 (P1)

**Goal**: 把受控终端直连规则写成稳定契约。

**Independent Test**: 终端开发者能列出直连前必须满足的密钥、设备、`terminal_id`、timeout 和 audit 要求。

- [X] T013 [US3] 在通用契约中增加受控终端直连数据流
- [X] T014 [US3] 在通用契约中写清直连前提：设备受控、密钥受控、稳定 `terminal_id`、失败可审计
- [X] T015 [US3] 在通用契约中增加中风险重试规则，明确 `risk_retry_token` 不可解析、不可展示、不可写日志明文

## Phase 6: User Story 4 - 运维人员能按服务化基线检查现场状态 (P2)

**Goal**: 把服务化运行检查入口集中到通用契约和 README。

**Independent Test**: 运维人员能完成 `/health`、`/system/status`、`/config/effective`、audit、CPU/GPU 和备份恢复入口检查。

- [X] T016 [US4] 在通用契约中增加运行检查入口：启动、停止、健康检查、状态、配置、audit、备份恢复
- [X] T017 [US4] 在通用契约中增加 401/403、timeout、摄像头、活体、无匹配和现场慢的排障入口
- [X] T018 [US4] 更新 `README.md` 的当前阶段和文档入口，指向 V2.5 通用接入契约

## Phase 7: User Story 5 - 后续 `/goal` 能直接执行 V2.5 (P2)

**Goal**: 同步 spec-kit 入口和项目文档索引。

**Independent Test**: 从 `specs/README.md`、`docs/01_document_index.md` 和 `docs/02_product/02_quarterly_plan.md` 能找到 V2.5 执行入口、边界和验收标准。

- [X] T019 [US5] 更新 `specs/README.md`，新增 `ROADMAP-v2.5.md` 和 `026-general-integration-service-baseline` 入口
- [X] T020 [US5] 更新 `docs/01_document_index.md`，新增通用接入契约阅读入口
- [X] T021 [US5] 更新 `docs/02_product/02_quarterly_plan.md`，新增 V2.5 当前计划、边界和推荐 `/goal`
- [X] T022 [US5] 更新 `.specify/feature.json`，指向 `specs/026-general-integration-service-baseline`
- [X] T023 [US5] 更新 `AGENTS.md` 和 `CLAUDE.md` 的 SPECKIT 当前计划指针，指向 `specs/026-general-integration-service-baseline/plan.md`

## Phase 8: Verification

- [X] T024 运行路径检查，确认 V2.5 roadmap、spec、plan、tasks、quickstart、设计文档、通用接入契约和 V2.5 验收记录文件存在
- [X] T025 运行未完成标记扫描，覆盖 V2.5 roadmap、spec、plan、tasks、quickstart、设计文档、通用接入契约、V2.5 验收记录、README、文档索引、季度计划和 specs 索引
- [X] T026 运行 `git diff --check`
- [X] T027 若未修改 Python/JS 代码，记录“不需要运行 unittest”；若修改了代码，运行全量 unittest 和 compileall
- [X] T028 检查 staged 文件，确保没有误提交 code review 报告、数据库、日志、模型或 WMS 仓库文件

## Commit Boundary Commands

Face API 仓库只提交 Face API 侧文档和 spec-kit 文件：

```powershell
git status --short
git add -- 'specs/ROADMAP-v2.5.md' 'specs/README.md' 'specs/026-general-integration-service-baseline' 'docs/superpowers/specs/2026-06-19-v2.5-general-integration-service-baseline-design.md' 'docs/04_usage/06_general_integration_contract.md' 'docs/90_archive/04_acceptance/09_v2.5_acceptance_record.md' 'docs/01_document_index.md' 'docs/02_product/02_quarterly_plan.md' 'README.md' '.specify/feature.json' 'AGENTS.md' 'CLAUDE.md'
git commit -m "docs: complete v2.5 general integration service baseline"
```

禁止使用 `git add .`。

## Dependencies & Execution Order

- Phase 1 必须先完成，避免在错误分支或脏工作区写入。
- Phase 2 可并行检查。
- US1 是核心 MVP，必须先完成。
- US2 和 US3 可并行处理。
- US4 依赖通用契约文件已创建。
- US5 依赖 V2.5 文档路径确定。
- Verification 最后执行。

## Parallel Opportunities

- T004、T005、T006 可并行。
- T010-T012 与 T013-T015 可由两个 agent 分别处理。
- T019、T020、T021 可在通用契约文件稳定后并行处理。

## Implementation Strategy

1. 先完成 US1，建立通用接入模式和职责边界。
2. 再完成 US2/US3，把普通 Web/Java 与受控终端两条主链路写清楚。
3. 然后完成 US4，把运行检查和排障入口写清楚。
4. 最后完成 US5，同步所有入口和当前计划指针。
5. 不在 V2.5 中临时实现 SDK、WMS adapter、多租户或新 API；这些进入后续版本评估。
