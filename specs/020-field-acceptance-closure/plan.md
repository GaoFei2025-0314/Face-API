# 实施计划：现场验收收口与 P1/P2 小修

## 范围

V1.9 只做现场验收收口和验收暴露的 P1/P2 小修。重点是确认 V1.8 已交付能力在真实工作站、真实摄像头和交付文档中可用、可解释、可维护。

本计划覆盖：

- Windows 启动、停止、监控和状态验收。
- 摄像头注册、login challenge、face login 和中文错误验收。
- login audit、维护模式、备份和恢复验收。
- `architecture.html` 与文档一致性验收。
- 验收中确认的 P1/P2 小修闭环。

## 设计决策

- 不新增公开 API、环境变量或鉴权机制。
- 不新增完整业务后端、前端项目或向量数据库。
- `/admin/overview` 继续作为轻量控制台概览，不返回全量人脸列表。
- 小修必须从验收复现开始；生产代码修复必须优先补自动化测试。
- 页面或现场问题无法自动化时，必须写入 V1.9 验收记录。
- P3/P4 问题只记录，不进入本版本实现范围。

## 验证

- 运行 `D:\anaconda3\envs\face_api\python.exe -m unittest discover -s tests -v`。
- 运行 `git diff --check`。
- 扫描本地 HTML 外部依赖：

```powershell
Select-String -Path "H:\AI_test\face_api\architecture.html","H:\AI_test\face_api\camera-integration.html","H:\AI_test\face_api\admin.html" -Pattern "cdn|script src|link rel=.*stylesheet|import |require\("
```

- 在目标工作站验证服务启动、`/health`、`/system/status`、`/config/effective`。
- 使用 `camera-integration.html` 验证摄像头授权、注册、login challenge、face login 和中文错误。
- 使用 `admin.html` 验证运行概览、维护模式、备份和恢复。
- 使用 `architecture.html` 验证角色视图、流程播放和实际架构一致。

