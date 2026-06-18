# face_api 2026 Q2 季度计划与进度看板

> 当前日期：2026-06-17
> 季度范围：2026-04-01 至 2026-06-30  
> 当前版本基线：V2.3 轻量防翻拍阈值治理与中风险重试机制已完成，固定摄像头现场五类样例验收通过。

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
| V1.9 | 现场验收收口与 P1/P2 小修 | 已完成 | `docs/90_archive/04_acceptance/03_v1.9_acceptance_record.md`、`specs/020-field-acceptance-closure/tasks.md` |
| V2.0 | 业务系统正式接入示范版 | 已完成 | `docs/90_archive/04_acceptance/04_v2.0_acceptance_record.md`、`specs/021-business-integration-demo/tasks.md` |
| V2.1 | 轻量防翻拍活体增强 | 已完成 | `docs/90_archive/04_acceptance/05_v2.1_acceptance_record.md`、`specs/022-lightweight-anti-spoofing/tasks.md` |
| V2.2 | 现场算法验收与阈值调优台 | 现场验收完成，主链路通过，防翻拍未达上线标准 | `docs/90_archive/04_acceptance/06_v2.2_acceptance_record.md`、`specs/023-field-algorithm-acceptance-console/tasks.md` |
| V2.3 | 轻量防翻拍阈值治理与中风险重试机制 | 已完成 | `docs/90_archive/04_acceptance/07_v2.3_acceptance_record.md`、`specs/024-lightweight-anti-spoof-governance/tasks.md` |

当前 V1.3-V1.6 已统一提交：

```text
a1bdf64 feat: complete roadmap v1.3-v1.6
```

## 3. 本季度剩余重点

V2.0 已完成业务系统正式接入示范版。当前重点从“继续规划 V2.0”转为“按验收记录维护 business-demo、终端 demo 和 Java 接入文档的一致性”。

### P0：V2.0 规划验收

- [x] 确认 `specs/ROADMAP-v2.0.md` 的版本定位、边界和执行入口。
- [x] 确认 `specs/021-business-integration-demo/spec.md` 覆盖 Web 业务链路和受控终端链路。
- [x] 确认 `specs/021-business-integration-demo/tasks.md` 能直接作为后续 `/goal` 的任务入口。
- [x] 确认 `docs/04_usage/04_business_integration_v2.md` 能给业务后端和终端开发者解释清楚接入边界。
- [x] 确认 `docs/04_usage/05_spring_boot_integration_notes.md` 能让 Java / Spring Boot 团队理解替换方式。

### P0：Web 业务接入 Demo

- [x] 新增独立 `business-demo`，运行在 `http://localhost:8010`。
- [x] 页面能列出示例业务用户并新增用户。
- [x] 业务后端代理调用 `face_api`，浏览器不直接持有 `X-API-Key`。
- [x] 支持绑定、解绑、换脸、活体登录和 demo JWT。
- [x] 业务登录成功和失败都写入业务 audit。

### P1：受控终端接入 Demo

- [x] 提供 `http://localhost:8010/terminal.html` 和 `scripts/terminal-demo.py`。
- [x] 终端可直接调用 `face_api` 完成活体和 face login。
- [x] 终端用稳定 `terminal_id` 上报业务登录事件。
- [x] 业务后端能拒绝不存在、禁用或未绑定用户。

### P1：真实 Java 接入说明

- [x] 提供 Controller、Service、`FaceApiClient`、绑定表和业务 audit 的伪代码。
- [x] 说明 demo JWT 如何替换成真实 session/JWT/SSO。
- [x] 明确 `face_api` 错误和业务错误的分层处理方式。

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

## 8. V2.0 完成状态

V2.0 已作为业务接入版本完成。它不改变 `face_api` 公开接口，而是在 `face_api` 外围新增独立 `business-demo`，让真实业务系统能照着接入。

V2.0 执行入口：

```text
/goal Implement face_api Roadmap V2.0 - Business Integration Demo Suite
```

V2.0 规格和验收入口见：

```text
specs/ROADMAP-v2.0.md
specs/021-business-integration-demo/spec.md
specs/021-business-integration-demo/plan.md
specs/021-business-integration-demo/tasks.md
docs/90_archive/04_acceptance/04_v2.0_acceptance_record.md
```

V2.0 准入和边界：

- `face_api` 只做人脸识别服务。
- 业务用户、登录态、权限和业务 audit 放在 `business-demo` 或真实业务系统。
- 同时规划 Web 业务链路和受控终端链路。
- Demo 用 FastAPI + SQLite，真实环境按 Java / Spring Boot 文档替换。
- 不新增 `face_api` 公开接口。
- 不引入完整业务平台、SSO、复杂权限系统或前端框架。

## 9. V2.1 与 V2.2 当前状态

V2.1 已完成轻量防翻拍活体增强，核心结果是 `anti_spoof_risk`、中文失败原因、audit 记录和 business-demo 风险透传能力。

## 10. V2.2 现场验收结果与 V2.3 下一步计划

V2.2 主题为“现场算法验收与阈值调优台”。目标是在不新增后端存储和公开接口的前提下，用 `acceptance.html` 完成五类样例现场验收、报告下载和保守调参建议。

V2.2 基线入口：

```text
specs/ROADMAP-v2.2.md
specs/023-field-algorithm-acceptance-console/spec.md
specs/023-field-algorithm-acceptance-console/plan.md
specs/023-field-algorithm-acceptance-console/tasks.md
docs/90_archive/04_acceptance/06_v2.2_acceptance_record.md
```

V2.2 关键边界：

- 测试用户 `user_id` 使用数字或留空。
- 活体失败时记录失败，不继续 face login。
- 注册/重绑兼容注册活体开关。
- 通过 `FACE_CORS_ORIGINS` 支持 `http://localhost:8122` 现场浏览器验收。
- 不保存原图、连续帧、embedding 或 API Key。

V2.2 现场验收结论：

- 真人正脸 3/3 成功，说明主链路可用。
- 打印照片、手机屏幕照片、电脑屏幕照片和手机播放眨眼视频仍出现低风险成功。
- 后续进入 V2.3，重点治理轻量防翻拍风险评分和中风险重试策略。

V2.3 基线入口：

```text
specs/ROADMAP-v2.3.md
specs/024-lightweight-anti-spoof-governance/spec.md
specs/024-lightweight-anti-spoof-governance/plan.md
specs/024-lightweight-anti-spoof-governance/tasks.md
docs/90_archive/04_acceptance/07_v2.3_acceptance_record.md
```

V2.3 关键边界：

- 真人正脸至少 2/3 通过。
- 翻拍样例不能再低风险静默成功。
- 不新增复杂动作，不引入重型 anti-spoofing 模型。
- 中风险默认由后端强制重试，最多重试 1 次。
- 中风险策略可配置，但默认验收使用强制重试。
- 中风险重试由后端签发的 `risk_retry_token` 强制，第二次 login 必须回传有效 token 和新的 `challenge_id`，不能依赖前端 `state` 或业务端自报次数。
- 第一次中风险错误响应固定包含 `detail.retry.risk_retry_token`、`detail.retry.expires_at`、`detail.retry.remaining_attempts`；audit 和报告不得导出原始 token。
- 固定摄像头现场验收已通过；手持或移动摄像头制造运动视差属于残余风险，需要后续更强活体能力或设备固定约束。

## 11. 每周检查节奏

每周只看 5 件事：

1. 服务能否启动和停止。
2. `/health`、`/config/effective`、`/system/status` 是否正常。
3. login/register 真实摄像头流程是否成功。
4. 最近 audit 里失败原因是否可解释。
5. 是否出现文档和实际行为不一致。

如果这 5 件事都稳定，再考虑新功能。
