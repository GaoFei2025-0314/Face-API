# 任务：Windows 长期运行加固

- [x] 梳理现有 `run-prod.bat`、监控脚本和停止脚本。
- [x] 改造 `run-prod.bat` 支持 `FACE_PORT`，默认仍为 8000。
- [x] 新增 `scripts/install-task-scheduler.ps1`。
- [x] 新增 `scripts/uninstall-task-scheduler.ps1`。
- [x] 新增 `scripts/install-nssm-service.ps1`。
- [x] 新增 `scripts/uninstall-nssm-service.ps1`。
- [x] 脚本支持配置项目路径、任务/服务名称、端口、Python 路径和环境变量。
- [x] 安装/卸载脚本支持 dry-run / WhatIf 类安全预览。
- [x] 安装/卸载脚本重复执行时给出清晰结果，不留下不可恢复状态。
- [x] 脚本输出健康检查和日志检查提示。
- [x] 增加 PowerShell 脚本 smoke test，覆盖语法、帮助信息、参数校验和 NSSM 缺失提示。
- [x] 验证 Task Scheduler 安装、启动、卸载流程（脚本 smoke + WhatIf 安全验证 + 临时任务真实创建/删除；启动验证见验收记录）。
- [x] 验证 NSSM 安装、启动、卸载流程（脚本 smoke + NSSM 参数 stub + NSSM 缺失负向验证；真实安装需现场具备 NSSM）。
- [x] 更新 `docs/03_deployment/01_runbook.md`。
- [x] 更新 `README.md` 的生产运行入口说明。
- [x] 完成 Windows 现场手工验收记录。
