# 人脸识别 API 运行与使用说明

> 最后同步：2026-05-27  
> 适用阶段：face_api modularization phase-1

这是 **首次接手时优先阅读** 的文档。

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
- 活体检测

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
- `docs/usage/API_INTEGRATION.md`

---

## 7. GPU / CPU 怎么看

### 默认行为
系统默认：
- 优先尝试 `CUDAExecutionProvider`
- 不可用时回退 `CPUExecutionProvider`

### 强制 CPU
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
| `FACE_FORCE_CPU` | `0` | 设为 `1` 时强制 CPU |
| `FACE_API_KEY` | 空 | 启用 API Key 鉴权 |
| `FACE_MAX_BASE64_CHARS` | `11185068` | Base64 图片字符串最大长度 |
| `FACE_MAX_IMAGE_BYTES` | `8388608` | 解码后图片字节最大值 |
| `FACE_MAX_IMAGE_PIXELS` | `4096000` | 解码后图片最大像素数 |

---

## 9. 数据库文件说明

运行过程中通常会看到：
- `faces.db`
- `faces.db-wal`
- `faces.db-shm`

这是 WAL 模式下的正常现象。

### 备份
- **停服务后** 复制数据库文件

### 清空底库
- 停服务
- 删除 `faces.db`、`faces.db-wal`、`faces.db-shm`
- 重启服务后自动重建空库

---

## 10. 常见问题

### Q1：我该先看哪份文档？

按这个顺序：
1. `README.md` —— 先跑起来
2. `docs/usage/API_INTEGRATION.md` —— 看怎么调用接口
3. `docs/architecture/ARCHITECTURE.md` —— 看架构、边界和维护重点
4. `docs/releases/2026-05-27-phase-1-summary.md` —— 看当前阶段成果和风险边界

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

## 11. 其他文档分别干什么

### `docs/usage/API_INTEGRATION.md`
适合：
- 前端/全栈联调
- 想直接复制请求体、返回体、TS 类型、fetch 示例

### `docs/architecture/ARCHITECTURE.md`
适合：
- 接手维护
- 看模块边界、数据流、存储设计、高风险改动点

### `docs/releases/2026-05-27-phase-1-summary.md`
适合：
- 看本轮阶段成果
- 看 phase-1 当前已经交付了什么
- 看已接受的风险边界
