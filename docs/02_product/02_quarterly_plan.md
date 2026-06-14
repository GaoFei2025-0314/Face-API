# face_api 2026 Q2 季度计划与进度看板

> 当前日期：2026-06-14
> 季度范围：2026-04-01 至 2026-06-30  
> 当前版本基线：V1.9 现场验收收口与 P1/P2 小修（规划中）

## 1. 本季度目标

本季度目标不是继续堆功能，而是把 face_api 从“能跑的识别 API”推进到：

> Windows 工作站上可运行、可监控、可接入业务系统、可解释失败原因、可做性能验证的本地人脸识别服务底座。

## 2. 当前季度交付状态

| 版本 | 主题 | 状态 | 验收依据 |
|---|---|---|---|
| V1.1 | 现场安全可用版 | 已完成 | `1bef86c feat: complete roadmap v1.1` |
| V1.2 | PRD/specs 规划版 | 已完成 | `4856ae5 docs: add roadmap v1.2 specs` |
| V1.3 | 生产运行与监控 | 已完成 | `specs/014-production-runtime-monitoring/tasks.md` |
| V1.4 | 识别安全与准确率增强 | 已完成 | `specs/015-recognition-security-accuracy/tasks.md` |
| V1.5 | 前端与业务接入体验 | 已完成 | `specs/016-frontend-business-integration/tasks.md` |
| V1.6 | 性能与规模化能力 | 已完成 | `specs/017-performance-scale/tasks.md` |
| V1.7.1 | 摄像头注册登录闭环验收 | 已完成 | `specs/018-camera-acceptance-loop/tasks.md` |
| V1.7.2 | Windows 长期运行加固 | 已完成 | `specs/019-windows-long-running/tasks.md` |
| V1.8.1 | 文档与版本基线收口 | 已完成 | `1f5e376 docs: align v1.8 delivery maintenance baseline` |
| V1.8.2 | `main.py` 可维护性拆分 | 已完成 | `06e8555`、`a9625fd`、`0473080`、`1558959` |
| V1.8.3 | 现场验收台与运行状态总览 | 已完成 | `5968483 feat: improve local field acceptance status` |
| V1.8.4 | 交互式架构图演示增强 | 已完成 | `fc40854 docs: enhance architecture demo mode` |
| V1.9 | 现场验收收口与 P1/P2 小修 | 规划中 | `specs/ROADMAP-v1.9.md`、`specs/020-field-acceptance-closure/tasks.md` |

当前 V1.3-V1.6 已统一提交：

```text
a1bdf64 feat: complete roadmap v1.3-v1.6
```

## 3. 本季度剩余重点

剩余时间建议不再新增大功能，优先做现场验证和收口。

### P0：现场运行验收

- 在目标 Windows 工作站启动 `run.bat`。
- 验证 `GET /health`。
- 验证 Swagger：`http://localhost:8000/docs`。
- 验证 `scripts/monitor-service.ps1`。
- 验证 `scripts/stop-service.ps1`。
- 验证日志轮转配置能在 `/config/effective` 看到。

### P0：摄像头链路验收

- 打开 `camera-integration.html`。
- 完成摄像头授权。
- 完成 login challenge。
- 完成 `/auth/face-login`。
- 验证错误码能显示中文提示。
- 确认正式业务前端不直接持有 `X-API-Key`。

### P1：识别策略验收

- 用真实摄像头采集明亮、过暗、过曝、模糊、距离过远样本。
- 观察 `FACE_DET_SCORE_LOW`、`FACE_TOO_SMALL`、`FACE_TOO_DARK`、`FACE_TOO_BRIGHT`、`FACE_BLURRY` 是否符合预期。
- 查看 `/audit/login/recent`。
- 查看 `/policy/tuning-summary`。

### P1：性能验收

- 跑小规模 benchmark，确认脚本可用。
- 不要在真实库上使用 `--write-db`。
- 需要 5 万规模时，先用临时 benchmark 库验证。

## 4. 功能把控规则

以后任何新需求先回答 4 个问题：

1. 它是否属于 face_api 的职责？
2. 它服务哪类用户：前端、业务后端、终端、运维？
3. 它属于哪个版本线：运行、识别安全、前端接入、性能规模？
4. 它是否有可验证的验收标准？

如果回答不清楚，先不写代码。

## 5. 版本准入规则

新功能进入开发前，必须满足：

- 有对应 spec 或季度计划条目。
- 有明确“不做什么”。
- 有可执行测试或手工验收命令。
- 会影响接口、环境变量、启动方式、错误码时，同步更新文档。

## 6. 版本完成规则

一个版本完成必须同时满足：

- `tasks.md` 全部勾选。
- 相关 `spec.md` 状态为已完成。
- 单元测试通过。
- 脚本解析或 smoke test 通过。
- code review 问题已处理或记录为残余风险。
- 有 commit。

## 7. V1.8 完成状态

V1.8 已按“现场交付与维护闭环”完成，重点不是新增业务平台能力，而是让 face_api 更容易交付、排障、讲解和维护。

| 子版本 | 主题 | 状态 |
|---|---|---|
| V1.8.1 | 文档与版本基线收口 | 已完成 |
| V1.8.2 | `main.py` 可维护性拆分 | 已完成 |
| V1.8.3 | 现场验收台与运行状态总览 | 已完成 |
| V1.8.4 | 交互式架构图演示增强 | 已完成 |

V1.8 验收记录见 `docs/90_archive/04_acceptance/02_v1.8_acceptance_record.md`。

## 8. V1.9 下一版本计划

V1.9 建议作为本季度最后的收口版本，不继续扩大产品边界。它的目标是把 V1.8 已交付能力放到真实 Windows 工作站、真实摄像头链路和交付文档中验证清楚。

V1.9 执行入口：

```text
/goal Implement face_api Roadmap V1.9 - Field Acceptance Closure and P1/P2 Fixes
```

V1.9 验收记录见 `docs/90_archive/04_acceptance/03_v1.9_acceptance_record.md`。

V1.9 准入和边界：

- 先做现场验收，再做小修。
- 只修复验收中确认的 P1/P2 问题。
- 不新增公开 API、环境变量、鉴权机制或大功能。
- P3/P4 问题只记录，不临时扩范围。

## 9. 每周检查节奏

每周只看 5 件事：

1. 服务能否启动和停止。
2. `/health`、`/config/effective`、`/system/status` 是否正常。
3. login/register 真实摄像头流程是否成功。
4. 最近 audit 里失败原因是否可解释。
5. 是否出现文档和实际行为不一致。

如果这 5 件事都稳定，再考虑新功能。
