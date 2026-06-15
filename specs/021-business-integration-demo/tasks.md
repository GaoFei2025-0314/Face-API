# 任务：业务接入 Demo 套件

## Phase 1: Setup

- [ ] T001 阅读 `specs/ROADMAP-v2.0.md`、`specs/021-business-integration-demo/spec.md`、`specs/021-business-integration-demo/plan.md` 和 `docs/04_usage/04_business_integration_v2.md`。
- [ ] T002 确认工作区干净：在 `H:\AI_test\face_api` 执行 `git status --short`，结果应为空。
- [ ] T003 运行基线测试：执行 `D:\anaconda3\envs\face_api\python.exe -m unittest discover -s tests -v`，结果应全部通过。
- [ ] T004 创建 `business_demo/`、`business_demo/static/` 和必要的 README 骨架。

## Phase 2: Foundational

- [ ] T005 [P] 新增 `business_demo/schemas.py`，定义业务用户、绑定、登录、audit 和错误响应模型。
- [ ] T006 [P] 新增 `business_demo/storage.py`，实现业务 SQLite 初始化、示例用户初始化、用户 CRUD、绑定和业务 audit。
- [ ] T007 [P] 新增 `business_demo/face_api_client.py`，封装服务端调用 `face_api` 的 API Key、错误转换和超时处理。
- [ ] T008 新增 `business_demo/app.py`，创建 FastAPI 应用、静态页面入口、配置读取和统一错误处理。
- [ ] T009 [P] 新增 `scripts/run-business-demo.bat`，启动 `business-demo` 到端口 `8010`。
- [ ] T010 [P] 新增 `tests/test_business_demo.py`，覆盖业务存储、绑定约束和错误映射的基础测试。

## Phase 3: User Story 1 - Web 业务后端代理人脸登录 (P1)

**独立测试标准**：浏览器只访问 `business-demo`，完成活体和 face login 后拿到 demo JWT，浏览器不暴露 `face_api` 的 `X-API-Key`。

- [ ] T011 [US1] 在 `business_demo/app.py` 实现 `POST /api/auth/liveness/challenge` 和 `POST /api/auth/liveness/submit`。
- [ ] T012 [US1] 在 `business_demo/app.py` 实现 `POST /api/auth/face-login`，服务端调用 `face_api /auth/face-login`。
- [ ] T013 [US1] 在 `business_demo/app.py` 实现最小 demo JWT 签发和 `GET /api/auth/me`。
- [ ] T014 [US1] 在 `business_demo/storage.py` 写入业务登录 audit，覆盖成功和失败。
- [ ] T015 [P] [US1] 在 `tests/test_business_demo.py` 增加 Web 登录成功、用户禁用、未绑定和 `face_api` 错误映射测试。

## Phase 4: User Story 2 - 业务用户绑定、解绑和换脸 (P1)

**独立测试标准**：页面能新增用户、绑定人脸、解绑、换脸；一个业务用户同一时间只有一个有效绑定。

- [ ] T016 [US2] 在 `business_demo/app.py` 实现 `GET /api/users` 和 `POST /api/users`。
- [ ] T017 [US2] 在 `business_demo/app.py` 实现 `POST /api/users/{user_id}/face-binding`，服务端调用 `face_api /faces/register`。
- [ ] T018 [US2] 在 `business_demo/app.py` 实现 `DELETE /api/users/{user_id}/face-binding`，服务端调用 `face_api DELETE /faces/{face_id}`。
- [ ] T019 [US2] 在 `business_demo/app.py` 实现 `POST /api/users/{user_id}/face-binding/replace`。
- [ ] T020 [P] [US2] 在 `tests/test_business_demo.py` 增加重复绑定、解绑后登录失败、换脸后仅保留一个有效绑定测试。
- [ ] T021 [US2] 在 `business_demo/static/index.html` 实现用户列表、新增用户、绑定、解绑和换脸操作区。

## Phase 5: User Story 3 - 受控终端识别和业务上报 (P2)

**独立测试标准**：终端 demo 直接调用 `face_api`，再把识别结果上报给 `business-demo`，业务 audit 能看到 terminal 来源记录。

- [ ] T022 [US3] 在 `business_demo/app.py` 实现 `POST /api/terminal/login-events`。
- [ ] T023 [US3] 新增 `scripts/terminal-demo.py`，支持读取图片或摄像头采集、调用 `face_api`、上报 `business-demo`。
- [ ] T024 [P] [US3] 在 `tests/test_scripts_smoke.py` 增加 `terminal-demo.py --help` 和参数解析 smoke test。
- [ ] T025 [P] [US3] 在 `tests/test_business_demo.py` 增加终端事件上报成功、用户不存在、用户禁用和重复事件处理测试。

## Phase 6: User Story 4 - Java / Spring Boot 接入说明 (P2)

**独立测试标准**：Java 开发者能按文档理解 Controller、Service、`face_api` client、绑定表、audit 和登录态替换点。

- [ ] T026 [US4] 更新 `docs/04_usage/05_spring_boot_integration_notes.md`，补充 Controller、Service 和 `face_api` client 伪代码。
- [ ] T027 [US4] 更新 `docs/04_usage/04_business_integration_v2.md`，补充 Web 链路、终端链路、错误码和上线检查清单。
- [ ] T028 [US4] 更新 `README.md` 和 `docs/01_document_index.md`，加入 `business-demo` 入口。

## Final Phase: Closure

- [ ] T029 更新 `architecture.html`，加入 V2.0 `business-demo`、Web 代理链路和终端链路。
- [ ] T030 运行全量测试：`D:\anaconda3\envs\face_api\python.exe -m unittest discover -s tests -v`。
- [ ] T031 运行 `git diff --check`。
- [ ] T032 扫描本地 HTML 外部依赖，确认 `business_demo/static/index.html` 未引入外部 CDN、`import` 或 `require`。
- [ ] T033 完成 V2.0 验收记录并提交，建议 commit message：`feat: add business integration demo suite`。

## 依赖和执行顺序

- Phase 1 和 Phase 2 是基础工作，必须先完成。
- US1 和 US2 都依赖 `business_demo/app.py`、`storage.py` 和 `face_api_client.py`。
- US3 可在 US1/US2 基础上并行推进。
- US4 文档可和 US1-US3 并行推进，但最终必须和实际实现一致。

## 推荐 MVP

先完成 Phase 1、Phase 2、US2 的用户绑定，再完成 US1 的 Web 登录。这样最早能演示“业务用户 -> 绑定人脸 -> 活体登录 -> demo JWT”。
