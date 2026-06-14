# 人脸识别 API 运行与使用说明

> 最后同步：2026-06-14
> 适用阶段：V1.9 现场验收收口与 P1/P2 小修

这是 **首次接手时优先阅读** 的文档。

如果你不知道该看哪份文档，先看：

- `docs/01_document_index.md`

如果你想先用一张图理解整体架构，可以直接双击：

- `architecture.html`

它是交互式架构讲解页，支持演示模式、流程播放和 SVG 导出。

如果你要把控季度进度和功能边界，看：

- `docs/02_product/02_quarterly_plan.md`

如果你现在的目标是：
- 把服务跑起来
- 验证接口是否可用
- 知道下一份该看什么文档

先看这一份就够了。

---

## 1. 项目是什么

`face_api` 是一个运行在本地 Windows 工作站上的人脸识别 REST API。

当前已经支持：
- 人脸检测
- 单人脸特征提取（受控 primitive）
- 1:1 人脸比对
- 1:N 人脸搜索
- 人脸库增删查
- 轻量人脸登录认证
- 最小运维状态 / 配置 / 审计查询

它当前更适合被理解为：

> **可复用的人脸识别模块底座**

而不是：

> 完整登录平台 / 权限平台 / 大规模向量数据库平台

它不负责：
- 业务用户主表管理
- token / session 签发
- 完整权限体系
- 分布式部署
- 完整风控平台

---

## 2. 唯一推荐启动路径

当前仓库同时保留了 conda 和 venv 两套说明，但：

- **主路径：conda**
- **备选路径：venv**

第一次接手时，**直接按 conda 路径跑**，不要犹豫。

### 方式 A：双击启动

直接双击：

- `H:\AI_test\face_api\run.bat`

### 方式 B：命令行启动

在 **Anaconda Prompt / cmd** 中执行：

```bat
cd /d H:\AI_test\face_api
conda activate face_api
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

启动成功后默认访问：

- Swagger：`http://localhost:8000/docs`
- OpenAPI：`http://localhost:8000/openapi.json`
- 联调页：直接打开 `test.html`
- 摄像头接入示例：直接打开 `camera-integration.html`，可做服务检查、注册、登录、活体和 audit 验收

---

## 3. 启动后最小验证（只做这 3 步）

### 1）健康检查

```bat
curl http://localhost:8000/health
```

期望返回类似：

```json
{ "status": "ok", "device": "CPU", "faces": 0 }
```

### 2）打开 Swagger

浏览器打开：

```text
http://localhost:8000/docs
```

### 3）查看 OpenAPI

```bat
curl http://localhost:8000/openapi.json
```

做到这 3 步，就说明：
- 服务起来了
- 路由注册正常
- 文档可访问

---

## 4. 接口怎么分层理解

这是当前模块最重要的理解方式。

### runtime primitives
给受控集成方的原子能力：
- `GET /health`
- `GET /system/status`
- `GET /config/effective`
- `POST /extract/base64`

### library helpers
围绕人脸库和通用识别的能力：
- `POST /detect`
- `POST /detect/base64`
- `POST /compare`
- `POST /search`
- `POST /faces/register`
- `GET /faces`
- `DELETE /faces/{face_id}`

### auth helper
给业务系统做认证辅助：
- `POST /auth/face-login`

### ops helpers
给运维/调优用：
- `GET /audit/login/recent`
- `GET /audit/login/summary`

---

## 5. 鉴权规则

先记最重要的两句：

### 永远公开
- `GET /health`

### 强制鉴权
这些接口必须显式配置并传入 `X-API-Key`：
- `POST /extract/base64`
- `GET /system/status`
- `GET /config/effective`
- `POST /auth/face-login`
- `GET /audit/login/recent`
- `GET /audit/login/summary`

### 条件启用鉴权
这些接口保留原有兼容行为：
- `POST /detect`
- `POST /detect/base64`
- `POST /compare`
- `POST /faces/register`
- `GET /faces`
- `DELETE /faces/{face_id}`
- `POST /search`

也就是说：
- 如果没设置 `FACE_API_KEY`，这些接口默认不强制校验
- 如果设置了 `FACE_API_KEY`，就必须带请求头

---

## 6. 当前最常用的接口

### 探活
- `GET /health`

### 检测
- `POST /detect`
- `POST /detect/base64`

### 提特征（受控 primitive）
- `POST /extract/base64`

### 比对 / 检索
- `POST /compare`
- `POST /search`

### 登录辅助
- `POST /auth/face-login`

### 运维
- `GET /system/status`
- `GET /config/effective`
- `GET /audit/login/recent`
- `GET /audit/login/summary`

详细请求/响应样例不要在这里死记，直接去看：
- `docs/04_usage/01_api_integration.md`
- `docs/04_usage/02_frontend_business_integration.md`

---

## 7. GPU / CPU 怎么看

### 默认行为
系统默认：
- 使用 `CPUExecutionProvider`
- 不主动占用 GPU，适合 Windows 工作站稳定运行

### 启用 GPU
需要 GPU 推理时显式设置：

```bat
set FACE_USE_GPU=1
```

此时如果 `CUDAExecutionProvider` 可用，服务会优先使用 GPU，并保留 CPU 作为回退 provider。

### 强制 CPU 覆盖
如果同时配置了 GPU 开关，但临时想强制回到 CPU：

```bat
set FACE_FORCE_CPU=1
```

### 一个非常容易误解的点

**看到 CUDA provider，不代表实际推理已经稳定跑在 GPU 上。**

判断顺序建议：
1. 看 `onnxruntime.get_available_providers()`
2. 看服务启动日志
3. 看接口耗时
4. 必要时再做单独 provider 验证

### 模型初始化失败怎么看

如果服务启动时报 `FaceEngine initialization failed`，优先看错误中的：
- `model`
- `det_size`
- `force_cpu`
- `use_gpu`
- `available_providers`
- `selected_providers`
- `Original error`

这几个字段可以判断是模型下载/路径问题、CUDA provider 问题，还是输入配置问题。

---

## 8. 环境变量

| 变量 | 默认值 | 作用 |
|---|---|---|
| `FACE_MODEL` | `buffalo_l` | 模型名 |
| `FACE_DET_SIZE` | `640` | 检测输入尺寸 |
| `FACE_DB_PATH` | `faces.db` | SQLite 数据库路径 |
| `FACE_ENV` | `development` | 运行环境；`production` 会启用更严格启动校验 |
| `FACE_PORT` | `8000` | `run-prod.bat` 监听端口 |
| `FACE_PYTHON` | `D:\anaconda3\envs\face_api\python.exe` | `run-prod.bat` 使用的 Python 解释器路径 |
| `FACE_USE_GPU` | `0` | 设为 `1` 时允许优先使用 GPU |
| `FACE_FORCE_CPU` | `0` | 设为 `1` 时强制 CPU，并覆盖 `FACE_USE_GPU` |
| `FACE_API_KEY` | 空 | 启用 API Key 鉴权 |
| `FACE_CORS_ORIGINS` | `*` | 允许跨域访问的前端来源，多个用英文逗号分隔 |
| `FACE_LOG_PATH` | `logs/face_api.log` | 服务日志文件路径 |
| `FACE_LOG_MAX_BYTES` | `10485760` | 单个日志文件最大字节数 |
| `FACE_LOG_BACKUP_COUNT` | `5` | 日志轮转保留文件数 |
| `FACE_MAINTENANCE_FILE` | `.maintenance_mode` | 运维控制台维护模式标记文件 |
| `FACE_ALLOW_ONLINE_RESTORE` | 开发为 `1`，生产为 `0` | 是否允许通过 API 在线恢复数据库；生产建议停服务后离线恢复 |
| `FACE_DUPLICATE_POLICY` | `allow` | 同一 `user_id` 重复注册策略：`allow` / `reject` / `replace` |
| `FACE_MIN_REGISTER_DET_SCORE` | `0.5` | 注册人脸最低检测置信度 |
| `FACE_MIN_REGISTER_FACE_PIXELS` | `2500` | 注册人脸框最小像素面积 |
| `FACE_MIN_REGISTER_BRIGHTNESS` | `30` | 注册图片最低平均亮度 |
| `FACE_MAX_REGISTER_BRIGHTNESS` | `225` | 注册图片最高平均亮度 |
| `FACE_MIN_LOGIN_DET_SCORE` | `0.4` | 登录人脸最低检测置信度 |
| `FACE_MIN_LOGIN_FACE_PIXELS` | `1600` | 登录人脸框最小像素面积 |
| `FACE_MIN_FACE_SHARPNESS` | `2` | 注册/login 图片最低清晰度 |
| `FACE_LOGIN_LIVENESS_ENABLED` | `1` | face login 是否启用活体检测 |
| `FACE_REGISTER_LIVENESS_ENABLED` | `0` | 注册是否启用活体检测 |
| `FACE_CHALLENGE_TTL_SECONDS` | `60` | 活体 challenge 有效期 |
| `FACE_CHALLENGE_ACTION_SECONDS` | `10` | 活体动作完成窗口 |
| `FACE_CHALLENGE_MIN_FRAMES` | `10` | 眨眼 challenge 最少连续帧 |
| `FACE_CHALLENGE_MAX_FRAMES` | `30` | 眨眼 challenge 最多连续帧；如果最小帧数配置超过 30 且未显式设置该值，默认会跟随最小帧数 |
| `FACE_CHALLENGE_ACTIONS` | `blink` | 支持的活体动作，V1.1 稳定支持 `blink` |
| `FACE_DEFAULT_POLICY_PROFILE` | `default` | 默认识别策略档案 |
| `FACE_TERMINAL_POLICY_MAP` | 空 | terminal 到策略档案的绑定，如 `door-1:strict` |
| `FACE_MAX_BASE64_CHARS` | `11185068` | Base64 图片字符串最大长度 |
| `FACE_MAX_IMAGE_BYTES` | `8388608` | 解码后图片字节最大值 |
| `FACE_MAX_IMAGE_PIXELS` | `4096000` | 解码后图片最大像素数 |

---

## 9. 生产运行

生产类运行使用：

```bat
set FACE_API_KEY=your-secret
run-prod.bat
```

`run-prod.bat` 会设置 `FACE_ENV=production`，并且不使用 `--reload`。默认监听 8000；如需换端口：

```bat
set FACE_PORT=8001
run-prod.bat
```

启动后建议运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\health-check.ps1
```

详细运行、备份、恢复和排障说明见：

- `docs/03_deployment/01_runbook.md`
- `docs/04_usage/03_recognition_security_accuracy.md`

### Windows 长期运行

V1.7 提供两种长期运行方式：

- Task Scheduler：轻量开机或登录后自启。
- NSSM：注册成 Windows Service，适合正式交付。

安装前先用 `-WhatIf` 预览：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-task-scheduler.ps1 -Port 8000 -WhatIf
powershell -ExecutionPolicy Bypass -File scripts\install-task-scheduler.ps1 -Port 8000
```

NSSM 方案需要先安装 NSSM，并显式传入 `nssm.exe` 路径：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-nssm-service.ps1 -NssmPath C:\tools\nssm\nssm.exe -ApiKey "your-secret" -Port 8000 -WhatIf
powershell -ExecutionPolicy Bypass -File scripts\install-nssm-service.ps1 -NssmPath C:\tools\nssm\nssm.exe -ApiKey "your-secret" -Port 8000
```

Task Scheduler 脚本不会把 `FACE_API_KEY` 写入任务动作；请先在运行用户或机器环境变量里配置 `FACE_API_KEY`。如果 NSSM 安装时传入 `-ApiKey`，密钥会保存到 NSSM 服务环境中；更严格的交付方式是先配置机器环境变量 `FACE_API_KEY`，NSSM 安装脚本不传 `-ApiKey`。

详细安装、卸载和排障见 `docs/03_deployment/01_runbook.md`。

### 运维控制台

V1.1 提供本地运维控制台：

```text
http://localhost:8000/admin.html
```

控制台复用 `FACE_API_KEY`。支持查看状态、人脸记录、audit、删除记录、备份数据库和恢复数据库。

高风险规则：

- 删除人脸记录必须二次确认。
- 恢复数据库必须先进入维护模式，再二次确认。
- 在线恢复只适合单进程维护窗口；production 默认禁用在线恢复，多 worker 或生产恢复建议先停止 API 服务，再用恢复脚本执行。
- 控制台、人脸库、搜索和登录接口不会展示 embedding 或 API secret；`/extract/base64` 仅用于受控服务侧特征提取，不建议暴露给普通页面。

活体 challenge 通过后会绑定当次连续帧里检测到的人脸，后续 login 或启用活体的注册必须使用同一个人的图片。

---

## 10. 数据库文件说明

运行过程中通常会看到：
- `faces.db`
- `faces.db-wal`
- `faces.db-shm`

这是 WAL 模式下的正常现象。

### 备份
- **停服务后** 复制数据库文件
- 或运行 `scripts\backup-db.ps1`

### 恢复
- 停服务
- 运行 `scripts\restore-db.ps1 -BackupDir <备份目录>`
- 重启服务
- 运行 `scripts\health-check.ps1`

### 清空底库
- 停服务
- 删除 `faces.db`、`faces.db-wal`、`faces.db-shm`
- 重启服务后自动重建空库

---

## 11. 常见问题

### Q1：我该先看哪份文档？

按这个顺序：
1. `README.md` —— 先跑起来
2. `docs/04_usage/01_api_integration.md` —— 看怎么调用接口
3. `docs/05_architecture/01_architecture.md` —— 看架构、边界和维护重点
4. `docs/90_archive/01_releases/01_2026-05-27_phase_1_summary.md` —— 看当前阶段成果和风险边界

### Q2：报 `ModuleNotFoundError`

说明环境没激活好，先确认：
- conda 路径是否已 `conda activate face_api`
- venv 路径是否已 `venv\Scripts\activate`

### Q3：前端接口报 401

优先检查：
- 是否设置了 `FACE_API_KEY`
- 前端是否带了 `X-API-Key`
- 当前调用的是不是强制鉴权接口

### Q4：局域网访问不了

排查顺序：
1. 服务是否启动成功
2. 是否绑定 `0.0.0.0`
3. 后端机器 IPv4 是否正确
4. Windows 防火墙是否放行 8000 端口

---

## 12. 其他文档分别干什么

### `docs/04_usage/01_api_integration.md`
适合：
- 前端/全栈联调
- 想直接复制请求体、返回体、TS 类型、fetch 示例

### `docs/04_usage/02_frontend_business_integration.md`
适合：
- 接摄像头 login / register
- 看错误码中文映射、业务系统调用示例和上线检查清单
- 明确 face_api 识别结果和业务系统 session 的边界

### `docs/05_architecture/01_architecture.md`
适合：
- 接手维护
- 看模块边界、数据流、存储设计、高风险改动点

### `docs/90_archive/01_releases/01_2026-05-27_phase_1_summary.md`
适合：
- 看本轮阶段成果
- 看 phase-1 当前已经交付了什么
- 看已接受的风险边界
