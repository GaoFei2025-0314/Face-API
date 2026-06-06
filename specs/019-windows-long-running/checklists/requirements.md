# 需求检查清单：Windows 长期运行加固

- [x] 范围明确：Task Scheduler + NSSM 两套长期运行方案。
- [x] 交付物明确：两套安装脚本、两套卸载脚本、runbook。
- [x] 不做事项明确：不静默下载 NSSM，不做服务管理平台。
- [x] 启动边界明确：production 风格启动，不使用 `--reload`。
- [x] 端口策略明确：优先改造 `run-prod.bat` 支持 `FACE_PORT`，默认 8000。
- [x] 脚本安全明确：安装/卸载支持 dry-run / WhatIf 类预览，重复执行可解释。
- [x] 脚本验证明确：需要 PowerShell smoke test 覆盖语法、帮助、参数和 NSSM 缺失提示。
- [x] 验收标准可执行：安装、启动、健康检查、卸载。
- [x] 排障场景明确：环境、端口、权限、日志、NSSM 缺失。
