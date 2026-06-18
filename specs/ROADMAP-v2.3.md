# face_api Roadmap v2.3

> 创建时间：2026-06-17
> 用途：定义 V2.3 轻量防翻拍阈值治理与中风险重试机制的范围、边界和执行入口
> 状态：已完成，固定摄像头现场五类样例验收通过

## 1. 版本定位

V2.3 的目标是根据 V2.2 现场验收报告修正轻量防翻拍偏宽松的问题。

V2.2 已证明真人注册、活体和登录链路可用，但打印照片、手机屏幕照片、电脑屏幕照片和手机播放眨眼视频存在低风险成功。V2.3 不追求企业级强活体，也不引入重型模型，而是治理现有轻量风险评分和中风险处理策略。

本版本定位为：

> 轻量防翻拍阈值治理与中风险重试机制。

## 2. 子版本范围

| 子版本 | Spec | 主题 | 目标 |
|---|---|---|---|
| V2.3.1 | `specs/024-lightweight-anti-spoof-governance` | 风险评分治理 | 减少翻拍样例被判为 `normal_motion` 的低风险成功 |
| V2.3.2 | `specs/024-lightweight-anti-spoof-governance` | 中风险重试策略 | 默认后端拦截中风险并提示重试一次，策略可配置 |
| V2.3.3 | `specs/024-lightweight-anti-spoof-governance` | 页面和报告同步 | `camera-integration.html`、`acceptance.html` 展示中风险重试和复核语义 |
| V2.3.4 | `specs/024-lightweight-anti-spoof-governance` | 文档和验收 | 更新接入文档、季度计划、架构说明和 V2.3 验收记录 |

## 3. 已确认决策

- 验收目标采用平衡策略：真人正脸至少 2/3 通过。
- 翻拍样例不能再低风险静默成功。
- 不新增复杂动作。
- 不引入重型 anti-spoofing 模型。
- 不新增硬件依赖。
- 增强现有连续帧轻量评分逻辑。
- 中风险默认不直接通过，提示用户重试一次。
- 中风险策略可配置，默认由后端强制。
- 中风险最多重试 1 次；第二次仍中风险则失败或进入复核。
- 中风险重试次数必须由后端签发的 `risk_retry_token` 约束，不能依赖前端 `state` 或业务端自报次数。
- 第一次中风险默认返回 `detail.code=ANTI_SPOOF_MEDIUM_RETRY_REQUIRED`，并固定携带 `detail.retry.risk_retry_token`、`detail.retry.expires_at`、`detail.retry.remaining_attempts`。
- V2.3 只配置中风险处理策略和 retry token TTL；最大重试次数固定为 1，不新增最大重试次数环境变量。

## 4. 明确不做

- 不把 V2.3 扩展成企业级强活体。
- 不接入 PyTorch 或重型防伪模型。
- 不新增多动作 challenge 作为默认流程。
- 不保存原图、连续帧或 embedding 到报告。
- 不改变 `X-API-Key` 鉴权规则。
- 不让 similarity 阈值替代防翻拍判断。

## 5. 推荐执行入口

```text
/goal Implement face_api Roadmap V2.3 - Lightweight Anti-Spoof Governance
```

实施前先阅读：

```text
docs/superpowers/specs/2026-06-17-v2.3-lightweight-anti-spoof-governance-design.md
specs/024-lightweight-anti-spoof-governance/spec.md
specs/024-lightweight-anti-spoof-governance/plan.md
specs/024-lightweight-anti-spoof-governance/tasks.md
docs/90_archive/04_acceptance/07_v2.3_acceptance_record.md
```

## 6. 验收总则

- [X] 真人正脸 3 次测试至少 2 次成功。
- [X] 打印照片不得低风险静默成功。
- [X] 手机屏幕照片不得低风险静默成功。
- [X] 电脑屏幕照片不得低风险静默成功。
- [X] 手机播放眨眼视频不得低风险静默成功。
- [X] 中风险默认提示重试，不返回登录成功。
- [X] 中风险最多重试 1 次，第二次仍中风险则失败或复核。
- [X] 第二次重试必须携带后端签发的有效 `risk_retry_token`。
- [X] 第一次中风险错误响应包含稳定的 `detail.retry` 结构。
- [X] audit 和验收报告能看到风险等级、原因、处理动作和 terminal。
- [X] 文档说明中风险策略可配置，但默认验收使用后端强制重试。
