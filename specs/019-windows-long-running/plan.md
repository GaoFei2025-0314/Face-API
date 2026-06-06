# 实施计划：Windows 长期运行加固

## 范围

为 face_api 提供两套 Windows 长期运行方案：

- Task Scheduler：轻量自启方案。
- NSSM：正式 Windows Service 方案。

本计划覆盖：

- 安装脚本。
- 卸载脚本。
- 启动验证。
- 日志路径说明。
- runbook 更新。

## 设计决策

- production 风格启动必须使用 `run-prod.bat` 或等价命令，不使用 `--reload`。
- 优先改造 `run-prod.bat` 支持 `FACE_PORT`，让手工运行、Task Scheduler 和 NSSM 使用同一套端口语义。
- Task Scheduler 方案作为简单路径，适合小白和临时现场。
- NSSM 方案作为正式路径，适合长期交付。
- NSSM 不由脚本静默下载。
- 所有脚本执行后输出 `/health` 验证命令和日志检查位置。
- 安装/卸载脚本应支持 dry-run / WhatIf 类预览，并做到重复执行可解释、可退出。

## 验证

- 执行 Task Scheduler 安装脚本。
- 手工触发计划任务并检查 `/health`。
- 执行 Task Scheduler 卸载脚本。
- 在 NSSM 可用时执行 NSSM 安装脚本。
- 启动服务并检查 `/health`。
- 执行 NSSM 卸载脚本。
- 验证 `FACE_PORT` 能改变 `run-prod.bat` 的监听端口，未设置时仍使用 8000。
- 验证安装/卸载脚本 dry-run / WhatIf 不修改系统状态。
- 运行 PowerShell 脚本 smoke test，覆盖语法、帮助信息、参数校验和 NSSM 缺失提示。
- 按 runbook 排查一次端口占用或环境缺失场景。
