# face_api Windows 工作站运行手册

## 1. 适用范围

本文用于 `face_api Roadmap v1.0/v1.1` 的生产类本地运行、交付、备份、恢复和排障。

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

## 5. CORS

开发环境可以使用默认 `*`。

生产类环境建议设置明确前端地址：

```bat
set FACE_CORS_ORIGINS=http://localhost:3000,http://192.168.1.100:3000
```

CORS 只控制浏览器跨域，不替代 `X-API-Key`。

## 6. 备份

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

## 7. 恢复

恢复前先停止服务。

运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\restore-db.ps1 -BackupDir backups\20260605-120000
```

恢复后重新启动服务，并运行健康检查。

如果通过 V1.1 运维控制台恢复数据库，必须先进入维护模式，再二次确认恢复。production 默认禁用在线恢复；生产恢复建议先停止 API 服务，再运行 `scripts\restore-db.ps1` 离线恢复。恢复完成后退出维护模式，并运行健康检查。

## 8. 常见问题

### 服务启动时报 `FACE_API_KEY`

生产类环境必须设置 `FACE_API_KEY`。

### 服务很慢

先看 `/system/status` 或 `/config/effective` 中的 `device`、`use_gpu`、`force_cpu`。

默认是 CPU。如需 GPU，设置 `FACE_USE_GPU=1`。

### 前端跨域失败

检查 `FACE_CORS_ORIGINS` 是否包含前端地址。

### 人脸登录失败

查看接口返回的 `detail.code`、`detail.reason`，再查看 `logs/face_api.log` 和 `/audit/login/recent`。

### 数据恢复后人脸数量不对

确认恢复时服务已经停止，并且 `faces.db`、`faces.db-wal`、`faces.db-shm` 都来自同一份备份。
