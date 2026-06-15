# face_api Roadmap v2.0

> 创建时间：2026-06-15
> 用途：定义 V2.0 业务系统正式接入示范版的范围、边界和执行入口
> 状态：已规划

## 1. 版本定位

V2.0 的目标是把 `face_api` 从“本地识别服务和现场验收工具”，推进到“业务系统可以照着接入的标准识别底座”。

本版本定位为：

> 业务系统正式接入示范版。

`face_api` 继续只做人脸识别、活体、人脸库和识别 audit。业务用户、登录态、权限和最终业务决策由业务系统负责。

## 2. 子版本范围

| 子版本 | Spec | 主题 | 目标 |
|---|---|---|---|
| V2.0.1 | `specs/021-business-integration-demo` | Mock 业务后端 | 新增独立 `business-demo`，模拟真实业务系统调用 `face_api` |
| V2.0.2 | `specs/021-business-integration-demo` | Web 业务接入 Demo | 浏览器只访问业务后端，由业务后端代理调用 `face_api` 并签发 demo JWT |
| V2.0.3 | `specs/021-business-integration-demo` | 受控终端 Demo | 终端页面和命令行脚本直接调用 `face_api`，再把识别结果上报给业务后端 |
| V2.0.4 | `specs/021-business-integration-demo` | Java 接入说明 | 提供 Java / Spring Boot 接口级伪代码和上线注意事项 |

## 3. 已确认决策

- `face_api` 只做人脸识别服务，不接管用户资料、登录态和权限。
- 同时规划两条正式接入链路：
  - Web 链路：业务前端 -> 业务后端 -> `face_api`。
  - 终端链路：受控终端 -> `face_api` -> 业务后端。
- Demo 业务后端使用 Python / FastAPI；真实生产环境按 Java / Spring Boot 接入说明替换。
- Demo 业务数据使用 SQLite。
- 业务用户必须先存在，再绑定人脸。
- 一个业务用户只允许绑定一张人脸。
- V2.0 支持解绑和换脸流程。
- 登录必须活体；绑定活体通过 `BUSINESS_DEMO_BINDING_LIVENESS_REQUIRED` 可配置，默认关闭。
- Demo 业务后端保存业务登录 audit。
- Demo 页面由 `business-demo` 服务提供，入口为 `http://localhost:8010`。
- 受控内网终端允许配置 `face_api` 的 `X-API-Key`。
- 终端 demo 同时提供页面和命令行脚本。
- V2.0 不新增 `face_api` 公开接口。

## 4. 明确不做

- 不把 `face_api` 改成用户系统。
- 不新增 `face_api` 公开 API。
- 不新增复杂权限、组织架构、SSO 或完整 RBAC。
- 不做完整 Spring Boot demo 项目。
- 不引入 React、Vue 或其他前端框架。
- 不新增向量数据库、Faiss、ANN index 或更强活体模型。
- 不把业务登录 audit 写进 `face_api`。

## 5. 推荐执行入口

后续实现建议使用：

```text
/goal Implement face_api Roadmap V2.0 - Business Integration Demo Suite
```

实施前先阅读：

```text
specs/021-business-integration-demo/spec.md
specs/021-business-integration-demo/plan.md
specs/021-business-integration-demo/tasks.md
docs/04_usage/04_business_integration_v2.md
docs/04_usage/05_spring_boot_integration_notes.md
```

## 6. 验收总则

V2.0 完成时必须满足：

- `face_api:8000` 和 `business-demo:8010` 能同时启动。
- 浏览器打开 `http://localhost:8010` 能完成业务用户列表、新增用户、绑定、登录、解绑和换脸。
- Web 登录链路不向浏览器暴露 `face_api` 的 `X-API-Key`。
- 已绑定且启用的业务用户能通过活体和人脸登录拿到 demo JWT。
- 未绑定、禁用、活体失败、识别失败等场景能显示中文原因。
- 终端 demo 能直接调用 `face_api` 并向 `business-demo` 上报业务登录事件。
- `business-demo` 能保存并查询业务登录 audit。
- 普通 Web 页面不包含 `face_api` 的 `X-API-Key` 或 `FACE_API_KEY`。
- Java / Spring Boot 接入说明能解释 Controller、Service、`face_api` 调用、绑定关系和业务 audit。
- 不改变现有 `face_api` 公开接口和鉴权规则。
