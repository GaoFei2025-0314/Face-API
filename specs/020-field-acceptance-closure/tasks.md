# 任务：现场验收收口与 P1/P2 小修

## Phase 1: Setup

- [x] T001 阅读 `specs/ROADMAP-v1.9.md`、`specs/020-field-acceptance-closure/spec.md`、`specs/020-field-acceptance-closure/plan.md` 和 `docs/90_archive/04_acceptance/03_v1.9_acceptance_record.md`。
- [x] T002 确认工作区干净：在 `H:\AI_test\face_api` 执行 `git status --short`，结果应为空。
- [x] T003 运行基线测试：执行 `D:\anaconda3\envs\face_api\python.exe -m unittest discover -s tests -v`，结果应全部通过。
- [x] T004 运行基线检查：执行 `git diff --check`，结果应无 whitespace 错误。

## Phase 2: Foundational

- [x] T005 [P] 检查本地 HTML 外部依赖：对 `architecture.html`、`camera-integration.html`、`admin.html` 执行 `Select-String` 扫描并记录到 `docs/90_archive/04_acceptance/03_v1.9_acceptance_record.md`。
- [x] T006 [P] 检查文档入口：确认 `docs/01_document_index.md` 能指向启动、接入、架构、性能和版本来源。
- [x] T007 [P] 检查接口文档：确认 `docs/04_usage/01_api_integration.md` 说明 `/admin/overview` 是轻量概览，`GET /faces` 才是人脸列表。

## Phase 3: User Story 1 - Windows 工作站运行验收 (P1)

**独立测试标准**：服务能启动，`/health`、`/system/status`、`/config/effective` 能返回可解释状态，停止和监控入口清楚。

- [x] T008 [US1] 按 `README.md` 和 `docs/03_deployment/01_runbook.md` 启动服务，记录启动命令和结果到 `docs/90_archive/04_acceptance/03_v1.9_acceptance_record.md`。
- [x] T009 [US1] 验证 `GET /health`，记录 HTTP 状态和返回内容到 `docs/90_archive/04_acceptance/03_v1.9_acceptance_record.md`。
- [x] T010 [US1] 验证 `GET /system/status` 和 `GET /config/effective`，记录设备、鉴权、人脸库数量和维护模式到 `docs/90_archive/04_acceptance/03_v1.9_acceptance_record.md`。
- [x] T011 [US1] 验证 `scripts/monitor-service.ps1` 和 `scripts/stop-service.ps1` 的说明或实际运行结果，记录到 `docs/90_archive/04_acceptance/03_v1.9_acceptance_record.md`。
- [x] T012 [US1] 如果 T008-T011 发现 P1/P2 问题，先在 `tests/test_scripts_smoke.py`、`tests/test_main_api.py` 或对应测试文件补失败测试，再最小修复 `run.bat`、`run-prod.bat`、`scripts/*.ps1`、`main.py` 或 `docs/03_deployment/01_runbook.md`。

## Phase 4: User Story 2 - 摄像头注册登录闭环验收 (P1)

**独立测试标准**：`camera-integration.html` 能完成摄像头授权、注册、login challenge、face login，并显示中文结果和最近 audit。

- [x] T013 [US2] 打开 `camera-integration.html`，记录 API 地址、API Key 配置和摄像头授权结果到 `docs/90_archive/04_acceptance/03_v1.9_acceptance_record.md`。
- [x] T014 [US2] 完成一次 `/faces/register` 注册，记录 user_id、username、结果和失败原因到 `docs/90_archive/04_acceptance/03_v1.9_acceptance_record.md`，不得记录 embedding。
- [x] T015 [US2] 完成一次 login challenge 和 `/auth/face-login`，记录匹配结果、similarity、活体状态和耗时到 `docs/90_archive/04_acceptance/03_v1.9_acceptance_record.md`。
- [x] T016 [US2] 触发至少一个失败场景，确认页面显示中文 `message` 和 `reason`，记录到 `docs/90_archive/04_acceptance/03_v1.9_acceptance_record.md`。
- [x] T017 [US2] 验证最近 login audit 展示，记录成功、失败和失败原因到 `docs/90_archive/04_acceptance/03_v1.9_acceptance_record.md`。
- [x] T018 [US2] 如果 T013-T017 发现 P1/P2 问题，先在 `tests/test_main_api.py` 或可自动化的 HTML 检查中补失败测试，再最小修复 `camera-integration.html`、`main.py`、`api_errors.py` 或 `docs/04_usage/02_frontend_business_integration.md`。

## Phase 5: User Story 3 - 文档和架构一致性验收 (P2)

**独立测试标准**：项目负责人能从文档入口找到当前目标、启动方式、接口契约、架构图和验收记录，且内容与实际行为一致。

- [x] T019 [US3] 检查 `docs/02_product/01_prd.md` 和 `docs/02_product/02_quarterly_plan.md`，确认 V1.9 目标和边界一致。
- [x] T020 [US3] 检查 `specs/README.md` 和 `specs/ROADMAP-v1.9.md`，确认后续 `/goal` 入口明确。
- [x] T021 [US3] 检查 `architecture.html`，确认模块节点、接口入口、运维流程和当前实现一致。
- [x] T022 [US3] 如发现文档与实际行为不一致，更新 `README.md`、`docs/01_document_index.md`、`docs/03_deployment/01_runbook.md`、`docs/04_usage/01_api_integration.md`、`docs/04_usage/02_frontend_business_integration.md` 或 `architecture.html` 中对应内容。

## Final Phase: Closure

- [x] T023 重新运行 `D:\anaconda3\envs\face_api\python.exe -m unittest discover -s tests -v`。
- [x] T024 重新运行 `git diff --check`。
- [x] T025 重新扫描本地 HTML 外部依赖并确认无新增外部脚本、样式、`import` 或 `require`。
- [x] T026 更新 `docs/90_archive/04_acceptance/03_v1.9_acceptance_record.md` 的完成状态、验证命令、残余风险和 commit 信息。
- [x] T027 提交 V1.9 实施结果，建议 commit message：`feat: complete roadmap v1.9 field acceptance closure`。
