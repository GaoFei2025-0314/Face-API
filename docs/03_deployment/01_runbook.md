# face_api Windows 工作站运行手册

## 1. 适用范围

本文用于 `face_api Roadmap v1.0-v1.6` 的生产类本地运行、交付、备份、恢复和排障。

目标环境是单台 Windows 工作站。

## 2. 生产启动

生产类运行使用：

```bat
run-prod.bat
```

生产类启动默认要求：

- `FACE_ENV=production`
- 必须配置 `FACE_API_KEY`
- 默认 CPU 推理
- 如需 GPU，显式设置 `FACE_USE_GPU=1`
- 如需强制 CPU，设置 `FACE_FORCE_CPU=1`

生产类运行不使用 `--reload`。

## 3. 最小验证

启动后运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\health-check.ps1
```

如果需要验证受保护配置接口，先设置：

```powershell
$env:FACE_API_KEY="你的密钥"
```

## 4. 日志

默认日志路径：

```text
logs/face_api.log
```

可通过环境变量修改：

```bat
set FACE_LOG_PATH=logs\face_api.log
```

日志中不应包含 API Key、图片 Base64 或 embedding。

V1.3 起支持日志轮转，避免单个日志文件无限增长：

```bat
set FACE_LOG_MAX_BYTES=10485760
set FACE_LOG_BACKUP_COUNT=5
```

- `FACE_LOG_MAX_BYTES`：单个日志文件最大字节数，默认 10 MB。
- `FACE_LOG_BACKUP_COUNT`：保留历史日志数量，默认 5 个。
- 轮转后会生成 `face_api.log.1`、`face_api.log.2` 等历史文件。

## 5. CORS

开发环境可以使用默认 `*`。

生产类环境建议设置明确前端地址：

```bat
set FACE_CORS_ORIGINS=http://localhost:3000,http://192.168.1.100:3000
```

CORS 只控制浏览器跨域，不替代 `X-API-Key`。

## 6. 备份

## 6. 停止服务

开发窗口中可以按 `Ctrl+C`。

V1.3 起推荐使用停止脚本释放端口和 uvicorn 父子进程：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop-service.ps1
```

脚本默认只会停止命令行匹配当前项目目录或 `uvicorn main:app` 的进程。如果 8000 被其他程序占用，脚本会打印 PID 和命令行并拒绝强杀。

如果使用非默认端口：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop-service.ps1 -Port 8001
```

只有人工确认该进程可以停止时，才使用：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop-service.ps1 -ForceUnrelated
```

## 7. 备份

建议停服务后备份 SQLite 文件。

运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\backup-db.ps1
```

V1.1 也可以通过运维控制台触发备份：

```text
http://localhost:8000/admin.html
```

需要关注的文件包括：

- `faces.db`
- `faces.db-wal`
- `faces.db-shm`

## 8. 恢复

恢复前先停止服务。

运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\restore-db.ps1 -BackupDir backups\20260605-120000
```

恢复后重新启动服务，并运行健康检查。

如果通过 V1.1 运维控制台恢复数据库，必须先进入维护模式，再二次确认恢复。production 默认禁用在线恢复；生产恢复建议先停止 API 服务，再运行 `scripts\restore-db.ps1` 离线恢复。恢复完成后退出维护模式，并运行健康检查。

## 9. 监控

V1.3 起提供监控脚本，用于一次性查看健康接口、OpenAPI、受保护配置、端口、进程、数据库文件、日志文件和 GPU 状态：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\monitor-service.ps1
```

带 API Key 检查受保护接口：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\monitor-service.ps1 -ApiKey $env:FACE_API_KEY
```

监控输出重点看：

- `Port`：8000 是否有监听进程。
- `Health`：`/health` 是否返回 `status=ok`。
- `Protected Config`：带 `X-API-Key` 是否能访问 `/config/effective`。
- `Database`：`faces.db`、`faces.db-wal`、`faces.db-shm` 文件大小和更新时间。
- `Log`：日志是否存在，最近是否有错误。
- `GPU`：`nvidia-smi` 是否可用。CPU 模式运行时 GPU 不可用不一定是错误。

## 10. 常见问题

### 服务启动时报 `FACE_API_KEY`

生产类环境必须设置 `FACE_API_KEY`。

### 服务很慢

先看 `/system/status` 或 `/config/effective` 中的 `device`、`use_gpu`、`force_cpu`。

默认是 CPU。如需 GPU，设置 `FACE_USE_GPU=1`。

### 前端跨域失败

检查 `FACE_CORS_ORIGINS` 是否包含前端地址。

### 人脸登录失败

查看接口返回的 `detail.code`、`detail.reason`，再查看 `logs/face_api.log` 和 `/audit/login/recent`。

### 启动提示端口被占用

说明 8000 端口已有旧服务或其他程序在监听。先运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop-service.ps1
```

再重新执行 `run.bat` 或 `run-prod.bat`。

### 日志文件过大

检查 `/config/effective` 返回里的 `log_rotation.max_bytes` 和 `log_rotation.backup_count`。如果历史日志仍过多，可以在停服务后手工归档或删除旧的 `logs\face_api.log.*`。

### 数据恢复后人脸数量不对

确认恢复时服务已经停止，并且 `faces.db`、`faces.db-wal`、`faces.db-shm` 都来自同一份备份。
