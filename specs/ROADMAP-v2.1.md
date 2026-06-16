# face_api Roadmap v2.1

> 创建时间：2026-06-16
> 用途：定义 V2.1 轻量防翻拍活体增强的范围、边界和执行入口
> 状态：规划中

## 1. 版本定位

V2.1 的目标是在不明显增加用户操作负担的前提下，增强当前基础活体对照片翻拍、屏幕翻拍和静态重放的风险识别能力。

本版本定位为：

> 轻量防翻拍活体增强。

V2.1 不把 `face_api` 升级为完整风控平台，也不承诺企业级 anti-spoofing。它的重点是把当前“能完成活体 challenge”的能力推进到“能给出更清楚的翻拍风险判断、审计和现场验收报告”。

## 2. 子版本范围

| 子版本 | Spec | 主题 | 目标 |
|---|---|---|---|
| V2.1.1 | `specs/022-lightweight-anti-spoofing` | 轻量风险分级 | 给活体结果增加低/中/高风险语义，不打扰低风险用户 |
| V2.1.2 | `specs/022-lightweight-anti-spoofing` | 翻拍样例矩阵 | 整理真人、打印照片、手机屏幕、电脑屏幕和播放视频样例 |
| V2.1.3 | `specs/022-lightweight-anti-spoofing` | 用户体验保护 | 只在高风险或连续失败时要求重试，不默认增加复杂动作 |
| V2.1.4 | `specs/022-lightweight-anti-spoofing` | 验收报告 | 输出当前能防什么、不能防什么和后续升级建议 |

## 3. 已确认决策

- 选择轻量风险评分路线，不做重交互活体。
- 保留现有 login 默认活体流程。
- 注册活体继续保持可配置，不强制默认开启。
- 优先降低照片、屏幕翻拍和静态重放风险。
- 不默认要求用户完成多个动作。
- 不引入新硬件。
- 不引入重型 anti-spoofing 模型。
- 不改变 `face_api` 的业务边界：它只返回识别、活体、风险和失败原因，最终业务决策仍由业务系统处理。
- 所有失败原因必须对用户保留简短中文提示，对运维保留可复核原因。

## 4. 明确不做

- 不接入红外、深度摄像头或专用硬件。
- 不引入企业级活体模型作为强依赖。
- 不新增复杂多动作强制流程。
- 不把低风险用户每次都拦截重试。
- 不把 `face_api` 改成完整风控系统。
- 不承诺防住高清屏幕视频、深度伪造、虚拟摄像头流或专业攻击。
- 不为了安全加固牺牲现场登录主流程的可用性。

## 5. 推荐执行入口

本版本后续实现建议使用：

```text
/goal Implement face_api Roadmap V2.1 - Lightweight Anti-Spoofing
```

实施前先阅读：

```text
specs/022-lightweight-anti-spoofing/spec.md
docs/04_usage/03_recognition_security_accuracy.md
docs/04_usage/04_business_integration_v2.md
docs/90_archive/04_acceptance/03_v1.9_acceptance_record.md
docs/90_archive/04_acceptance/04_v2.0_acceptance_record.md
```

## 6. 验收总则

V2.1 完成时必须满足：

- [ ] 真实用户正常完成 face login 时不需要额外复杂动作。
- [ ] 明显静态照片或静态屏幕样例能被标记为更高风险。
- [ ] 高风险样例不会被静默当作普通活体成功。
- [ ] 活体失败或高风险时返回简短中文原因。
- [ ] audit 能记录活体风险等级、主要原因和 terminal 信息。
- [ ] 现场验收报告能列出真人、打印照片、手机屏幕、电脑屏幕、播放视频样例的结果。
- [ ] 文档明确说明 V2.1 是轻量防翻拍增强，不是企业级强活体。
- [ ] 不破坏 V2.0 business-demo 和终端 demo 的现有登录链路。
