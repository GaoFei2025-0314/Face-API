# 实施计划：通用接入契约与服务化基线

**分支/目录**：`026-general-integration-service-baseline`

**日期**：2026-06-19

**规格**：`specs/026-general-integration-service-baseline/spec.md`

## Summary

V2.5 建立 `face_api` 的通用接入契约与服务化基线。实施重点是文档、索引、接入模式、错误处理、运行基线和 `/goal` 执行入口，不修改公开 API、不新增 SDK、不改 WMS 代码。

## Spec-kit Execution Note

当前仓库可能停留在 `main` 分支。原生 spec-kit 前置脚本会要求当前分支名类似 `026-general-integration-service-baseline`，否则 `check-prerequisites.ps1 -RequireTasks` 可能失败。

后续实施二选一：

1. 如果使用原生 `/speckit-*` 命令，先创建或切换到 `026-general-integration-service-baseline` 分支。
2. 如果使用 `/goal` 执行本计划，使用 `.specify/feature.json` 和本计划中的显式路径，不依赖原生前置脚本推导 feature 目录。

## Technical Context

**语言/版本**：Markdown 文档、PowerShell 命令、Git。

**主要依赖**：现有 `face_api` 文档结构、spec-kit 目录、README、API 集成文档、Java / Spring Boot 接入说明。

**存储**：无新增运行时存储；只新增 Markdown 文档。

**测试**：PowerShell `Test-Path`、`Select-String`、`git diff --check`，必要时运行现有 unittest 确认未改代码。

**目标平台**：Windows 工作站、本地或边缘 Face API 服务、多类业务接入方。

**项目类型**：本地 REST API 服务的接入契约与服务化文档基线。

**性能目标**：不引入运行时代码，不影响 Face API 请求性能。

**约束**：

- 不新增公开 API。
- 不新增环境变量。
- 不新增数据库表。
- 不新增 SDK 或 WMS adapter。
- 不修改 WMS 代码。
- 不改变 `FACE_API_KEY` / `X-API-Key` 鉴权规则。
- 不把业务用户、token、权限、菜单或 WMS 业务流程放入 `face_api`。

## Constitution Check

当前 `.specify/memory/constitution.md` 仍是模板示例内容，没有可执行 MUST 条款。按项目实际约束执行：

- 保持 MVP 小范围。
- 文档变更必须同步索引和季度计划。
- 新版本进入实现前必须有 spec、plan、tasks 和验收标准。
- 不修改无关代码。

结论：通过。

## Project Structure

### Documentation

```text
specs/
├── ROADMAP-v2.5.md
└── 026-general-integration-service-baseline/
    ├── spec.md
    ├── plan.md
    ├── quickstart.md
    └── tasks.md

docs/
├── 01_document_index.md
├── 02_product/
│   └── 02_quarterly_plan.md
├── 04_usage/
│   └── 06_general_integration_contract.md
└── superpowers/
    └── specs/
        └── 2026-06-19-v2.5-general-integration-service-baseline-design.md
```

### Existing Documents To Keep Consistent

```text
README.md
docs/04_usage/01_api_integration.md
docs/04_usage/04_business_integration_v2.md
docs/04_usage/05_spring_boot_integration_notes.md
docs/03_deployment/01_runbook.md
architecture.html
AGENTS.md
.specify/feature.json
```

## Design Decisions

1. V2.5 采用 docs-only 路线，先固化通用接入契约。
2. 三类接入模式固定为业务后端代理、受控终端直连、本地运维验收。
3. 普通 Web 浏览器不得持有 `X-API-Key`。
4. WMS 后续接入走通用受控终端模式，不作为 `face_api` 专用设计中心。
5. 多项目共享实例、SDK、中心管理平台进入后续版本评估，不在 V2.5 实现。

## Implementation Phases

1. 建立 V2.5 roadmap 和 spec-kit 目录。
2. 新增通用接入契约文档。
3. 更新 README、文档入口、季度计划和 specs 索引。
4. 更新 `.specify/feature.json` 和 `AGENTS.md` 当前计划指针。
5. 执行静态验证和提交范围检查。

## Verification Plan

```powershell
git status --short
Test-Path 'H:\AI_test\face_api\specs\ROADMAP-v2.5.md'
Test-Path 'H:\AI_test\face_api\specs\026-general-integration-service-baseline\spec.md'
Test-Path 'H:\AI_test\face_api\specs\026-general-integration-service-baseline\plan.md'
Test-Path 'H:\AI_test\face_api\specs\026-general-integration-service-baseline\tasks.md'
Test-Path 'H:\AI_test\face_api\specs\026-general-integration-service-baseline\quickstart.md'
Test-Path 'H:\AI_test\face_api\docs\superpowers\specs\2026-06-19-v2.5-general-integration-service-baseline-design.md'
Test-Path 'H:\AI_test\face_api\docs\04_usage\06_general_integration_contract.md'
Test-Path 'H:\AI_test\face_api\docs\90_archive\04_acceptance\09_v2.5_acceptance_record.md'

$scanTerms = @(
  ('TB' + 'D')
  ('TO' + 'DO')
  ('待' + '定')
  ('占' + '位')
)
$scanPaths = @(
  'H:\AI_test\face_api\specs\ROADMAP-v2.5.md',
  'H:\AI_test\face_api\specs\026-general-integration-service-baseline\spec.md',
  'H:\AI_test\face_api\specs\026-general-integration-service-baseline\plan.md',
  'H:\AI_test\face_api\specs\026-general-integration-service-baseline\tasks.md',
  'H:\AI_test\face_api\specs\026-general-integration-service-baseline\quickstart.md',
  'H:\AI_test\face_api\docs\superpowers\specs\2026-06-19-v2.5-general-integration-service-baseline-design.md',
  'H:\AI_test\face_api\docs\04_usage\06_general_integration_contract.md',
  'H:\AI_test\face_api\docs\90_archive\04_acceptance\09_v2.5_acceptance_record.md',
  'H:\AI_test\face_api\docs\01_document_index.md',
  'H:\AI_test\face_api\docs\02_product\02_quarterly_plan.md',
  'H:\AI_test\face_api\specs\README.md',
  'H:\AI_test\face_api\README.md'
)
$missingScanPaths = $scanPaths | Where-Object { -not (Test-Path $_) }
if ($missingScanPaths) { throw "Missing scan path: $($missingScanPaths -join ', ')" }
Select-String -LiteralPath $scanPaths -Pattern $scanTerms -SimpleMatch

git diff --check
```

如果实施过程修改了代码，再运行：

```powershell
D:\anaconda3\envs\face_api\python.exe -m unittest discover -s tests -v
D:\anaconda3\envs\face_api\python.exe -m compileall main.py app_config.py api_errors.py api_schemas.py storage.py business_demo tests scripts
```

## 风险和缓解

- 风险：V2.5 变成 WMS 专用版本。缓解：所有文档先描述通用模式，WMS 只作为受控终端消费者。
- 风险：文档承诺 SDK 或多租户。缓解：明确列为后续评估，不在 V2.5 实现。
- 风险：浏览器误持有 API Key。缓解：通用契约和 README 都明确普通 Web 走业务后端代理。
- 风险：接入方误认为 `face_api` 签发业务 token。缓解：成功流明确由业务系统签发 session/JWT/SSO。
- 风险：后续 `/goal` 找不到当前计划。缓解：更新 `.specify/feature.json`、AGENTS 指针、specs 索引和季度计划。
