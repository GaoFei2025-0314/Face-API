# face_api Roadmap v1.7

> 创建时间：2026-06-06  
> 用途：定义 V1.7 现场闭环与 Windows 长期运行版的范围、子版本和执行入口  
> 状态：V1.7.1 和 V1.7.2 已完成

## 1. 版本定位

V1.7 的目标不是继续扩大算法能力，而是把 V1.3-V1.6 已交付的能力放到真实 Windows 工作站和真实摄像头链路中跑顺。

本版本定位为：

> 现场闭环与 Windows 长期运行版。

## 2. 子版本范围

| 子版本 | Spec | 主题 | 目标 |
|---|---|---|---|
| V1.7.1 | `specs/018-camera-acceptance-loop` | 摄像头注册登录闭环验收 | 增强 `camera-integration.html`，跑通注册、登录、活体状态、中文错误原因和最近 audit 展示 |
| V1.7.2 | `specs/019-windows-long-running` | Windows 长期运行加固 | 提供 Task Scheduler 与 NSSM 两套长期运行方案、安装/卸载脚本和 runbook 说明 |

## 3. 已确认决策

- V1.7 先做 A、B 两个方向。
- V1.7.1 先不关心业务后端代理，优先跑通 face_api 自己的摄像头页面。
- V1.7.1 增强现有 `camera-integration.html`，不新增 `acceptance.html`。
- V1.7.1 页面需要显示最近 login audit。
- V1.7.2 同时规划 Task Scheduler 简单方案和 NSSM 正式服务方案。
- V1.7.2 提供两套方案的安装和卸载脚本。
- NSSM 脚本默认不静默下载 NSSM；如果机器没有 NSSM，应提示用户配置路径或先安装。

## 4. 明确不做

- 不接业务后端。
- 不新增完整前端项目。
- 不新增独立验收页面。
- 不做更强 anti-spoofing 模型。
- 不做硬件活体接入。
- 不做 Faiss / ANN index。
- 不做权限平台、用户系统、token 或 session。

## 5. 推荐执行顺序

```text
/goal Implement face_api Roadmap V1.7.1 - Camera Acceptance Loop
/goal Implement face_api Roadmap V1.7.2 - Windows Long Running
```

先做 V1.7.1，因为页面闭环能直接暴露注册、登录、活体、错误提示和 audit 的真实问题。

再做 V1.7.2，因为长期运行脚本需要基于已确认可用的启动、停止、监控流程。

## 6. 验收总则

V1.7 完成时必须满足：

- `camera-integration.html` 能完成注册 + 登录闭环。
- 页面能展示本次结果和最近 login audit。
- 中文错误原因对现场人员可理解。
- Task Scheduler 方案有安装、卸载、启动验证和停止说明。
- NSSM 方案有安装、卸载、启动验证和停止说明。
- 生产运行说明同步到 `docs/03_deployment/01_runbook.md`。
- 相关接口或页面行为变化同步到 `docs/04_usage/02_frontend_business_integration.md`。
