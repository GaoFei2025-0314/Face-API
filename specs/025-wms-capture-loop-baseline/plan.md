# 实施计划：Face API 与 WMS 现场联动验收基线

**分支/目录**：`025-wms-capture-loop-baseline`

**日期**：2026-06-18

**规格**：`specs/025-wms-capture-loop-baseline/spec.md`

## Summary

V2.4 建立 Face API 与 Electron WMS 的现场联动验收基线。实施重点是文档、模板、runbook、索引和检查流程，不默认修改 `face_api` 后端接口、不改 WMS 登录业务逻辑。

## Spec-kit Execution Note

当前仓库可能停留在 `main` 分支。原生 spec-kit 前置脚本会要求当前分支名类似 `025-wms-capture-loop-baseline`，否则 `check-prerequisites.ps1 -RequireTasks` 会失败。

后续实施二选一：

1. 如果使用原生 `/speckit-*` 命令，先创建或切换到 `025-wms-capture-loop-baseline` 分支。
2. 如果使用 `/goal` 执行本计划，使用 `.specify/feature.json` 和本计划中的显式路径，不依赖原生前置脚本推导 feature 目录。

## Technical Context

**语言/版本**：Markdown 文档、PowerShell 命令、Git。

**主要依赖**：现有 `face_api` 文档结构、spec-kit 目录、Electron WMS `doc/` 目录。

**存储**：无新增运行时存储；只新增 Markdown 文档。

**测试**：PowerShell `Test-Path`、`Select-String`、`git diff --check`，必要时运行现有 unittest 确认未改代码。

**目标平台**：Windows 工作站，本地 Face API 服务，本地 Electron WMS 仓库。

**项目类型**：本地 REST API 项目 + 外部 Electron WMS 项目联动验收文档。

**性能目标**：不引入运行时代码，不影响 Face API 请求性能。

**约束**：

- 不新增 `face_api` API。
- 不新增环境变量。
- 不新增数据库表。
- 不修改 WMS 登录业务逻辑。
- 不保存原图、视频帧、embedding、API Key 或真实用户敏感信息。
- 不自动猜测 WMS 仓库路径。

**规模/范围**：一次可复用联动验收基线，覆盖 Face API 仓库文档和 WMS 仓库 runbook。

## Constitution Check

当前 `.specify/memory/constitution.md` 仍是模板占位，没有可执行 MUST 条款。按项目实际约束执行：

- 保持 MVP 小范围。
- 文档变更必须同步索引和季度计划。
- 新版本进入实现前必须有 spec、plan、tasks 和验收标准。
- 不修改无关代码。

结论：通过。

## Project Structure

### Documentation

```text
specs/
├── ROADMAP-v2.4.md
└── 025-wms-capture-loop-baseline/
    ├── spec.md
    ├── plan.md
    ├── research.md
    ├── data-model.md
    ├── quickstart.md
    ├── checklists/
    │   └── requirements.md
    └── tasks.md

docs/
├── 01_document_index.md
├── 02_product/
│   └── 02_quarterly_plan.md
└── 90_archive/
    └── 04_acceptance/
        └── 08_face_api_wms_capture_loop_baseline.md
```

### External WMS Documentation

```text
H:\AI_test\electron-wms\electron-wms\doc\
└── 13-Face-API-WMS智能抓拍联动验收基线.md
```

## Research Decisions

完整决策见 `specs/025-wms-capture-loop-baseline/research.md`。

核心结论：

1. V2.4 先做 docs-only 联动验收基线。
2. Face API 保存算法底座和联动验收模板。
3. WMS 保存终端侧 runbook。
4. 问题归因固定为算法底座、终端采集、业务流程。

## Data Model

完整数据模型见 `specs/025-wms-capture-loop-baseline/data-model.md`。

V2.4 的“数据”是验收记录中的结构化字段，不是运行时数据库表。

## Implementation Phases

1. 建立 spec-kit V2.4 文档和索引。
2. 创建 Face API 侧联动验收模板。
3. 创建 WMS 侧终端 runbook。
4. 更新文档入口、季度计划和 agent 当前计划指针。
5. 执行静态验证和提交说明。

## Verification Plan

```powershell
git status --short
Test-Path 'H:\AI_test\face_api\specs\ROADMAP-v2.4.md'
Test-Path 'H:\AI_test\face_api\specs\025-wms-capture-loop-baseline\spec.md'
Test-Path 'H:\AI_test\face_api\specs\025-wms-capture-loop-baseline\plan.md'
Test-Path 'H:\AI_test\face_api\specs\025-wms-capture-loop-baseline\tasks.md'
Test-Path 'H:\AI_test\face_api\docs\90_archive\04_acceptance\08_face_api_wms_capture_loop_baseline.md'
Test-Path 'H:\AI_test\electron-wms\electron-wms\doc\13-Face-API-WMS智能抓拍联动验收基线.md'

$scanTerms = @('TB' + 'D', 'TO' + 'DO', '待' + '定', '占' + '位')
$scanPaths = @(
  'H:\AI_test\face_api\specs\ROADMAP-v2.4.md',
  'H:\AI_test\face_api\specs\025-wms-capture-loop-baseline\spec.md',
  'H:\AI_test\face_api\specs\025-wms-capture-loop-baseline\plan.md',
  'H:\AI_test\face_api\specs\025-wms-capture-loop-baseline\tasks.md',
  'H:\AI_test\face_api\docs\90_archive\04_acceptance\08_face_api_wms_capture_loop_baseline.md',
  'H:\AI_test\electron-wms\electron-wms\doc\13-Face-API-WMS智能抓拍联动验收基线.md'
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

- 风险：V2.4 被扩展成同时改两个项目的大功能。缓解：默认只做文档和验收基线，业务逻辑变更进入后续版本。
- 风险：WMS 仓库路径或工作区状态不一致。缓解：实施前先 `Test-Path` 和 `git status --short`，不覆盖未提交变更。
- 风险：在 `main` 分支直接运行原生 spec-kit 前置脚本失败。缓解：原生 spec-kit 流程先切换到 `025-wms-capture-loop-baseline` 分支，或使用 `/goal` 显式路径执行。
- 风险：Face API 与 WMS API Key 不一致导致 401/403。缓解：runbook 必须说明 WMS `faceService.js` 会把 `this.apiKey` 注入 `FACE_API_KEY`，并在请求中使用同一个值发送 `x-api-key`。
- 风险：验收记录变成主观描述。缓解：模板要求填写错误码、风险等级、相似度、耗时、audit 和日志证据。
- 风险：现场敏感数据进入文档。缓解：模板明确禁止保存原图、视频、embedding、API Key 和真实用户敏感信息。
