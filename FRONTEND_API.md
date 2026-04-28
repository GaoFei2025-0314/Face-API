# 人脸识别 API 前端对接文档

> 后端基于 FastAPI + InsightFace + SQLite，运行于本地 Windows 工作站。

---

## 一、基础信息

| 项 | 值 |
|---|---|
| 默认地址 | `http://localhost:8000`（局域网访问改为后端机器 IP） |
| 协议 | HTTP / REST |
| 数据格式 | JSON + multipart/form-data |
| 跨域 | 已启用 CORS |
| 认证 | 默认无；若启用，需在请求头加 `X-API-Key: <密钥>` |

**交互式文档**：启动后端后访问 `http://localhost:8000/docs`

---

## 二、图片格式约定

**方式 A：文件上传**（multipart/form-data）
```javascript
const fd = new FormData();
fd.append("file", fileObject);
fetch("/detect", { method: "POST", body: fd });
```

**方式 B：Base64 字符串**
- 带 data URL 前缀：`"data:image/jpeg;base64,/9j/4AAQ..."` ✅
- 不带前缀：`"/9j/4AAQ..."` ✅

```javascript
function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
```

---

## 三、接口清单

### 3.1 健康检查 `GET /health`

```json
{ "status": "ok", "device": "GPU (CUDA)", "faces": 12 }
```

### 3.2 人脸检测（文件） `POST /detect`

```json
{
  "count": 2,
  "faces": [
    {
      "bbox": [120.5, 88.2, 340.1, 380.7],
      "det_score": 0.98,
      "landmarks": [[180, 200], [260, 200], [220, 240], [190, 290], [250, 290]],
      "gender": "M",
      "age": 28
    }
  ],
  "elapsed_ms": 42.3
}
```

### 3.3 人脸检测（Base64） `POST /detect/base64`

请求：`{ "image": "data:image/jpeg;base64,..." }`，返回同上。

### 3.4 1:1 比对 `POST /compare`

请求：
```json
{ "image1": "...", "image2": "...", "threshold": 0.5 }
```

返回：
```json
{ "similarity": 0.782, "threshold": 0.5, "is_same_person": true, "elapsed_ms": 88.1 }
```

### 3.5 注册人脸 `POST /faces/register`

请求：
```json
{
  "name": "张三",
  "image": "...",
  "metadata": { "department": "研发部" }
}
```

返回：
```json
{ "id": "550e8400-...", "name": "张三", "message": "注册成功" }
```

**约束**：图片必须只有一张人脸，否则 400。

### 3.6 列出底库 `GET /faces`

```json
{
  "count": 2,
  "faces": [
    { "id": "...", "name": "张三", "metadata": {}, "created_at": "2026-04-27 10:23:15" }
  ]
}
```

### 3.7 删除人脸 `DELETE /faces/{face_id}`

```json
{ "deleted": "550e8400-..." }
```

### 3.8 1:N 搜索 `POST /search`

请求：
```json
{ "image": "...", "top_k": 5, "threshold": 0.5 }
```

返回：
```json
{
  "query_face_count": 1,
  "threshold": 0.5,
  "matches": [
    { "id": "...", "name": "张三", "similarity": 0.823, "metadata": {} }
  ],
  "elapsed_ms": 45.6
}
```

---

## 四、阈值参考

| 范围 | 判定 |
|---|---|
| ≥ 0.60 | 基本确定同人 |
| 0.45 ~ 0.60 | 可能同人，需结合业务 |
| < 0.45 | 通常不是同人 |

---

## 五、错误响应

```json
{ "detail": "错误描述" }
```

| HTTP 状态码 | 场景 |
|---|---|
| 400 | 图片无法解码 / 未检测到人脸 / 注册时多人 |
| 401 | 未提供或错误的 X-API-Key（启用鉴权时） |
| 404 | 资源不存在 |
| 422 | 请求体格式错误 |

---

## 六、对接代码

### 6.1 原生 fetch

```javascript
const API_BASE = "http://localhost:8000";
const API_KEY = ""; // 后端启用鉴权时填

async function request(path, options = {}) {
  options.headers = {
    ...(options.headers || {}),
    ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
  };
  const res = await fetch(API_BASE + path, options);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "请求失败");
  return data;
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export const faceAPI = {
  health: () => request("/health"),

  detect: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return request("/detect", { method: "POST", body: fd });
  },

  compare: async (file1, file2, threshold = 0.5) => {
    const [image1, image2] = await Promise.all([fileToBase64(file1), fileToBase64(file2)]);
    return request("/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image1, image2, threshold }),
    });
  },

  register: async (name, file, metadata = {}) => {
    const image = await fileToBase64(file);
    return request("/faces/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, image, metadata }),
    });
  },

  list: () => request("/faces"),
  delete: (id) => request(`/faces/${id}`, { method: "DELETE" }),

  search: async (file, top_k = 5, threshold = 0.5) => {
    const image = await fileToBase64(file);
    return request("/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image, top_k, threshold }),
    });
  },
};
```

### 6.2 Next.js API Route 代理

```javascript
// app/api/face/[...path]/route.js
const BACKEND = "http://localhost:8000";
const API_KEY = process.env.FACE_API_KEY || "";

export async function POST(request, { params }) {
  const path = params.path.join("/");
  const body = await request.text();
  const res = await fetch(`${BACKEND}/${path}`, {
    method: "POST",
    headers: {
      "Content-Type": request.headers.get("content-type") || "application/json",
      ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
    },
    body,
  });
  return new Response(await res.text(), {
    status: res.status,
    headers: { "Content-Type": res.headers.get("content-type") || "application/json" },
  });
}
```

---

## 七、TypeScript 类型

```typescript
export interface FaceInfo {
  bbox: [number, number, number, number];
  det_score: number;
  landmarks: number[][] | null;
  gender: "M" | "F";
  age: number;
}

export interface DetectResp {
  count: number;
  faces: FaceInfo[];
  elapsed_ms: number;
}

export interface CompareResp {
  similarity: number;
  threshold: number;
  is_same_person: boolean;
  elapsed_ms: number;
}

export interface MatchItem {
  id: string;
  name: string;
  similarity: number;
  metadata: Record<string, any>;
}

export interface SearchResp {
  query_face_count: number;
  threshold: number;
  matches: MatchItem[];
  elapsed_ms: number;
}

export interface RegisteredFace {
  id: string;
  name: string;
  metadata: Record<string, any>;
  created_at: string;
}
```

---

## 八、性能参考（后端：i9-7940X + GTX 1080 Ti）

| 接口 | 耗时 |
|---|---|
| `/detect` | 30-50ms |
| `/compare` | 60-100ms |
| `/search`（底库 1k） | 35-55ms |
| `/search`（底库 10k） | 50-70ms |

建议前端仍设 30 秒超时，并对图片做客户端压缩到 1000px 以内。
