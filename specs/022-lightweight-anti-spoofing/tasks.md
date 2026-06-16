# Tasks: 轻量防翻拍活体增强

**Input**: Design documents from `specs/022-lightweight-anti-spoofing/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api-contract.md`, `quickstart.md`

**Tests**: 本功能按 TDD 执行；每个用户故事的测试任务必须先写，并确认在实现前失败。

**Organization**: 任务按用户故事分组，保证每个故事都能独立实现、独立验证、独立验收。

## Phase 1: Setup

**Purpose**: 锁定 V2.1 基线，避免把上一轮 code review 文件和本版本实现混在一起。

- [X] T001 Run baseline `git status`, full unittest, and `git diff --check`; record result in `docs/90_archive/04_acceptance/05_v2.1_acceptance_record.md`
- [X] T002 [P] Review V2.1 scope and assumptions in `specs/ROADMAP-v2.1.md`
- [X] T003 [P] Review API compatibility contract in `specs/022-lightweight-anti-spoofing/contracts/api-contract.md`
- [X] T004 [P] Review manual acceptance sample matrix in `specs/022-lightweight-anti-spoofing/quickstart.md`

---

## Phase 2: Foundational

**Purpose**: 建立所有用户故事共用的轻量风险语义、配置、错误码和持久化基础。

**Critical**: Phase 2 完成前不要开始任何用户故事实现。

- [X] T005 Add lightweight anti-spoof configuration parsing and defaults in `app_config.py`
- [X] T006 [P] Add failing configuration tests for anti-spoof defaults and invalid values in `tests/test_app_config.py`
- [X] T007 Add `AntiSpoofRisk` and related optional response fields in `api_schemas.py`
- [X] T008 [P] Add `ANTI_SPOOF_HIGH_RISK` structured Chinese error definition in `api_errors.py`
- [X] T009 Add backward-compatible SQLite schema migration fields for risk JSON in `storage.py`
- [X] T010 [P] Add failing schema migration tests for risk columns in `tests/test_storage_schema.py`
- [X] T011 Add shared JSON serialization/deserialization helpers for anti-spoof risk records in `storage.py`
- [X] T012 [P] Expose anti-spoof policy summary in `/config/effective` and `/system/status` tests in `tests/test_main_api.py`
- [X] T013 Implement anti-spoof policy summary responses in `main.py`

**Checkpoint**: 配置、错误码、schema、基础响应模型已经可用，用户故事可以开始。

---

## Phase 3: User Story 1 - 登录时降低明显翻拍通过风险 (Priority: P1)

**Goal**: 在不默认增加复杂动作的前提下，让 login 和 liveness challenge 输出低/中/高风险，并阻断高风险。

**Independent Test**: 使用 mocked 连续帧和 face login 流程验证真人低风险通过、静态照片/屏幕类高风险拒绝、中风险不默认阻断。

### Tests for User Story 1

- [X] T014 [P] [US1] Add failing tests for low/medium/high risk scoring outcomes in `tests/test_main_api.py`
- [X] T015 [P] [US1] Add failing tests for `/liveness/challenges/submit` returning `anti_spoof_risk` in `tests/test_main_api.py`
- [X] T016 [P] [US1] Add failing tests for `/auth/face-login` blocking high-risk attempts with `ANTI_SPOOF_HIGH_RISK` in `tests/test_main_api.py`
- [X] T017 [P] [US1] Add failing tests that low-risk face login remains backward compatible in `tests/test_main_api.py`

### Implementation for User Story 1

- [X] T018 [US1] Implement lightweight frame variation, face-box stability, sharpness variation, and insufficient-signal scoring helpers in `main.py`
- [X] T019 [US1] Map scoring signals to `low`, `medium`, and `high` risk levels with stable reason codes in `main.py`
- [X] T020 [US1] Integrate anti-spoof risk calculation into `/liveness/challenges/submit` in `main.py`
- [X] T021 [US1] Integrate high-risk blocking into `/auth/face-login` before final authentication success in `main.py`
- [X] T022 [US1] Ensure high-risk login and liveness failures use Chinese user-facing messages from `api_errors.py`
- [X] T023 [US1] Keep low-risk and medium-risk flows compatible with existing liveness configuration in `main.py`
- [X] T024 [US1] Show concise anti-spoof risk state and retry guidance in `camera-integration.html`
- [X] T025 [US1] Add business demo response handling for `anti_spoof_risk` in `business_demo/app.py`
- [X] T026 [US1] Show anti-spoof risk hints without exposing metrics in `business_demo/static/index.html`
- [X] T027 [US1] Show terminal login risk result in `business_demo/static/terminal.html`
- [X] T028 [US1] Show terminal CLI risk level and Chinese action hint in `scripts/terminal-demo.py`

**Checkpoint**: US1 独立完成后，真人低风险登录不增加复杂动作，高风险样例会被拒绝并显示中文提示。

---

## Phase 4: User Story 2 - 运维人员能复核翻拍风险原因 (Priority: P1)

**Goal**: audit 和运维视图能看到风险等级、原因码和 terminal 信息，便于现场判断是画面质量、活体失败还是疑似翻拍。

**Independent Test**: 构造成功、普通失败、中风险和高风险登录记录，查看 `/audit/login/recent` 和页面展示是否能区分原因。

### Tests for User Story 2

- [X] T029 [P] [US2] Add failing persistence tests for liveness challenge risk JSON in `tests/test_storage_schema.py`
- [X] T030 [P] [US2] Add failing persistence tests for face login audit risk JSON in `tests/test_storage_schema.py`
- [X] T031 [P] [US2] Add failing tests for `/audit/login/recent` returning `anti_spoof_risk` in `tests/test_main_api.py`
- [X] T032 [P] [US2] Add failing business demo audit display tests in `tests/test_business_demo.py`

### Implementation for User Story 2

- [X] T033 [US2] Persist liveness challenge anti-spoof risk result in `storage.py`
- [X] T034 [US2] Persist face login audit anti-spoof risk result in `storage.py`
- [X] T035 [US2] Include `anti_spoof_risk` in `/audit/login/recent` records in `main.py`
- [X] T036 [US2] Ensure high-risk failure reason is distinguishable from normal no-match failures in `main.py`
- [X] T037 [US2] Display recent audit risk level and concise reason in `camera-integration.html`
- [X] T038 [US2] Display business demo audit risk level and reason in `business_demo/static/terminal.html`
- [X] T039 [US2] Document operator interpretation of risk levels and reason codes in `docs/04_usage/03_recognition_security_accuracy.md`

**Checkpoint**: US2 独立完成后，运维人员能通过 audit 判断失败类别，并获得摄像头、光线、距离等排障方向。

---

## Phase 5: User Story 3 - 安全负责人获得轻量防翻拍验收报告 (Priority: P2)

**Goal**: 提供 V2.1 现场验收记录和能力边界说明，避免把轻量增强误解为企业级强活体。

**Independent Test**: 查看验收记录和文档，确认五类样例、误拒记录、残余风险和升级建议都能落地。

### Tests for User Story 3

- [X] T040 [P] [US3] Add failing smoke test for V2.1 acceptance record presence in `tests/test_scripts_smoke.py`
- [X] T041 [P] [US3] Add failing documentation contract test for V2.1 API fields in `tests/test_scripts_smoke.py`

### Implementation for User Story 3

- [X] T042 [US3] Create V2.1 acceptance record template with five sample types in `docs/90_archive/04_acceptance/05_v2.1_acceptance_record.md`
- [X] T043 [US3] Update frontend/API integration notes for `anti_spoof_risk` in `docs/04_usage/01_api_integration.md`
- [X] T044 [US3] Update business integration guidance for Java production replacement boundaries in `docs/04_usage/04_business_integration_v2.md`
- [X] T045 [US3] Update visual architecture and flow notes for V2.1 anti-spoof risk in `architecture.html`
- [X] T046 [US3] Update V2.1 completion notes and implementation entry in `specs/README.md`

**Checkpoint**: US3 独立完成后，V2.1 的轻量能力、不可覆盖风险和现场验收方式都有文档依据。

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: 收尾验证、兼容性检查和提交前清理。

- [X] T047 Run focused tests for main API and storage from `specs/022-lightweight-anti-spoofing/quickstart.md`
- [X] T048 Run focused tests for scripts and business demo from `specs/022-lightweight-anti-spoofing/quickstart.md`
- [X] T049 Run full unittest, compileall, and `git diff --check`; record result in `docs/90_archive/04_acceptance/05_v2.1_acceptance_record.md`
- [X] T050 Scan local HTML external dependencies and record result in `docs/90_archive/04_acceptance/05_v2.1_acceptance_record.md`
- [X] T051 Review `Coding Review/code-review-v2.0-2026-06-16.md` and confirm no stale V2.0 review item is mixed into V2.1 implementation
- [X] T052 Prepare local commit command notes for the user in `docs/90_archive/04_acceptance/05_v2.1_acceptance_record.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖，可以立即执行。
- **Foundational (Phase 2)**: 依赖 Phase 1，阻塞所有用户故事。
- **US1 (Phase 3)**: 依赖 Phase 2，是 MVP。
- **US2 (Phase 4)**: 依赖 Phase 2，可与 US1 部分并行，但最终需要读取 US1 的风险语义。
- **US3 (Phase 5)**: 依赖 Phase 2，可先起草文档模板，最终需要同步 US1/US2 的实际字段。
- **Polish**: 依赖目标用户故事完成。

### User Story Dependencies

- **US1 (P1)**: 登录风险闭环，MVP，必须优先完成。
- **US2 (P1)**: audit 复核能力，可在 US1 风险结构稳定后并行推进。
- **US3 (P2)**: 验收和边界文档，可与 US1/US2 并行起草，最终统一校验。

### Within Each User Story

- 先写测试并确认失败。
- 再做最小实现。
- 再跑聚焦测试。
- 最后更新文档和验收记录。

---

## Parallel Examples

### Setup / Foundational

```text
Task: "T002 Review V2.1 scope and assumptions in specs/ROADMAP-v2.1.md"
Task: "T003 Review API compatibility contract in specs/022-lightweight-anti-spoofing/contracts/api-contract.md"
Task: "T004 Review manual acceptance sample matrix in specs/022-lightweight-anti-spoofing/quickstart.md"
```

### User Story 1

```text
Task: "T014 Add failing tests for low/medium/high risk scoring outcomes in tests/test_main_api.py"
Task: "T015 Add failing tests for /liveness/challenges/submit returning anti_spoof_risk in tests/test_main_api.py"
Task: "T016 Add failing tests for /auth/face-login blocking high-risk attempts with ANTI_SPOOF_HIGH_RISK in tests/test_main_api.py"
Task: "T017 Add failing tests that low-risk face login remains backward compatible in tests/test_main_api.py"
```

### User Story 2

```text
Task: "T029 Add failing persistence tests for liveness challenge risk JSON in tests/test_storage_schema.py"
Task: "T030 Add failing persistence tests for face login audit risk JSON in tests/test_storage_schema.py"
Task: "T031 Add failing tests for /audit/login/recent returning anti_spoof_risk in tests/test_main_api.py"
Task: "T032 Add failing business demo audit display tests in tests/test_business_demo.py"
```

### User Story 3

```text
Task: "T040 Add failing smoke test for V2.1 acceptance record presence in tests/test_scripts_smoke.py"
Task: "T041 Add failing documentation contract test for V2.1 API fields in tests/test_scripts_smoke.py"
Task: "T042 Create V2.1 acceptance record template with five sample types in docs/90_archive/04_acceptance/05_v2.1_acceptance_record.md"
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 only.
3. Validate真人低风险登录、静态翻拍高风险拒绝、中风险不默认阻断。
4. Stop and review before expanding audit and documentation scope.

### Incremental Delivery

1. US1: 登录风险评分和阻断闭环。
2. US2: audit 可复核和现场排障。
3. US3: 验收报告、文档边界和架构图同步。

### Parallel Team Strategy

1. One agent handles API/schema/config tasks in `main.py`, `api_schemas.py`, `app_config.py`, `api_errors.py`.
2. One agent handles persistence and audit tasks in `storage.py`, `tests/test_storage_schema.py`, `tests/test_main_api.py`.
3. One agent handles pages/docs tasks in `camera-integration.html`, `business_demo/`, `docs/`, `architecture.html`.
4. Final agent runs full validation and checks cross-file consistency.

## Format Validation

- All executable task lines use `- [ ] T###` format.
- Parallel tasks use `[P]` only when they do not depend on unfinished same-file edits.
- User story tasks include `[US1]`, `[US2]`, or `[US3]`.
- Each executable task references at least one concrete file path.
