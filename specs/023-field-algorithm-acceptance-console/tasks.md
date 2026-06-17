# Tasks: 现场算法验收与阈值调优台

**Input**: `spec.md`, `plan.md`, `docs/superpowers/specs/2026-06-16-v2.2-field-algorithm-acceptance-console-design.md`

**Tests**: 按 TDD 执行；先写 `tests/test_scripts_smoke.py` 静态测试，再实现页面和文档。

## Phase 1: Setup

- [x] T001 确认 V2.1 follow-up 修复和 V2.2 设计文档已独立提交或明确不纳入本版本提交
- [x] T002 确认/补齐 V2.2 roadmap/spec/plan/tasks/acceptance record
- [x] T003 更新 `specs/README.md` 和季度计划中的 V2.2 入口

## Phase 2: Page Contract Tests

- [x] T004 为 `acceptance.html` 增加本地依赖、安全字段、五类样例、报告导出静态测试
- [x] T005 确认 T004 在页面不存在时失败

## Phase 3: Acceptance Console

- [x] T006 新建 `acceptance.html` 页面骨架和样式
- [x] T007 实现摄像头预览和本地截图/连续帧采集
- [x] T008 实现 API client、运行状态读取和完整登录链路；活体失败时记录失败，不继续 face login
- [x] T009 实现测试用户注册/重绑，兼容注册活体开关和整数或留空 `user_id`
- [x] T010 实现结果汇总、JSON/CSV 导出和建议规则

## Phase 4: Docs And Architecture

- [x] T011 更新 `architecture.html`
- [x] T012 更新 README 和识别安全文档，说明通过 `FACE_CORS_ORIGINS` 支持 `http://localhost:8122` 现场浏览器验收
- [x] T013 完成 V2.2 验收记录

## Phase 5: Verification

- [x] T014 运行静态测试、全量 unittest、compileall、git diff --check
- [x] T015 打开 `acceptance.html` 做浏览器加载；现场摄像头五类样例保留在验收记录中人工执行
