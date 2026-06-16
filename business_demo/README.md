# business-demo

`business-demo` 是 V2.0 的 mock 业务后端，用来演示真实业务系统如何接入 `face_api`。

它负责：

- 业务用户。
- 人脸绑定、解绑和换脸。
- Web 活体登录代理。
- demo token。
- 业务登录 audit。
- 受控终端登录事件上报。

它不负责替代真实 Java / Spring Boot 后端；正式系统应按 `docs/04_usage/05_spring_boot_integration_notes.md` 替换。

## 启动

先启动 `face_api`：

```bat
set FACE_API_KEY=your-secret
run.bat
```

再启动 `business-demo`：

```bat
set FACE_API_KEY=your-secret
scripts\run-business-demo.bat
```

如果本机 Python 不在默认路径，先设置：

```bat
set FACE_PYTHON=D:\anaconda3\envs\face_api\python.exe
```

默认入口：

```text
http://localhost:8010
http://localhost:8010/terminal.html
```

`http://localhost:8010` 包含摄像头预览，普通业务浏览器只访问 `business-demo`，不会持有 `face_api` 的服务密钥。

## 配置

| 变量 | 默认值 | 说明 |
|---|---|---|
| `FACE_API_BASE_URL` | `http://localhost:8000` | `business-demo` 调用 `face_api` 的地址 |
| `FACE_API_KEY` | 空 | `business-demo` 服务端调用 `face_api` 的密钥 |
| `FACE_PYTHON` | `D:\anaconda3\envs\face_api\python.exe` | `run-business-demo.bat` 使用的 Python 解释器路径 |
| `BUSINESS_DEMO_ENV` | `development` | `business-demo` 运行环境；`production` 会拒绝默认 demo token 密钥 |
| `BUSINESS_DEMO_PORT` | `8010` | `business-demo` 监听端口 |
| `BUSINESS_DEMO_DB_PATH` | `business-demo.db` | 业务 demo SQLite 文件 |
| `BUSINESS_DEMO_BINDING_LIVENESS_REQUIRED` | `0` | 绑定人脸是否要求 register 活体 |
| `BUSINESS_DEMO_TOKEN_SECRET` | `business-demo-dev-secret` | demo token 签名密钥；仅适合开发，`BUSINESS_DEMO_ENV=production` 时必须替换为随机长密钥 |
| `BUSINESS_DEMO_TOKEN_TTL_SECONDS` | `3600` | demo token 有效期 |

生产类演示环境建议至少设置：

```bat
set BUSINESS_DEMO_ENV=production
set BUSINESS_DEMO_TOKEN_SECRET=your-random-long-secret
```

## 终端 CLI

从受控 Windows 终端摄像头采集活体帧和登录图片：

```bat
python scripts\terminal-demo.py --terminal-id gate-01 --event-id event-001 --camera-index 0 --api-key your-secret
```

使用图片文件和外部活体帧文件：

```bat
python scripts\terminal-demo.py --terminal-id gate-01 --event-id event-002 --image login.jpg --liveness-frame frame01.jpg --liveness-frame frame02.jpg --liveness-frame frame03.jpg --liveness-frame frame04.jpg --liveness-frame frame05.jpg --liveness-frame frame06.jpg --liveness-frame frame07.jpg --liveness-frame frame08.jpg --liveness-frame frame09.jpg --liveness-frame frame10.jpg --api-key your-secret
```

文件帧模式至少传 10 帧；现场验收更推荐摄像头模式。

复用已通过且未消费的 login challenge：

```bat
python scripts\terminal-demo.py --terminal-id gate-01 --event-id event-003 --image login.jpg --challenge-id passed-login-challenge-id --api-key your-secret
```
