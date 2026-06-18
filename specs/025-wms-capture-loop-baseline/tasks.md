# Tasks: Face API 与 WMS 现场联动验收基线

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `docs/superpowers/specs/2026-06-17-face-api-wms-capture-loop-design.md`

**Tests**: 本版本以文档和流程基线为主；行为改动不在默认范围内。文档变更必须先定义可验证检查，再创建或修改文档。

## Phase 1: Setup

- [X] T001 检查 Face API 工作区状态和分支策略：`git status --short`、`git branch --show-current`；原生 spec-kit 流程需切换到 `025-wms-capture-loop-baseline` 分支，`/goal` 流程使用显式路径
- [X] T002 检查 WMS 仓库路径和工作区状态：`Test-Path 'H:\AI_test\electron-wms\electron-wms'` 与 `git -C 'H:\AI_test\electron-wms\electron-wms' status --short`
- [X] T003 读取 `docs/superpowers/specs/2026-06-17-face-api-wms-capture-loop-design.md` 和 `docs/superpowers/plans/2026-06-17-face-api-wms-capture-loop-baseline.md`

## Phase 2: Foundational

- [X] T004 [P] 确认 `docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md` 尚未存在
- [X] T005 [P] 确认 `H:\AI_test\electron-wms\electron-wms\doc\13-Face-API-WMS智能抓拍联动验收基线.md` 尚未存在
- [X] T006 [P] 确认 `docs/01_document_index.md`、`specs/README.md`、`docs/02_product/02_quarterly_plan.md` 已有 V2.4 规划入口，且验收模板和 WMS runbook 仍待创建

## Phase 3: User Story 1 - 验收人员能记录完整联动链路 (P1)

**Goal**: 创建 Face API 侧联动验收模板。

**Independent Test**: 只打开模板即可填写环境快照、启动检查、样例矩阵、单次样例、问题分类、验收结论和下一轮改进项。

- [X] T007 [US1] 创建 `docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md`
- [X] T008 [US1] 在 `docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md` 增加环境快照、启动检查、样例矩阵和单次样例记录表
- [X] T009 [US1] 在 `docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md` 增加问题分类、验收结论和下一轮改进清单
- [X] T010 [US1] 验证 Face API 模板不包含原图、视频帧、embedding、API Key 或真实用户敏感信息

## Phase 4: User Story 2 - WMS 终端开发者能按 runbook 复现现场检查 (P1)

**Goal**: 创建 WMS 侧终端 runbook。

**Independent Test**: 只打开 WMS runbook 即可完成启动、摄像头权限、本地人脸库、Face API 连通性、页面提示和日志证据检查。

- [X] T011 [US2] 创建 `H:\AI_test\electron-wms\electron-wms\doc\13-Face-API-WMS智能抓拍联动验收基线.md`
- [X] T012 [US2] 在 WMS runbook 中增加启动前检查、终端侧操作流程、Face API 连通检查和 API Key 对齐检查
- [X] T013 [US2] 在 WMS runbook 中增加日志与证据收集、问题归因规则、401/403 排查规则和验收后输出
- [X] T014 [US2] 验证 WMS runbook 链接 Face API 联动验收模板

## Phase 5: User Story 3 - 项目负责人能用统一规则决定下一轮改哪里 (P2)

**Goal**: 把问题归因规则和下一轮决策入口同步到文档索引和季度计划。

**Independent Test**: 从项目入口文档能找到 V2.4 联动验收基线，并理解问题只能归到算法底座、终端采集或业务流程。

- [X] T015 [US3] 复核 `docs/01_document_index.md` 的 V2.4 入口，并在模板和 runbook 创建后补成实际文件入口
- [X] T016 [US3] 复核 `specs/README.md` 已包含 `ROADMAP-v2.4.md` 和 `025-wms-capture-loop-baseline`
- [X] T017 [US3] 复核 `docs/02_product/02_quarterly_plan.md` 已记录 V2.4 当前计划、范围和验收边界

## Phase 6: User Story 4 - 后续 `/goal` 能直接执行 V2.4 (P2)

**Goal**: 让后续 agent 或开发者能直接从当前计划进入实施。

**Independent Test**: 从 `AGENTS.md` 的 SPECKIT 指针能找到 V2.4 plan，`/goal` 可直接引用 V2.4 roadmap。

- [X] T018 [US4] 复核 `.specify/feature.json` 已指向 `specs/025-wms-capture-loop-baseline`
- [X] T019 [US4] 复核 `AGENTS.md` 的 SPECKIT 当前计划指针已指向 `specs/025-wms-capture-loop-baseline/plan.md`
- [X] T020 [US4] 复核 `specs/ROADMAP-v2.4.md` 的推荐 `/goal` 命令和实施前阅读清单

## Phase 7: Verification

- [X] T021 运行未完成标记扫描，覆盖 V2.4 roadmap、spec、plan、tasks、Face API 验收模板和 WMS runbook，命令必须先检查所有扫描路径存在
- [X] T022 运行路径检查，确认 Face API 模板和 WMS runbook 文件存在
- [X] T023 运行 `git diff --check`
- [X] T024 分别检查 Face API 和 WMS 仓库 staged 文件，确保提交范围不混用
- [X] T025 形成提交说明：Face API 文档提交与 WMS 文档提交分开处理

## Commit Boundary Commands

Face API 仓库只提交 Face API 侧文档和 spec-kit 文件：

```powershell
git -C 'H:\AI_test\face_api' status --short
git -C 'H:\AI_test\face_api' add -- 'specs/ROADMAP-v2.4.md' 'specs/README.md' 'specs/025-wms-capture-loop-baseline' 'docs/01_document_index.md' 'docs/02_product/02_quarterly_plan.md' 'docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md'
git -C 'H:\AI_test\face_api' commit -m "docs: add v2.4 wms capture loop baseline"
```

WMS 仓库只提交 WMS 侧 runbook：

```powershell
git -C 'H:\AI_test\electron-wms\electron-wms' status --short
git -C 'H:\AI_test\electron-wms\electron-wms' add -- 'doc/13-Face-API-WMS智能抓拍联动验收基线.md'
git -C 'H:\AI_test\electron-wms\electron-wms' commit -m "docs: add face api wms capture loop runbook"
```

禁止在任一仓库使用 `git add .` 处理本版本跨仓库变更。

## Dependencies & Execution Order

- Phase 1 必须先完成，避免在错误仓库或脏工作区写入。
- Phase 2 可并行检查。
- US1 和 US2 可在路径确认后并行实施。
- US3 依赖 US1/US2 的文件路径确定。
- US4 依赖 V2.4 spec-kit 文档完成。
- Verification 最后执行。

## Parallel Opportunities

- T004、T005、T006 可并行。
- T007-T010 与 T011-T014 可由两个 agent 分别处理。
- T015、T016、T017 可在模板和 runbook 路径确定后并行处理。

## Implementation Strategy

1. 先完成 US1，建立 Face API 侧验收模板，形成 MVP。
2. 再完成 US2，把 WMS 侧操作和日志回收落到 WMS 仓库。
3. 最后完成 US3/US4，同步索引、季度计划和 agent 指针。
4. 不在 V2.4 中临时修改算法或 WMS 业务逻辑；真实联动验收暴露的问题进入 V2.5 或独立修复版本。
