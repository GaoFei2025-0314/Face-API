# face_api Roadmap v1.9

> 创建时间：2026-06-14  
> 用途：定义 V1.9 现场验收收口与 P1/P2 小修的范围、执行入口和验收总则  
> 状态：规划中

## 1. 版本定位

V1.9 的目标不是继续新增大功能，而是把 V1.8 已完成的交付、维护、架构演示和运行能力，放到真实 Windows 工作站、真实摄像头链路和实际交付文档中做一次收口。

本版本定位为：

> 现场验收收口与 P1/P2 小修。

## 2. 子版本范围

| 子版本 | Spec | 主题 | 目标 |
|---|---|---|---|
| V1.9.1 | `specs/020-field-acceptance-closure` | 现场验收收口 | 验证启动、健康检查、摄像头注册登录、中文错误、audit、备份恢复和架构图一致性 |
| V1.9.2 | `specs/020-field-acceptance-closure` | P1/P2 小修闭环 | 只修复验收中确认的 P1/P2 问题，不新增大功能 |

## 3. 已确认决策

- V1.9 主线是现场验收收口。
- V1.9 允许修复验收中发现的 P1/P2 小问题。
- V1.9 不新增公开 API，不新增环境变量，不改变 `X-API-Key` 鉴权规则。
- P3/P4 问题只记录到验收记录或后续 backlog，不在 V1.9 临时扩大范围。
- `/admin/overview` 继续保持轻量控制台概览定位，不返回全量人脸列表。
- 后续实施继续使用 `/goal`，入口为本 Roadmap 和 `specs/020-field-acceptance-closure`。

## 4. 明确不做

- 不接完整业务后端。
- 不新增完整前端项目。
- 不新增向量数据库、Faiss 或 ANN index。
- 不新增更强 anti-spoofing 模型或硬件活体。
- 不新增用户系统、权限平台、token 或 session。
- 不做大规模重构；小修必须有明确验收问题或回归测试支撑。

## 5. 推荐执行顺序

```text
/goal Implement face_api Roadmap V1.9 - Field Acceptance Closure and P1/P2 Fixes
```

执行时先做验收，再做小修。没有验收证据的问题，不进入 P1/P2 小修范围。

## 6. 验收总则

V1.9 完成时必须满足：

- `run.bat` 或生产运行入口能在 Windows 工作站启动服务。
- `/health`、`/system/status`、`/config/effective` 可用于判断运行状态。
- `camera-integration.html` 能完成摄像头授权、注册、login challenge 和 face login。
- 中文错误原因能帮助现场人员定位常见失败。
- 最近 login audit 能解释登录成功和失败。
- 维护模式、备份、恢复流程有可执行验收记录。
- `architecture.html` 与实际入口、模块边界和运维流程一致。
- 全量单元测试通过，HTML 外部依赖扫描通过。

