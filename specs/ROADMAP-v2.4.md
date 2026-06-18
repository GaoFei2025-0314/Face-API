# face_api Roadmap v2.4

> 创建时间：2026-06-18
> 用途：定义 V2.4 Face API 与 Electron WMS 智能抓拍联动验收基线的范围、边界和执行入口
> 状态：已规划，待实施

## 1. 版本定位

V2.3 已经完成 `face_api` 自身的固定摄像头现场验收：真人正脸主链路可用，翻拍样例不会再低风险静默成功，中风险默认由后端强制重试一次。

V2.4 的目标不是继续单独堆算法规则，而是把 `face_api` 放进真实 WMS 终端链路里验收：

```text
WMS 摄像头采集
-> Face API 检测 / 活体 / face login
-> WMS 终端提示或登录
-> Face API audit 与 WMS 日志回收
-> 问题归因
-> 下一轮改进决策
```

本版本定位为：

> Face API + WMS 现场联动验收基线。

## 2. 子版本范围

| 子版本 | Spec | 主题 | 目标 |
|---|---|---|---|
| V2.4.1 | `specs/025-wms-capture-loop-baseline` | 联动验收规格 | 把已确认的 WMS 抓拍闭环设计转成可执行 spec-kit 文档 |
| V2.4.2 | `specs/025-wms-capture-loop-baseline` | Face API 验收模板 | 新增 Face API 侧联动验收记录模板，覆盖环境快照、样例矩阵、audit 和问题分类 |
| V2.4.3 | `specs/025-wms-capture-loop-baseline` | WMS 终端 runbook | 在 WMS 仓库新增终端侧操作、日志回收和归因说明 |
| V2.4.4 | `specs/025-wms-capture-loop-baseline` | 文档索引和季度计划 | 同步 `specs/README.md`、季度计划、文档入口和 agent 当前计划指针 |

## 3. 已确认决策

- V2.4 先做联动验收基线，不默认修改 `face_api` 后端接口。
- V2.4 先做文档、模板、runbook 和检查流程，不默认改 WMS 登录业务逻辑。
- WMS 仓库路径按 `H:\AI_test\electron-wms\electron-wms` 处理；如果实施时路径不存在，先停止并记录阻塞，不猜路径。
- Face API 侧保存联动验收模板，WMS 侧保存终端 runbook。
- 单次问题必须归为三类之一：算法底座、终端采集、业务流程。
- 验收样例至少覆盖真人正脸、真人弱光、真人侧脸或轻微遮挡、打印照片、手机屏幕照片、电脑屏幕照片、手机播放眨眼视频、多人入镜和模糊抓拍。
- 验收记录只写结果、配置、错误码、相似度、风险等级、耗时、audit 是否可查和日志证据，不保存原图、视频帧、embedding 或 API Key。
- 手持移动摄像头制造运动视差继续作为 V2.3 残余风险记录；V2.4 不把它临时升级成重型活体实现。

## 4. 明确不做

- 不新增 `face_api` 公开 API。
- 不新增环境变量。
- 不新增数据库表。
- 不改变 `X-API-Key` 鉴权规则。
- 不修改 WMS 正式登录、token、用户同步或离线回退逻辑。
- 不引入重型 anti-spoofing 模型或 PyTorch。
- 不把一次联动验收结果当作最终算法结论。
- 不在文档中保存现场原图、连续帧、视频或用户敏感信息。

## 5. 推荐执行入口

```text
/goal Implement face_api Roadmap V2.4 - WMS Capture Loop Baseline
```

实施前先阅读：

```text
docs/superpowers/specs/2026-06-17-face-api-wms-capture-loop-design.md
docs/superpowers/plans/2026-06-17-face-api-wms-capture-loop-baseline.md
specs/025-wms-capture-loop-baseline/spec.md
specs/025-wms-capture-loop-baseline/plan.md
specs/025-wms-capture-loop-baseline/tasks.md
```

## 6. 验收总则

- [ ] Face API 侧联动验收模板已创建，并能指导一次完整联动验收。
- [ ] WMS 侧终端 runbook 已创建，并能指导摄像头、登录、日志和证据回收。
- [ ] 文档入口、季度计划和 specs 索引能指向 V2.4。
- [ ] 实施任务明确区分 Face API 仓库和 WMS 仓库，不混用提交范围。
- [ ] 验收模板明确不保存原图、视频帧、embedding 或 API Key。
- [ ] 验收模板明确问题归因必须落到算法底座、终端采集或业务流程。
- [ ] `git diff --check` 通过。
- [ ] 若修改 WMS 仓库，WMS 工作区变更必须单独检查和提交。
