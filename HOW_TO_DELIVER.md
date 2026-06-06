# 如何把 API 交付给前端

## TL;DR

后端启动后，发以下三样东西给前端同学即可：
1. 接口地址：`http://<后端机器IP>:8000`
2. Swagger 文档链接：`http://<后端机器IP>:8000/docs`
3. 附件 `docs/04_usage/01_api_integration.md`

生产类运行和交付排障优先看：

- `docs/03_deployment/01_runbook.md`

V1.1 运维控制台：

- `http://<后端机器IP>:8000/admin.html`
- 复用 `FACE_API_KEY`
- 恢复数据库前必须进入维护模式并二次确认

---

## 一、本机开发：前后端都在一台机器

启动后端：
```bash
run.bat
```

生产类运行不要长期使用 `--reload`，改用：

```bat
set FACE_API_KEY=your-secret
run-prod.bat
```

前端代码用：
```javascript
const API_BASE = "http://localhost:8000";
```

V1.1 起，注册和 face login 请求都必须带 `terminal_id`，用于 audit、日志和现场排障。

CORS 已开启，直接跨域调用即可。

---

## 二、局域网协作：前端在另一台电脑

### 1. 启动后端时绑定 0.0.0.0

`run.bat` 默认就是 `--host 0.0.0.0`，无需额外操作。

### 2. 查后端机器 IP

```bash
ipconfig
```
找 "IPv4 地址"，比如 `192.168.1.100`。

### 3. 前端用 IP 替代 localhost

```javascript
const API_BASE = "http://192.168.1.100:8000";
```

### 4. 防火墙放行

第一次启动 uvicorn 时 Windows 会弹窗问是否允许，点"允许访问"即可。

如果没弹或已拒绝：
- 控制面板 → Windows Defender 防火墙 → 高级设置 → 入站规则
- 新建规则 → 端口 → TCP 8000 → 允许连接

### 5. 前端测连通性

让前端浏览器打开 `http://192.168.1.100:8000/docs`，能看 Swagger 即成功。

---

## 三、部署到服务器

### 1. 传项目到服务器

git / scp / 打包上传都可。

### 2. 服务器上常驻

最简单的 nohup（不优雅但能跑）：
```bash
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 > face.log 2>&1 &
```

正式环境建议用 systemd 或 supervisor。

### 3. Nginx 反向代理（推荐）

让前端用域名而不是 IP+端口：

```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    # SSL 证书...

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
    }
}
```

### 4. 启用鉴权

设置环境变量：
```bash
export FACE_API_KEY="your-secret-key-2026"
```

或在 `run.bat` 里：
```batch
set FACE_API_KEY=your-secret-key-2026
```

启用后，所有业务接口（除 `/health`）都需要在请求头加：
```
X-API-Key: your-secret-key-2026
```

### 5. 收紧 CORS

打开 `main.py`，把：
```python
allow_origins=["*"]
```
改为生产允许的前端地址。

V1.0 以后也可以通过环境变量配置：

```bat
set FACE_CORS_ORIGINS=http://localhost:3000,http://192.168.1.100:3000
```

### 6. 健康检查脚本

```powershell
powershell -ExecutionPolicy Bypass -File scripts\health-check.ps1
```

### 7. 备份和恢复

备份：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\backup-db.ps1
```

恢复前先停止服务：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\restore-db.ps1 -BackupDir backups\20260605-120000
```

---

## 四、4 种文档使用方式

### A. Swagger UI（最直观）

访问 `/docs`，每个接口可以在线 "Try it out"。

### B. 导入 Postman

1. Postman → Import → Link
2. 粘贴 `http://your-host:8000/openapi.json`
3. 自动生成完整接口集合

### C. 导入 Apifox（国内推荐）

1. 新建项目 → 导入数据 → OpenAPI/Swagger
2. 填 `http://your-host:8000/openapi.json`
3. 后端改了能自动同步

### D. 自动生成 TypeScript 客户端

```bash
npm install -g @openapitools/openapi-generator-cli
openapi-generator-cli generate \
  -i http://your-host:8000/openapi.json \
  -g typescript-fetch \
  -o ./src/api-client
```

或更轻量：
- `openapi-typescript`（仅类型）
- `orval`（生成 React Query hooks）

---

## 五、常见问题

### Q1：前端报 CORS 错误

确认 `main.py` 里 CORSMiddleware 的 `allow_origins` 包含前端域名，重启后端。

### Q2：上传大图 413

Nginx 加 `client_max_body_size 20M;`。

### Q3：请求慢/超时

- 前端压缩图到 1000px 以内
- 前端超时设 30 秒
- 看返回的 `elapsed_ms` 字段定位是后端慢还是网络慢

### Q4：文档过期

OpenAPI 自动从代码生成，**不会过期**。这是 FastAPI 的核心优势。

### Q5：接口需要鉴权了，前端怎么办

```javascript
fetch(url, {
  headers: { "X-API-Key": "your-key" },
});
```

axios 在 interceptor 里统一加：
```javascript
axios.interceptors.request.use(config => {
  config.headers["X-API-Key"] = process.env.FACE_API_KEY;
  return config;
});
```

---

## 六、给前端的交付模板

> Hi，人脸识别 API 已就绪：
>
> **基础地址**：`http://192.168.1.100:8000`
>
> **交互式文档**：http://192.168.1.100:8000/docs
>
> **详细文档**：见附件 `docs/04_usage/01_api_integration.md`
>
> **TypeScript 类型**：文档第七章
>
> **现成调用代码**：文档第六章（fetch / Next.js Route）
>
> **是否需要鉴权**：当前 [无] / [需要，密钥见安全渠道]
>
> 有问题联系我。
