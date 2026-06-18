# Spec Kit Roadmap 索引

本目录保存从产品 PRD 拆出来的 Spec Kit 功能规格。

## 当前产品基线

- `001-face-api-product` - face_api 产品整体基线和范围边界
- `ROADMAP-v1.0.md` - V1.0 后续 `/goal` 的版本化执行顺序
- `ROADMAP-v1.1.md` - V1.0 加固完成后的版本化功能路线图
- `ROADMAP-v1.2.md` - V1.1 完成后的 A/B/C/D 四条产品线总规划
- `ROADMAP-v1.7.md` - 现场闭环与 Windows 长期运行版规划
- `ROADMAP-v1.9.md` - 现场验收收口与 P1/P2 小修规划
- `ROADMAP-v2.0.md` - 业务系统正式接入示范版规划
- `ROADMAP-v2.1.md` - 轻量防翻拍活体增强规划
- `ROADMAP-v2.2.md` - 现场算法验收与阈值调优台规划
- `ROADMAP-v2.3.md` - 轻量防翻拍阈值治理与中风险重试机制规划
- `ROADMAP-v2.4.md` - Face API 与 WMS 现场联动验收基线规划

## 已规划开发阶段

Roadmap v1.0 执行顺序：

1. `002-production-hardening` - 稳定的生产类工作站运行
2. `003-runtime-config-startup` - 运行配置可见性和启动校验
3. `004-logging-audit-diagnostics` - 日志、audit 记录和诊断
4. `007-security-hardening` - CORS、受保护端点、敏感数据和基础防滥用
5. `008-delivery-deployment` - 交付、部署、备份、恢复和排障
6. `005-face-database-governance` - 人脸库质量和注册治理
7. `006-search-performance` - 可度量的 search 和 login 辅助性能改进

Roadmap v1.1 建议执行顺序：

1. `009-liveness-anti-spoofing` - 活体与防冒用控制
2. `010-recognition-policy-tuning` - 阈值和质量策略调参
3. `011-vector-search-scaling` - 更大人脸库 search 扩展
4. `012-admin-ops-console` - 本地运维控制台
5. `013-terminal-integration-kit` - 多 terminal 和业务系统接入指引

Roadmap v1.1 已确认主定位为“现场安全可用版”。关键决策包括：

- 活体检测真实实现，支持 login/注册分别配置开关；login 默认开启，注册默认关闭。
- 活体采用单张图片判断 + challenge 动作挑战；第一版至少稳定支持眨眼。
- 注册和 login 都必须携带 `terminal_id`。
- 搜索扩展目标为 5 万人脸记录，login/search 1 秒内返回。
- 控制台第一版包含查看、删除、备份、恢复，并复用 `FACE_API_KEY`。

Roadmap v1.2+ 建议版本线：

1. `014-production-runtime-monitoring` - 生产运行、启动停止、监控和恢复
2. `015-recognition-security-accuracy` - 识别安全、准确率、质量评分和调参
3. `016-frontend-business-integration` - 摄像头前端示例、业务接入和错误映射
4. `017-performance-scale` - 5 万人脸 benchmark、批量数据和搜索扩展

Roadmap v1.2 是规划版，只建立总 PRD/specs；后续建议从 V1.3 开始逐版本实施。

Roadmap v1.7 建议执行顺序：

1. `018-camera-acceptance-loop` - 摄像头注册登录闭环验收
2. `019-windows-long-running` - Windows 长期运行加固

Roadmap v1.7 已确认主定位为“现场闭环与 Windows 长期运行版”。关键决策包括：

- 先增强 `camera-integration.html`，不新增独立验收页面。
- 先跑通 face_api 自己的页面，不接业务后端。
- 页面展示注册、登录、活体状态、中文错误原因和最近 login audit。
- Task Scheduler 和 NSSM 两种长期运行方案都规划。
- 两种方案都提供安装和卸载脚本。
- NSSM 不由脚本静默下载。

Roadmap v1.9 建议执行顺序：

1. `020-field-acceptance-closure` - 现场验收收口与 P1/P2 小修

Roadmap v1.9 已确认主定位为“现场验收收口与 P1/P2 小修”。关键决策包括：

- 先做真实工作站、真实摄像头和文档一致性验收。
- 允许修复验收中确认的 P1/P2 小问题。
- 不新增公开 API、环境变量、鉴权机制或大功能。
- P3/P4 问题只记录到验收记录或后续 backlog。
- `/admin/overview` 保持轻量概览定位，不返回全量人脸列表。

Roadmap v2.0 建议执行顺序：

1. `021-business-integration-demo` - 业务接入 Demo 套件

Roadmap v2.0 已完成，主定位为“业务系统正式接入示范版”。关键决策包括：

- `face_api` 只做人脸识别服务，不接管业务用户、登录态和权限。
- 同时规划 Web 业务系统链路和受控终端链路。
- Demo 后端使用 FastAPI + SQLite，真实生产接入按 Java / Spring Boot 文档替换。
- 一个业务用户只允许一个有效人脸绑定，支持解绑和换脸。
- 登录必须活体，绑定活体可配置。
- 不新增 `face_api` 公开接口，新增接口只属于 `business-demo`。
- 验收记录见 `docs/90_archive/04_acceptance/04_v2.0_acceptance_record.md`。

Roadmap v2.1 建议执行顺序：

1. `022-lightweight-anti-spoofing` - 轻量防翻拍活体增强

Roadmap v2.1 已完成，主定位为“轻量防翻拍活体增强”。关键决策包括：

- 选择轻量风险评分路线，不做重交互活体。
- 低风险用户不默认增加复杂动作。
- 中风险记录 audit 并提示调整采集条件。
- 高风险可拒绝本次 login 或注册。
- 验收样例覆盖真人、打印照片、手机屏幕、电脑屏幕和播放视频。
- 不新增硬件，不引入重型 anti-spoofing 模型，不承诺企业级强活体。

Roadmap v2.1 历史入口和验收入口：

- `022-lightweight-anti-spoofing/spec.md`
- `022-lightweight-anti-spoofing/plan.md`
- `022-lightweight-anti-spoofing/tasks.md`
- `docs/90_archive/04_acceptance/05_v2.1_acceptance_record.md`

Roadmap v2.2 当前执行入口：

- `023-field-algorithm-acceptance-console/spec.md`
- `023-field-algorithm-acceptance-console/plan.md`
- `023-field-algorithm-acceptance-console/tasks.md`
- `docs/90_archive/04_acceptance/06_v2.2_acceptance_record.md`

Roadmap v2.2 建议执行顺序：

1. `023-field-algorithm-acceptance-console` - 现场算法验收与阈值调优台

Roadmap v2.2 已确认主定位为“现场算法验收与阈值调优台”。关键决策包括：

- 新建独立 `acceptance.html`。
- 测试用户 `user_id` 使用数字或留空。
- 固定五类样例，每类默认 3 次。
- 走完整登录链路。
- 活体失败时记录失败，不继续 face login。
- 注册/重绑兼容注册活体开关。
- 通过 `FACE_CORS_ORIGINS` 支持 `http://localhost:8122` 现场浏览器验收。
- 不新增 `face_api` 后端 API，不新增数据库表。
- 支持 JSON/CSV 报告下载。
- 不保存原图、连续帧或 API Key。
- 只提供保守调参方向。

Roadmap v2.3 已完成入口：

- `024-lightweight-anti-spoof-governance/spec.md`
- `024-lightweight-anti-spoof-governance/plan.md`
- `024-lightweight-anti-spoof-governance/tasks.md`
- `docs/90_archive/04_acceptance/07_v2.3_acceptance_record.md`

Roadmap v2.3 建议执行顺序：

1. `024-lightweight-anti-spoof-governance` - 轻量防翻拍阈值治理与中风险重试机制

Roadmap v2.3 已完成，主定位为“轻量防翻拍阈值治理与中风险重试机制”。关键决策包括：

- 真人正脸至少 2/3 通过。
- 翻拍样例不能再低风险静默成功。
- 不新增复杂动作，不引入重型 anti-spoofing 模型。
- 增强现有连续帧轻量评分逻辑。
- 中风险默认由后端强制重试。
- 中风险策略可配置，默认最多重试 1 次。
- 中风险重试由后端 `risk_retry_token` 强制，不依赖前端 `state` 或业务端自报次数。
- 第一次中风险错误响应固定包含 `detail.retry.risk_retry_token`、`detail.retry.expires_at`、`detail.retry.remaining_attempts`。
- V2.3 最大重试次数固定为 1，不新增最大重试次数环境变量；只配置中风险策略和 retry token TTL。
- 固定摄像头现场五类样例验收通过；手持或移动摄像头制造运动视差记录为残余风险。

Roadmap v2.4 当前执行入口：

- `025-wms-capture-loop-baseline/spec.md`
- `025-wms-capture-loop-baseline/plan.md`
- `025-wms-capture-loop-baseline/tasks.md`
- `docs/superpowers/specs/2026-06-17-face-api-wms-capture-loop-design.md`
- `docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md`
- `H:\AI_test\electron-wms\electron-wms\doc\13-Face-API-WMS智能抓拍联动验收基线.md`

Roadmap v2.4 建议执行顺序：

1. `025-wms-capture-loop-baseline` - Face API 与 WMS 现场联动验收基线

Roadmap v2.4 已确认主定位为“Face API + WMS 现场联动验收基线”。关键决策包括：

- 先建立联动验收基线，不默认修改 `face_api` 后端接口。
- 先新增 Face API 侧验收模板和 WMS 侧 runbook，不默认改 WMS 登录业务逻辑。
- WMS 仓库路径按 `H:\AI_test\electron-wms\electron-wms` 检查；路径不存在时停止并记录阻塞。
- 问题必须归到算法底座、终端采集或业务流程三类之一。
- 验收记录不得保存原图、视频帧、连续帧、embedding、API Key 或真实用户敏感信息。
- V2.4 的产出用于决定 V2.5 优先改算法、WMS 采集还是业务提示。

## 推荐流程

任何阶段都按以下流程推进：

```text
spec -> clarify -> plan -> tasks -> implement
```

不要直接从本索引开始实现。先选择一个阶段，澄清未决问题，再创建实施计划。
