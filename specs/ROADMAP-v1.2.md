# face_api Roadmap v1.2+

> 创建时间：2026-06-05  
> 用途：在 Roadmap v1.1 完成后，统一定义后续 A/B/C/D 四条产品线的 PRD 和 spec-kit 入口  
> 状态：规划草案，供后续 `/goal` 按版本实施

## 1. 最终目标

`face_api` 的最终目标是成为一个可在 Windows 工作站长期稳定运行、可监控、可维护、可接入业务系统、具备安全人脸识别能力，并能逐步扩展到中等规模人脸库的本地人脸识别服务底座。

它仍然不是完整业务平台：

- 不管理业务用户主表。
- 不签发 token/session。
- 不做完整 RBAC。
- 不做多租户 SaaS。
- 不替代业务系统的权限判断。

## 2. 产品主线

后续版本按四条主线推进：

| 主线 | Spec | 目标 | 推荐实现版本 |
|---|---|---|---|
| A 生产运行与监控 | `specs/014-production-runtime-monitoring` | 让服务稳定启动、停止、监控、告警和恢复 | V1.3 |
| B 识别安全与准确率增强 | `specs/015-recognition-security-accuracy` | 提升活体、质量、阈值和误识别分析能力 | V1.4 |
| C 前端与业务接入体验 | `specs/016-frontend-business-integration` | 提供摄像头示例、流程页、SDK 和接入规范 | V1.5 |
| D 性能与规模化能力 | `specs/017-performance-scale` | 支撑 5 万人脸、批量数据和性能报告 | V1.6 |

## 3. 主线连接关系

```text
A 生产运行与监控
  ↓ 保证服务稳定跑起来、可观测、可恢复
B 识别安全与准确率增强
  ↓ 提供更可靠的人脸判断和风险控制
C 前端与业务接入体验
  ↓ 让业务系统和摄像头终端正确使用能力
D 性能与规模化能力
  ↓ 支撑更多人脸、更高数据量和更稳定响应
```

## 4. 推荐版本策略

### V1.2 - PRD/specs 规划版

只建立本 Roadmap 和 014-017 specs，不实现功能。

完成标准：

- A/B/C/D 都有独立 spec、plan、tasks。
- 每个 spec 都明确用户价值、范围、验收标准和边界。
- 后续可以用 `/goal` 单独实施某个版本。

### V1.3 - 生产运行与监控

优先原因：近期已经出现启动脚本、端口占用、API Key 和服务进程管理问题。先把运行基础打稳，后续功能才有可靠环境。

### V1.4 - 识别安全与准确率增强

优先原因：V1.1 已经有基础活体和策略摘要，下一步应把识别安全从“可用”推进到“可度量、可调优、可复核”。

### V1.5 - 前端与业务接入体验

优先原因：当后端能力稳定后，业务系统和摄像头终端需要更低成本接入，减少 Swagger 手工调试和重复踩坑。

### V1.6 - 性能与规模化能力

优先原因：规模优化应基于稳定运行、清晰识别策略和标准接入之后再做，避免提前引入复杂 index。

计划交付：

- 5 万人脸 benchmark 脚本和 JSON 报告格式。
- 批量导出清单与导入清单校验流程。
- `/search/index-status` 和 `/performance/scale-plan` 只读状态接口。
- index 进入条件和 exact 回退策略文档。
- 性能验证文档：`docs/performance/PERFORMANCE_SCALE.md`。

## 5. 全局约束

- 继续以本地 Windows 工作站为主要部署目标。
- 继续保持 REST API 形态。
- 继续使用 FastAPI、InsightFace、ONNX Runtime、SQLite。
- 不引入 PyTorch。
- 不在同一环境同时安装 `onnxruntime` 和 `onnxruntime-gpu`。
- 默认 CPU 稳定运行，GPU 通过配置显式启用。
- 所有危险操作必须可审计、可确认、可回退。
- 所有新增前端语义必须同步 `docs/usage/API_INTEGRATION.md`。

## 6. 后续执行方式

后续建议按下面顺序启动 goal：

```text
/goal Implement face_api Roadmap V1.3 - Production Runtime Monitoring
/goal Implement face_api Roadmap V1.4 - Recognition Security Accuracy
/goal Implement face_api Roadmap V1.5 - Frontend Business Integration
/goal Implement face_api Roadmap V1.6 - Performance Scale
```

每个 goal 只实现一个版本，不跨版本混做。
