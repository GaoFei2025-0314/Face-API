# Tasks: 轻量防翻拍阈值治理与中风险重试机制

**Input**: `spec.md`, `plan.md`, `docs/superpowers/specs/2026-06-17-v2.3-lightweight-anti-spoof-governance-design.md`

**Tests**: 按 TDD 执行；每个行为改动先写失败测试，再最小实现。

## Phase 1: Setup

- [X] T001 确认 V2.2 验收报告已归档为 V2.3 输入基线
- [X] T002 确认 `specs/ROADMAP-v2.3.md`、`spec.md`、`plan.md`、`tasks.md` 已同步
- [X] T003 更新 `specs/README.md`、季度计划和 AGENTS spec-kit 当前指针

## Phase 2: Backend Contract Tests

- [X] T004 为 `FACE_ANTI_SPOOF_MEDIUM_ACTION` 和 `FACE_ANTI_SPOOF_RETRY_TOKEN_TTL_SECONDS` 增加配置解析失败测试，确认最大重试次数在 V2.3 固定为 1 且不依赖环境变量
- [X] T005 为后端签发和校验 `risk_retry_token` 增加失败测试，证明不能依赖客户端 `state` 绕过
- [X] T006 为中风险重试错误响应增加 face login 失败测试，断言 `detail.code=ANTI_SPOOF_MEDIUM_RETRY_REQUIRED` 和 `detail.retry.risk_retry_token`、`detail.retry.expires_at`、`detail.retry.remaining_attempts`
- [X] T007 为中风险最多重试 1 次增加 face login 失败测试
- [X] T008 为翻拍样例不应低风险成功增加轻量评分单元测试
- [X] T009 为 audit 记录中风险原因、处理动作和 retry 状态增加测试
- [X] T010 在 `tests/test_storage_schema.py` 增加旧库迁移测试，覆盖 `ALTER TABLE` 兼容、token hash 存储、索引创建、过期 token 清理或忽略、已使用 token 不可复用

## Phase 3: Backend Implementation

- [X] T011 在 `app_config.py` 增加或调整中风险策略和 retry token TTL 配置；默认 `FACE_ANTI_SPOOF_MEDIUM_ACTION=retry`、`FACE_ANTI_SPOOF_RETRY_TOKEN_TTL_SECONDS=300`
- [X] T012 在 `api_errors.py` 增加 `ANTI_SPOOF_MEDIUM_RETRY_REQUIRED` 错误码、中文原因和 `retry` 元数据支持
- [X] T013 在 `api_schemas.py` 为 `/auth/face-login` 增加可选 `risk_retry_token` 字段
- [X] T014 在 `storage.py` 增加后端 retry token 状态保存和校验能力，token 必须以 hash 或不可逆摘要保存，一次性、短期有效、绑定 terminal
- [X] T015 增强 `evaluate_anti_spoof_risk()`，减少移动照片或屏幕被判为 `normal_motion`
- [X] T016 在 `/auth/face-login` 中按策略处理中风险，默认不返回登录成功
- [X] T017 确保中风险和高风险都写入 login audit，包含 risk level、reasons、action、terminal 和 retry 状态

## Phase 4: Frontend And Report

- [X] T018 更新 `camera-integration.html`，展示中风险重试提示、保存本次 `risk_retry_token` 并在下一次重试时回传
- [X] T019 更新 `acceptance.html`，报告区分中风险重试、失败、高风险和低风险成功
- [X] T020 更新 `business-demo` 页面或后端处理：中风险 retry 显示“请重试一次”，第二次仍中风险显示失败或人工处理
- [X] T021 确认 JSON/CSV 仍不包含 API Key、原图、连续帧、embedding 或原始 retry token

## Phase 5: Docs And Architecture

- [X] T022 更新 `README.md` 环境变量表，说明 `FACE_ANTI_SPOOF_MEDIUM_ACTION`、`FACE_ANTI_SPOOF_RETRY_TOKEN_TTL_SECONDS`、最大重试固定 1 次和 retry token 行为
- [X] T023 更新 `docs/04_usage/01_api_integration.md`，固定 `detail.retry` 错误响应契约
- [X] T024 更新 `docs/04_usage/03_recognition_security_accuracy.md`
- [X] T025 更新 `docs/04_usage/05_spring_boot_integration_notes.md`
- [X] T026 更新 `architecture.html`
- [X] T027 完成 `docs/90_archive/04_acceptance/07_v2.3_acceptance_record.md`

## Phase 6: Verification

- [X] T028 运行聚焦后端测试
- [X] T029 运行页面和业务 demo smoke 测试
- [X] T030 运行全量 unittest
- [X] T031 运行 compileall 和 `git diff --check`
- [X] T032 使用 `acceptance.html` 复验五类样例，每类 3 次
- [X] T033 复核 V2.3 验收记录并准备版本完成提交说明
