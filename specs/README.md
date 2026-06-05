# Spec Kit Roadmap 索引

本目录保存从产品 PRD 拆出来的 Spec Kit 功能规格。

## 当前产品基线

- `001-face-api-product` - face_api 产品整体基线和范围边界
- `ROADMAP-v1.0.md` - V1.0 后续 `/goal` 的版本化执行顺序
- `ROADMAP-v1.1.md` - V1.0 加固完成后的版本化功能路线图

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

## 推荐流程

任何阶段都按以下流程推进：

```text
spec -> clarify -> plan -> tasks -> implement
```

不要直接从本索引开始实现。先选择一个阶段，澄清未决问题，再创建实施计划。
