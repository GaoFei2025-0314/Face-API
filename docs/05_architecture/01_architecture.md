# face_api 技术说明

> 最后同步：2026-05-27  
> 适用阶段：face_api modularization phase-1

这是 **维护 / 接手 / 架构理解文档**。  
如果你的目标是：
- 理解系统边界
- 理解模块职责
- 知道改哪里风险最大
- 后续继续演进这个模块

优先看这一份。

如果你只是想把服务跑起来：
- 看 `README.md`

如果你只是想联调接口：
- 看 `docs/usage/API_INTEGRATION.md`

如果你想看当前阶段成果和风险边界：
- 看 `docs/releases/2026-05-27-phase-1-summary.md`

---

## 1. 文档定位

本文不再承担：
- 启动手册
- 前端联调手册
- 阶段汇报文档

本文只承担 4 件事：
1. 解释系统边界
2. 解释模块分层
3. 解释存储与数据流
4. 说明维护时最容易踩坑的地方

---

## 2. 系统边界

`face_api` 当前更适合被理解为：

> **可复用的人脸识别模块底座**

它负责：
- 接收图片并执行人脸识别相关能力
- 维护本地人脸底库
- 根据匹配结果返回 `user_id` / `username`
- 提供最小审计、状态和配置读取能力

它不负责：
- 业务用户主表维护
- token / session 签发
- 完整权限体系
- 活体检测
- 多终端集中化审计平台
- 分布式部署或大规模向量检索

### 关键理解
- `/extract/base64` 是 **primitive**，给受控集成方用
- `/auth/face-login` 是 **auth helper**，不是完整登录系统
- `/audit/*`、`/system/status`、`/config/effective` 是 **ops/helper** 能力，不是普通前端页面能力

---

## 3. 模块化能力分层

当前系统可按 4 层理解：

### 3.1 runtime primitives
- `/health`
- `/system/status`
- `/config/effective`
- `/extract/base64`

用途：
- 给集成方提供最小可复用识别原子能力
- 给运维或桌面端提供当前运行状态和配置读取能力

### 3.2 library helpers
- `/detect`
- `/detect/base64`
- `/compare`
- `/search`
- `/faces/*`

用途：
- 围绕检测、比对、搜索、底库管理提供通用 helper 能力

### 3.3 auth helper
- `/auth/face-login`

用途：
- 返回识别后的认证辅助判定
- 不负责业务 token / session

### 3.4 ops helpers
- `/audit/login/recent`
- `/audit/login/summary`

用途：
- 查看最近登录尝试
- 查看成功/失败汇总
- 支撑阈值调优和现场排障

---

## 4. 模块职责

### `main.py`
负责：
- 创建 FastAPI 应用
- 定义请求/响应模型
- 配置 CORS
- 实现鉴权规则
- 解码图片
- 调用识别引擎
- 调用数据库读写 / 搜索 / 审计
- 组装响应

### `face_engine.py`
负责：
- 读取模型与检测尺寸配置
- 检测 ONNX Runtime provider
- 默认走 CPU；仅在 `FACE_USE_GPU=1` 且未强制 CPU 时尝试 GPU
- 初始化 `FaceAnalysis`
- 整理 InsightFace 输出
- 提供余弦相似度计算

### `storage.py`
负责：
- 初始化 SQLite 表结构
- 管理连接与 PRAGMA
- 保存 / 删除 / 列出底库记录
- 执行 1:N 搜索
- 保存 / 查询登录审计

---

## 5. 运行时约束

### 5.1 模块级单例
`main.py` 在模块导入时创建：
- `engine = FaceEngine(...)`
- `db = FaceDB()`

这意味着：
- 模型长驻内存
- 启动慢一点正常
- 不应在请求处理函数里重新初始化 `FaceEngine`
- 多 worker 下每个 worker 都会各自初始化资源

### 图片输入保护

所有图片入口必须经过统一校验：
- Base64 字符串长度不能超过 `FACE_MAX_BASE64_CHARS`
- 解码后的图片字节不能超过 `FACE_MAX_IMAGE_BYTES`
- OpenCV 解码后的像素总数不能超过 `FACE_MAX_IMAGE_PIXELS`

文件上传和 Base64 输入共用同一套字节和像素校验，避免不同入口出现不同资源消耗边界。

### 5.2 图像颜色空间
整个系统默认使用 **BGR 图像**。  
不要随手改成 RGB 再送进 InsightFace。

### 5.3 GPU / CPU 理解
- 默认推理设备是 CPU，避免 Windows 工作站启动时主动占用 GPU
- 需要 GPU 推理时设置 `FACE_USE_GPU=1`
- `FACE_FORCE_CPU=1` 优先级最高，会覆盖 `FACE_USE_GPU=1`
- provider 可见，不等于实际稳定跑在 GPU 上
- 判断要结合：provider、启动日志、接口耗时

### 5.4 V1.0 运行保护

V1.0 增加了生产类运行保护：

- `FACE_ENV=production` 时必须配置 `FACE_API_KEY`
- 环境变量中的数字配置会在启动时校验
- `FACE_DB_PATH` 所在目录必须可写
- `FACE_CORS_ORIGINS` 用于配置允许跨域的前端来源
- `FACE_LOG_PATH` 控制日志落盘位置
- 请求日志会记录路由、状态码和耗时，但不记录 API Key、图片或 embedding

### 5.5 V1.1 现场安全能力

V1.1 增加现场安全可用能力：

- `terminal_id` 在注册和 face login 中必填，用于 audit、日志和现场排障。
- face login 默认启用活体检测；注册默认关闭，但可配置开启。
- 活体 challenge 持久化到 SQLite，避免多 worker 下内存状态不一致。
- challenge 与用途、`terminal_id` 和通过挑战时检测到的人脸特征绑定，一次性使用，60 秒有效。
- 控制台复用 `FACE_API_KEY`，不引入账号系统。
- 数据库恢复必须进入维护模式并二次确认。

### 5.6 环境口径
当前推荐：
- **conda 主路径**
- **venv 备选路径**

启动细节不要在这里重复看，回 `README.md`。

---

## 6. 数据流

### 6.1 基础链路
```text
Client / Frontend / Terminal
        ↓
FastAPI main.py
        ↓
decode_image_bytes / decode_base64
        ↓
FaceEngine.analyze
        ↓
InsightFace + ONNX Runtime
        ↓
FaceDB / SQLite
        ↓
structured response / audit / helper result
```

### 6.2 primitive 路径
```text
Base64 image
  ↓
/extract/base64
  ↓
decode + single-face check
  ↓
embedding + stable failure code
```

### 6.3 auth helper 路径
```text
Base64 image
  ↓
/auth/face-login
  ↓
single-face check
  ↓
search top-1 in local DB
  ↓
audit write
  ↓
helper judgment result
```

---

## 7. 存储设计

### 7.1 `faces` 表
用途：
- 底库主表

字段：
- `id`
- `user_id`
- `username`
- `embedding`
- `metadata`
- `created_at`

### 7.2 人脸库治理

注册人脸时会执行基础治理：

- 图片必须恰好一张脸
- `username` 不能为空
- 注册人脸必须达到最低检测置信度、人脸框面积和亮度要求
- `FACE_DUPLICATE_POLICY` 控制同一 `user_id` 重复注册策略：
  - `allow`：允许多条记录
  - `reject`：已有记录时拒绝
  - `replace`：先删除旧记录再注册新记录

### 7.3 搜索缓存

`FaceDB.search()` 会使用内存中的归一化 embedding 矩阵作为搜索缓存。

- SQLite 仍然是持久化来源
- 注册、删除、按 `user_id` 删除后会标记缓存失效
- 下一次搜索或缓存状态查询会重新加载缓存
- `/system/status` 会返回 `search_cache` 状态

### 7.4 `face_login_audit` 表
用途：
- 记录登录尝试
- 支撑 recent/summary
- 为后续阈值调优和排障留数据基础

### 7.5 embedding 存储方式
embedding 使用 `float32 BLOB`，不是 JSON 数组。

原因：
- 更省空间
- 更适合 NumPy 直接还原和计算

### 7.6 搜索策略
当前 `search()` 采用：
- 全表读取 embedding
- NumPy 矩阵化余弦相似度计算

优点：
- 简单
- 维护成本低
- 小中型底库足够快

局限：
- 底库规模再上去就会碰到瓶颈
- 后续如继续增长，考虑 Faiss / HNSW / 向量索引方案

---

## 8. 鉴权边界

### 永远公开
- `/health`

### 条件启用鉴权（兼容原有契约）
- `/detect`
- `/detect/base64`
- `/compare`
- `/faces/register`
- `/faces`
- `/faces/{face_id}`
- `/search`

### 强制显式鉴权
- `/extract/base64`
- `/system/status`
- `/config/effective`
- `/auth/face-login`
- `/audit/login/recent`
- `/audit/login/summary`

### 维护时最容易犯的错
不要为了“安全统一”直接把 legacy 业务接口全改成强制鉴权，除非你明确接受破坏原有契约。

---

## 9. 高风险改动点

以下改动风险最高：

1. `FaceEngine` 初始化方式
2. 图像颜色空间（BGR / RGB）
3. embedding 存储格式
4. `/extract/base64` 的受控边界
5. `/auth/face-login` 的业务边界
6. 1:N 搜索算法与底库规模匹配关系
7. 鉴权模式（条件鉴权 vs 强制鉴权）

---

## 10. 维护者排障顺序

推荐顺序：
1. 服务是否启动成功
2. `/health` 是否正常
3. `/docs` 是否可访问
4. provider 是否符合预期
5. 是否启用了 `FACE_API_KEY`
6. 图片是否能正常解码
7. 底库是否有数据
8. 审计里是否有失败记录
9. 当前请求是否属于多人脸 / 无人脸 / 脏底库记录场景

---

## 11. 当前已知问题

### 11.1 环境说明仍有双轨
- conda 是主路径
- venv 是备选

### 11.2 GPU 状态容易误判
provider 可见，不等于实际稳定跑在 GPU 上。

### 11.3 `test.html` 只是本地调试工具
- 写死 `http://localhost:8000`
- 没有 API Key 输入
- 不适合作为正式前端工程示例

### 11.4 认证能力仍然较轻
当前没有：
- 活体检测
- 防重放机制
- 更强的风控层

### 11.5 `/extract/base64` 有明确的受控边界
它返回 raw embedding，属于当前阶段**有意识接受的风险边界**。
不要把它当普通浏览器接口使用。

---

## 12. 后续建议

如果继续推进 phase-2，最值的方向是：

1. 更细的 audit summary
2. 更完整的安全收口（特别是 `/extract/base64`）
3. 配置层增强（可控写入、配置来源说明）
4. 文档继续去重和瘦身

---

## 13. 接手顺序建议

第一次接手时，按这个顺序：

1. `README.md` —— 先跑起来
2. `docs/usage/API_INTEGRATION.md` —— 看怎么联调
3. `main.py` —— 看接口与鉴权边界
4. `face_engine.py` —— 看模型初始化和 GPU / CPU 逻辑
5. `storage.py` —— 看底库和审计存储
6. `docs/releases/2026-05-27-phase-1-summary.md` —— 看当前阶段成果与风险边界
