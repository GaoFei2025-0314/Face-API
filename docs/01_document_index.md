# face_api 文档入口

这份文件是文档导航。以后不知道看哪里，先看这里。

## 1. 只想知道项目是什么

看：

- `docs/02_product/01_prd.md`

作用：

- 定义项目最终目标。
- 定义 face_api 做什么、不做什么。
- 判断新需求是否应该放进本项目。

## 2. 想知道当前季度进度

看：

- `docs/02_product/02_quarterly_plan.md`

作用：

- 看当前季度目标。
- 看已完成版本、待验证事项和下一版本计划。
- 控制功能不要失控扩张。

## 3. 想把服务跑起来

看：

- `README.md`
- `docs/03_deployment/01_runbook.md`

作用：

- `README.md`：第一次接手、启动、最小验证。
- `03_deployment/01_runbook.md`：生产运行、停止、监控、日志、备份、恢复、排障。

## 4. 想接前端或业务系统

看：

- `docs/04_usage/01_api_integration.md`
- `docs/04_usage/02_frontend_business_integration.md`
- `camera-integration.html`

作用：

- `04_usage/01_api_integration.md`：接口契约、请求返回、错误码。
- `04_usage/02_frontend_business_integration.md`：摄像头 login/register 标准流程。
- `camera-integration.html`：本机或内网联调、V1.7.1 现场闭环验收页面。

注意：正式前端不要直接持有 face_api 的 `X-API-Key`，应由业务后端代理调用 face_api。

## 5. 想看架构

看：

- `docs/05_architecture/01_architecture.md`
- `docs/05_architecture/02_face_api_rest_architecture.svg`

作用：

- 理解 FastAPI、FaceEngine、SQLite、脚本、前端示例之间的关系。

## 6. 想看识别安全和准确率

看：

- `docs/04_usage/03_recognition_security_accuracy.md`

作用：

- 看质量评分字段。
- 看细分错误原因。
- 看活体能力边界。
- 看 terminal 策略和调参原则。

## 7. 想看性能和规模化

看：

- `docs/06_performance/01_performance_scale.md`

作用：

- 看 5 万人脸 benchmark 怎么跑。
- 看批量导入/导出清单怎么校验。
- 看什么时候才考虑 index 或 ANN。

## 8. 想看每个版本怎么来的

看：

- `specs/README.md`
- `specs/ROADMAP-v1.2.md`
- `specs/ROADMAP-v1.7.md`
- `specs/014-production-runtime-monitoring/`
- `specs/015-recognition-security-accuracy/`
- `specs/016-frontend-business-integration/`
- `specs/017-performance-scale/`
- `specs/018-camera-acceptance-loop/`
- `specs/019-windows-long-running/`
- `docs/90_archive/04_acceptance/01_v1.7_acceptance_record.md`

作用：

- `specs/` 是开发过程和验收依据。
- 日常使用不需要每次看 `specs/`。
- 新版本开发前，再看对应 spec。

## 9. 文档分层规则

以后按这个规则维护：

- `docs/02_product/`：产品目标、季度计划、版本边界。
- `docs/03_deployment/`：启动、停止、监控、备份、恢复。
- `docs/04_usage/`：前端、业务系统、接口契约。
- `docs/05_architecture/`：整体架构。
- `docs/06_performance/`：benchmark、批量、规模化。
- `specs/`：spec-kit 规格、任务和验收记录。

如果一个文档不属于这些类别，就先不要新建，避免文档继续失控。
