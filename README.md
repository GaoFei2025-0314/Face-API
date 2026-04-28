# 人脸识别 API（实际运行版）

> 基于 InsightFace + FastAPI + SQLite，已在 i9-7940X + GTX 1080 Ti + Python 3.10.8 上跑通。
> 当前推理后端：**CPU**（GPU 模式需要额外装 CUDA Toolkit，详见第八节）。

---

## 一、环境状态

| 项 | 值 |
|---|---|
| 环境管理 | conda |
| 环境名 | `face_api` |
| Python | 3.10.8 |
| InsightFace | 0.7.3（用 cgohlke 的 Win64 预编译 wheel 装的） |
| ONNX Runtime | onnxruntime-gpu 1.19.2（实际跑 CPU） |
| NumPy | 1.26.4（已锁定 < 2.0） |
| 数据库 | SQLite（faces.db） |

---

## 二、日常启动（最常用）

### 方式 A：双击 run.bat

最简单。

### 方式 B：命令行

打开 Anaconda Prompt（或 cmd），执行：

```bash
cd /d H:\AI_test\face_api
conda activate face_api
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

启动成功的标志：

```
[FaceEngine] Available providers: ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']
[FaceEngine] Ready. Running on GPU (CUDA)
[FaceDB-SQLite] Ready at H:\AI_test\face_api\faces.db, N faces loaded
INFO:     Uvicorn running on http://0.0.0.0:8000
```

> **关于 `Running on GPU (CUDA)` 提示**：这只是基于 provider 列表的探测显示，**实际推理回落到 CPU**（因为 cuda dll 加载失败，看启动日志会有 `Applied providers: ['CPUExecutionProvider']` 字样）。要让 GPU 真正生效需要装 CUDA Toolkit，详见第八节。

---

## 三、停止服务

在 cmd 窗口按 `Ctrl + C`。

---

## 四、测试

服务跑起来后，三种方式都能测：

1. **浏览器打开 test.html** —— 最直观
2. **浏览器打开 http://localhost:8000/docs** —— Swagger 交互式文档
3. **curl 命令行** —— 见 FRONTEND_API.md

---

## 五、人脸库存放在哪

- 主库文件：`H:\AI_test\face_api\faces.db`
- WAL 日志：`faces.db-wal`（运行时存在，正常）
- 共享内存：`faces.db-shm`（运行时存在，正常）

**备份**：停止服务后直接复制 `faces.db` 即可。

**清空**：停止服务，删除 `faces.db`、`faces.db-wal`、`faces.db-shm` 三个文件，下次启动自动重建空库。

---

## 六、查看人脸库内容

不停止服务的情况下：

```bash
conda activate face_api
python -c "import sqlite3; conn=sqlite3.connect('faces.db'); rows=conn.execute('SELECT id, name, length(embedding), created_at FROM faces').fetchall(); [print(r) for r in rows]"
```

或者推荐用图形化工具：[DB Browser for SQLite](https://sqlitebrowser.org/)。

---

## 七、接口一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| POST | `/detect` | 人脸检测（文件） |
| POST | `/detect/base64` | 人脸检测（Base64） |
| POST | `/compare` | 1:1 比对 |
| POST | `/faces/register` | 注册人脸 |
| GET | `/faces` | 列出底库 |
| DELETE | `/faces/{id}` | 删除人脸 |
| POST | `/search` | 1:N 搜索 |

详细接口文档见 `FRONTEND_API.md` 或运行后访问 `/docs`。

---

## 八、让 GPU 真正生效（可选，性能提升 5-10 倍）

当前 CPU 推理：约 200-400ms/次。
GPU 模式可以降到：约 30-50ms/次。

需要装两个 NVIDIA 工具包：

### 1. 装 CUDA Toolkit 12.x

- 下载：<https://developer.nvidia.com/cuda-12-1-0-download-archive>
- 选 Windows → x86_64 → 10 → exe (local)
- 大小约 3GB
- 安装时可以**自定义路径到 D 盘**省 C 盘空间
- 装完会自动配好环境变量

### 2. 装 cuDNN 9.x for CUDA 12

- 下载：<https://developer.nvidia.com/cudnn>
- 需要注册 NVIDIA 账号
- 选 cuDNN v9.x for CUDA 12.x
- 大小约 700MB
- 解压后把 bin / lib / include 三个文件夹的内容**复制到 CUDA Toolkit 安装目录的对应文件夹**

### 3. 验证

```bash
conda activate face_api
python -c "import onnxruntime as ort; sess = ort.InferenceSession('C:/Users/Administrator/.insightface/models/buffalo_l/det_10g.onnx', providers=['CUDAExecutionProvider']); print('Active:', sess.get_providers())"
```

如果输出 `Active: ['CUDAExecutionProvider', 'CPUExecutionProvider']`（不是仅 CPU），说明 GPU 真的生效了。

### 4. 重启服务

按 Ctrl+C 停止当前服务，重新 run.bat。日志里 `Applied providers` 应该变成 `['CUDAExecutionProvider', ...]`。

---

## 九、常见问题

### Q1：不小心关了 cmd 窗口

服务停了，重新双击 run.bat 即可。底库数据会保留。

### Q2：报 "ModuleNotFoundError: No module named 'xxx'"

conda 环境没激活成功。检查命令行最前面是否有 `(face_api)`，没有就跑：

```bash
conda activate face_api
```

### Q3：GPU dll 加载失败的红色错误一直滚

这是当前 CPU 模式下的预期警告（每次推理都试图加载 GPU 但失败），**不影响功能**。如果觉得吵，装 CUDA Toolkit（第八节）让它真的能加载，错误就消失了。

### Q4：相似度比预期低

InsightFace 的相似度在 0.4-0.5 之间是"模糊地带"，不是 bug。提升相似度的方法：
- 用更标准的正面照（无侧脸、无遮挡、光线好）
- 同人不同时期/不同照片本身就会有差异
- 阈值可以根据实际情况调整（business 场景常用 0.45-0.55）

### Q5：想让局域网内其他电脑访问

启动命令已经是 `--host 0.0.0.0`，其他电脑用你这台电脑的 IP 访问即可：

```bash
ipconfig                # 查 IPv4 地址
```

让他们浏览器打开 `http://<你的IP>:8000/docs`。如果连不上，检查 Windows 防火墙是否放行 8000 端口。

---

## 十、目录结构（最终版）

```
H:\AI_test\face_api\
├── main.py                  # FastAPI 应用与路由
├── face_engine.py           # InsightFace 封装
├── storage.py               # SQLite 人脸库
├── requirements.txt         # 依赖清单（参考用，实际用 conda 装）
├── requirements-cpu.txt     # CPU 版备用
├── run.bat                  # 一键启动（conda 版）
├── test.html                # 浏览器测试页
├── README.md                # 本文档（启动指南）
├── FRONTEND_API.md          # 给前端的接口文档
├── HOW_TO_DELIVER.md        # 部署交付指南
├── CLAUDE.md                # 给 Claude Code 的项目说明
├── faces.db                 # SQLite 主库（运行后生成）
├── faces.db-wal             # WAL 日志（运行时存在）
├── faces.db-shm             # 共享内存索引（运行时存在）
└── __pycache__/             # Python 编译缓存（自动生成，可忽略）
```

注意：原来的 `setup.bat` 已经废弃（因为环境用 conda 不用 venv 了），删掉就行。
