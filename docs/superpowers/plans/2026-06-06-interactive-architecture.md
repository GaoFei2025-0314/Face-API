# Interactive Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a polished, offline, interactive `architecture.html` page that explains the face_api architecture through an SVG graph, role views, flow highlighting, and node details.

**Architecture:** Keep the feature as one static root-level HTML file with embedded CSS, JavaScript, and SVG rendering. Use structured JavaScript data for nodes, edges, roles, and flows so future architecture changes mostly update data instead of rendering logic. Update documentation entry points so the interactive page becomes part of the project maintenance workflow.

**Tech Stack:** Native HTML, CSS, JavaScript, SVG, existing Markdown documentation, PowerShell verification commands.

---

## File Structure

- Create: `architecture.html`
  - Single offline page.
  - Owns visual layout, graph data, SVG rendering, pan/zoom, node dragging, role switching, flow highlighting, and node detail panel.
- Modify: `README.md`
  - Add `architecture.html` as the quickest visual architecture entry.
- Modify: `docs/01_document_index.md`
  - Add `architecture.html` under "想看架构".
- Modify: `docs/05_architecture/01_architecture.md`
  - Explain the relationship between the written architecture doc, static SVG, and interactive page.
- Modify: `AGENTS.md`
  - Extend documentation coupling rules: architecture changes must check `architecture.html`.
- No backend files change.
- No database files change.
- No dependency files change.

## Task 1: Create Static Page Shell And Visual Layout

**Files:**
- Create: `architecture.html`

- [ ] **Step 1: Create the page skeleton**

Create `architecture.html` with this structure:

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>face_api 交互式架构图</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #08111f;
      --panel: #101b2e;
      --panel-strong: #15233a;
      --line: #2a3f5f;
      --text: #e7edf7;
      --muted: #91a2ba;
      --api: #4da3ff;
      --engine: #44d18d;
      --page: #b58cff;
      --ops: #ffb55c;
      --data: #38d6d6;
      --docs: #a8b3c7;
      --risk: #ff6370;
      --active: #ffe082;
      --shadow: 0 18px 60px rgba(0, 0, 0, 0.35);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      overflow: hidden;
      background:
        radial-gradient(circle at 25% 15%, rgba(77, 163, 255, 0.14), transparent 30%),
        radial-gradient(circle at 75% 10%, rgba(68, 209, 141, 0.10), transparent 26%),
        linear-gradient(135deg, #08111f 0%, #0b1424 54%, #101827 100%);
      color: var(--text);
      font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
    }

    .app {
      display: grid;
      grid-template-columns: 280px minmax(520px, 1fr) 360px;
      height: 100vh;
      min-width: 1080px;
    }

    .sidebar,
    .details {
      background: rgba(16, 27, 46, 0.88);
      border-color: rgba(255, 255, 255, 0.08);
      border-style: solid;
      backdrop-filter: blur(16px);
      overflow: auto;
    }

    .sidebar {
      border-width: 0 1px 0 0;
      padding: 22px;
    }

    .details {
      border-width: 0 0 0 1px;
      padding: 24px;
    }

    .brand {
      margin-bottom: 24px;
    }

    .brand h1 {
      margin: 0 0 8px;
      font-size: 24px;
      line-height: 1.2;
      letter-spacing: 0;
    }

    .brand p,
    .hint,
    .detail-muted {
      color: var(--muted);
      line-height: 1.65;
    }

    .control-group {
      margin: 24px 0;
    }

    .control-title {
      margin: 0 0 10px;
      color: var(--muted);
      font-size: 13px;
    }

    .button-list {
      display: grid;
      gap: 8px;
    }

    button {
      border: 1px solid rgba(255, 255, 255, 0.10);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.055);
      color: var(--text);
      cursor: pointer;
      font: inherit;
      text-align: left;
      transition: border-color 140ms ease, background 140ms ease, transform 140ms ease;
    }

    button:hover {
      border-color: rgba(255, 255, 255, 0.28);
      background: rgba(255, 255, 255, 0.095);
    }

    .choice {
      padding: 10px 12px;
    }

    .choice.active {
      border-color: rgba(255, 224, 130, 0.70);
      background: rgba(255, 224, 130, 0.13);
    }

    .toolbar {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .toolbar button {
      padding: 9px 11px;
      text-align: center;
    }

    .canvas-wrap {
      position: relative;
      min-width: 0;
      background-image:
        linear-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
      background-size: 32px 32px;
    }

    .canvas-header {
      position: absolute;
      top: 18px;
      left: 22px;
      z-index: 2;
      pointer-events: none;
    }

    .canvas-header h2 {
      margin: 0 0 8px;
      font-size: 18px;
      letter-spacing: 0;
    }

    .canvas-header p {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
    }

    svg {
      display: block;
      width: 100%;
      height: 100%;
      cursor: grab;
    }

    svg.dragging {
      cursor: grabbing;
    }

    .edge {
      stroke: rgba(145, 162, 186, 0.42);
      stroke-width: 2;
      fill: none;
      transition: stroke 160ms ease, opacity 160ms ease, stroke-width 160ms ease;
    }

    .edge.active {
      stroke: var(--active);
      stroke-width: 4;
      filter: drop-shadow(0 0 8px rgba(255, 224, 130, 0.65));
    }

    .edge.dimmed,
    .node.dimmed {
      opacity: 0.22;
    }

    .node {
      cursor: pointer;
      transition: opacity 160ms ease, filter 160ms ease;
    }

    .node rect {
      rx: 8;
      ry: 8;
      stroke-width: 1.5;
      filter: drop-shadow(0 10px 22px rgba(0, 0, 0, 0.32));
    }

    .node.active rect {
      stroke: var(--active);
      stroke-width: 2.5;
      filter: drop-shadow(0 0 14px rgba(255, 224, 130, 0.58));
    }

    .node text {
      fill: var(--text);
      font-size: 13px;
      pointer-events: none;
    }

    .node .subtitle {
      fill: var(--muted);
      font-size: 11px;
    }

    .details h2 {
      margin: 0 0 8px;
      font-size: 22px;
      letter-spacing: 0;
    }

    .tag {
      display: inline-flex;
      align-items: center;
      margin: 8px 8px 8px 0;
      padding: 5px 8px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.08);
      color: var(--muted);
      font-size: 12px;
    }

    .detail-section {
      margin-top: 22px;
    }

    .detail-section h3 {
      margin: 0 0 10px;
      font-size: 14px;
      color: var(--text);
    }

    .detail-section ul {
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      line-height: 1.75;
    }

    .detail-section code {
      color: #d7e6ff;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 4px;
      padding: 1px 4px;
    }
  </style>
</head>
<body>
  <main class="app">
    <aside class="sidebar">
      <section class="brand">
        <h1>face_api 架构图</h1>
        <p>用一张可交互图谱讲清楚本地人脸识别 REST API 的边界、流程、运行和文档入口。</p>
      </section>

      <section class="control-group">
        <h2 class="control-title">角色视图</h2>
        <div class="button-list" id="roleButtons"></div>
      </section>

      <section class="control-group">
        <h2 class="control-title">流程高亮</h2>
        <div class="button-list" id="flowButtons"></div>
      </section>

      <section class="control-group">
        <h2 class="control-title">操作</h2>
        <div class="toolbar">
          <button type="button" id="resetView">复位视图</button>
          <button type="button" id="clearFocus">清除高亮</button>
        </div>
      </section>

      <p class="hint">滚轮缩放，拖动画布平移，拖拽节点调整位置，点击节点查看说明。</p>
    </aside>

    <section class="canvas-wrap">
      <div class="canvas-header">
        <h2 id="viewTitle">新同事视图</h2>
        <p id="viewSubtitle">先理解系统边界和主链路。</p>
      </div>
      <svg id="graph" role="img" aria-label="face_api interactive architecture graph">
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(145, 162, 186, 0.72)"></path>
          </marker>
        </defs>
        <g id="viewport">
          <g id="edges"></g>
          <g id="nodes"></g>
        </g>
      </svg>
    </section>

    <aside class="details" id="details"></aside>
  </main>

  <script>
    // Task 2 will fill the data and rendering logic.
  </script>
</body>
</html>
```

- [ ] **Step 2: Open the page locally**

Run:

```powershell
Start-Process "H:\AI_test\face_api\architecture.html"
```

Expected:

- Browser opens a dark three-column page.
- Left controls are visible.
- Center area has the grid background.
- Right panel is empty until Task 2 adds data.
- No network access is required.

- [ ] **Step 3: Commit the shell**

Run:

```powershell
git add -- architecture.html
git commit -m "docs: add interactive architecture page shell"
```

Expected:

- Commit succeeds.

## Task 2: Add Graph Data And SVG Rendering

**Files:**
- Modify: `architecture.html`

- [ ] **Step 1: Replace the placeholder script with graph data**

Replace the placeholder script body with data definitions. Keep this exact shape so later tasks can add behavior without changing the data contract:

```javascript
const nodeTypes = {
  user: { label: "使用者", color: "#7aa2ff", fill: "rgba(122, 162, 255, 0.16)" },
  page: { label: "页面入口", color: "#b58cff", fill: "rgba(181, 140, 255, 0.16)" },
  api: { label: "API 层", color: "#4da3ff", fill: "rgba(77, 163, 255, 0.16)" },
  engine: { label: "识别推理", color: "#44d18d", fill: "rgba(68, 209, 141, 0.16)" },
  data: { label: "数据层", color: "#38d6d6", fill: "rgba(56, 214, 214, 0.15)" },
  ops: { label: "运维层", color: "#ffb55c", fill: "rgba(255, 181, 92, 0.16)" },
  docs: { label: "文档", color: "#a8b3c7", fill: "rgba(168, 179, 199, 0.14)" },
  risk: { label: "安全边界", color: "#ff6370", fill: "rgba(255, 99, 112, 0.14)" }
};

const nodes = [
  {
    id: "overview",
    type: "docs",
    x: 520,
    y: 80,
    title: "face_api 总览",
    subtitle: "本地人脸识别 REST API",
    summary: "face_api 是运行在 Windows 工作站上的人脸识别模块底座，负责检测、比对、搜索、人脸库和轻量认证辅助。",
    inputs: ["图片上传或 Base64 图片", "配置项和启动环境变量"],
    outputs: ["识别结果", "匹配用户信息", "运行状态", "审计记录"],
    links: ["README.md", "docs/01_document_index.md", "docs/02_product/01_prd.md"],
    notes: ["它不是完整登录平台，不签发 token 或 session。"]
  },
  {
    id: "frontend",
    type: "user",
    x: 90,
    y: 220,
    title: "前端 / 摄像头",
    subtitle: "采集图片",
    summary: "前端负责摄像头采集、用户交互和把图片交给受控调用方。",
    inputs: ["摄像头画面", "用户点击注册或登录"],
    outputs: ["图片文件或 Base64 字符串"],
    links: ["camera-integration.html", "test.html", "docs/04_usage/02_frontend_business_integration.md"],
    notes: ["正式前端不应该直接暴露 face_api 的 X-API-Key。"]
  },
  {
    id: "backend",
    type: "user",
    x: 90,
    y: 390,
    title: "业务后端",
    subtitle: "代理调用",
    summary: "业务后端保存用户主表，代理调用 face_api，并在登录成功后签发自己的业务 token。",
    inputs: ["前端提交的图片", "业务用户信息"],
    outputs: ["业务登录态", "用户资料"],
    links: ["docs/04_usage/01_api_integration.md", "docs/04_usage/02_frontend_business_integration.md"],
    notes: ["face_api 只返回 user_id 和 username，不维护业务权限体系。"]
  },
  {
    id: "pages",
    type: "page",
    x: 310,
    y: 220,
    title: "HTML 页面入口",
    subtitle: "test / camera / admin",
    summary: "项目保留多个静态 HTML 页面用于调试、摄像头验收和运维观察。",
    inputs: ["浏览器访问", "API 地址和 API Key"],
    outputs: ["接口请求", "验收结果", "运维观察信息"],
    links: ["test.html", "camera-integration.html", "admin.html"],
    notes: ["这些页面是轻量工具，不改造成前端框架。"]
  },
  {
    id: "fastapi",
    type: "api",
    x: 560,
    y: 260,
    title: "FastAPI main.py",
    subtitle: "REST API 入口",
    summary: "main.py 定义路由、请求模型、鉴权、CORS、图片解析、错误响应，并调用 FaceEngine 和 FaceDB。",
    inputs: ["HTTP 请求", "上传文件", "Base64 JSON"],
    outputs: ["JSON 响应", "HTTPException detail"],
    links: ["main.py", "docs/04_usage/01_api_integration.md", "http://localhost:8000/docs"],
    notes: ["不要在请求处理函数里新建 FaceEngine。"]
  },
  {
    id: "auth",
    type: "risk",
    x: 560,
    y: 430,
    title: "X-API-Key / CORS",
    subtitle: "访问边界",
    summary: "FACE_API_KEY 设置后，受保护接口必须传入 X-API-Key。CORS 控制允许访问的前端来源。",
    inputs: ["FACE_API_KEY", "FACE_CORS_ORIGINS", "X-API-Key 请求头"],
    outputs: ["允许请求", "401 鉴权失败", "跨域控制"],
    links: ["README.md", "docs/03_deployment/01_runbook.md", "AGENTS.md"],
    notes: ["X-API-Key 是服务密钥，不是用户密码。/health 不加鉴权。"]
  },
  {
    id: "engine",
    type: "engine",
    x: 820,
    y: 260,
    title: "FaceEngine",
    subtitle: "检测与特征提取",
    summary: "face_engine.py 封装 InsightFace 和 ONNX Runtime，输出人脸框、质量信息和 512 维 embedding。",
    inputs: ["OpenCV BGR 图片", "FACE_MODEL", "FACE_DET_SIZE", "FACE_USE_GPU", "FACE_FORCE_CPU"],
    outputs: ["bbox", "det_score", "landmarks", "embedding", "gender", "age"],
    links: ["face_engine.py", "docs/05_architecture/01_architecture.md"],
    notes: ["Windows 工作站默认 CPU，需要 GPU 时通过环境变量切换。"]
  },
  {
    id: "models",
    type: "engine",
    x: 1080,
    y: 260,
    title: "InsightFace / ONNX",
    subtitle: "buffalo_l 模型",
    summary: "InsightFace 下载并加载 buffalo_l 模型，ONNX Runtime 执行 CPU 或 GPU provider。",
    inputs: ["模型文件", "ONNX Runtime provider"],
    outputs: ["检测、关键点、识别向量"],
    links: ["requirements.txt", "requirements-cpu.txt", "docs/03_deployment/01_runbook.md"],
    notes: ["不要同时安装 onnxruntime 和 onnxruntime-gpu。"]
  },
  {
    id: "sqlite",
    type: "data",
    x: 820,
    y: 460,
    title: "SQLite FaceDB",
    subtitle: "faces.db",
    summary: "storage.py 管理人脸底库、embedding、metadata 和登录审计记录。",
    inputs: ["人脸 embedding", "username", "user_id", "metadata", "audit 事件"],
    outputs: ["人脸列表", "搜索结果", "审计汇总"],
    links: ["storage.py", "docs/06_performance/01_performance_scale.md"],
    notes: ["embedding 以 float32 BLOB 存储，不返回给前端。"]
  },
  {
    id: "ops",
    type: "ops",
    x: 310,
    y: 590,
    title: "Windows 运维脚本",
    subtitle: "run / prod / service",
    summary: "脚本负责本地启动、生产启动、服务安装、定时任务和停止排障。",
    inputs: ["环境变量", "conda 环境", "端口配置"],
    outputs: ["Uvicorn 服务", "日志", "后台进程"],
    links: ["run.bat", "run-prod.bat", "scripts/install-nssm-service.ps1", "scripts/install-task-scheduler.ps1"],
    notes: ["生产启动要校验端口、日志和 API Key。"]
  },
  {
    id: "health",
    type: "ops",
    x: 560,
    y: 610,
    title: "健康检查 / 监控",
    subtitle: "/health / logs",
    summary: "运维通过 /health、日志、Swagger 和 admin 页面确认服务是否正常。",
    inputs: ["GET /health", "日志文件", "admin 页面请求"],
    outputs: ["运行状态", "device", "faces", "错误定位线索"],
    links: ["docs/03_deployment/01_runbook.md", "admin.html"],
    notes: ["/health 始终公开，便于基础监控。"]
  },
  {
    id: "docs",
    type: "docs",
    x: 820,
    y: 650,
    title: "文档 / specs",
    subtitle: "开发和交付依据",
    summary: "文档入口、PRD、季度计划、runbook、API 集成文档和 specs 共同约束项目演进。",
    inputs: ["需求", "版本计划", "验收记录"],
    outputs: ["开发边界", "交付说明", "后续计划"],
    links: ["docs/01_document_index.md", "docs/02_product/02_quarterly_plan.md", "specs/README.md"],
    notes: ["不知道看哪里时，先看 docs/01_document_index.md。"]
  }
];

const edges = [
  { id: "frontend-pages", from: "frontend", to: "pages", label: "打开页面", flows: ["register", "login", "search"] },
  { id: "frontend-backend", from: "frontend", to: "backend", label: "提交图片", flows: ["register", "login"] },
  { id: "backend-fastapi", from: "backend", to: "fastapi", label: "代理调用 API", flows: ["register", "login", "search"] },
  { id: "pages-fastapi", from: "pages", to: "fastapi", label: "本机联调", flows: ["register", "login", "search"] },
  { id: "fastapi-auth", from: "fastapi", to: "auth", label: "鉴权 / CORS", flows: ["register", "login", "search"] },
  { id: "fastapi-engine", from: "fastapi", to: "engine", label: "图片识别", flows: ["register", "login", "search"] },
  { id: "engine-models", from: "engine", to: "models", label: "模型推理", flows: ["register", "login", "search"] },
  { id: "fastapi-sqlite", from: "fastapi", to: "sqlite", label: "写入 / 搜索", flows: ["register", "login", "search", "backup"] },
  { id: "ops-fastapi", from: "ops", to: "fastapi", label: "启动服务", flows: ["startup"] },
  { id: "ops-health", from: "ops", to: "health", label: "检查状态", flows: ["startup"] },
  { id: "health-fastapi", from: "health", to: "fastapi", label: "GET /health", flows: ["startup"] },
  { id: "ops-sqlite", from: "ops", to: "sqlite", label: "备份恢复", flows: ["backup"] },
  { id: "docs-overview", from: "docs", to: "overview", label: "解释边界", flows: [] }
];
```

- [ ] **Step 2: Add render helpers below the data**

Append this code after the data:

```javascript
const graph = document.getElementById("graph");
const viewport = document.getElementById("viewport");
const edgeLayer = document.getElementById("edges");
const nodeLayer = document.getElementById("nodes");
const details = document.getElementById("details");

const state = {
  selectedNodeId: "overview",
  activeRole: "newcomer",
  activeFlow: "",
  transform: { x: 0, y: 0, scale: 1 },
  draggingCanvas: false,
  draggingNodeId: "",
  dragStart: { x: 0, y: 0 },
  moved: false
};

function byId(id) {
  return nodes.find((node) => node.id === id);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function updateTransform() {
  viewport.setAttribute(
    "transform",
    `translate(${state.transform.x} ${state.transform.y}) scale(${state.transform.scale})`
  );
}

function centerOf(node) {
  return { x: node.x + 92, y: node.y + 34 };
}

function isNodeActive(nodeId) {
  if (!state.activeFlow) {
    return false;
  }
  return edges.some((edge) => edge.flows.includes(state.activeFlow) && (edge.from === nodeId || edge.to === nodeId));
}

function isEdgeActive(edge) {
  return Boolean(state.activeFlow && edge.flows.includes(state.activeFlow));
}

function renderEdges() {
  edgeLayer.innerHTML = edges.map((edge) => {
    const from = centerOf(byId(edge.from));
    const to = centerOf(byId(edge.to));
    const active = isEdgeActive(edge);
    const dimmed = state.activeFlow && !active;
    return `
      <path
        class="edge${active ? " active" : ""}${dimmed ? " dimmed" : ""}"
        data-edge-id="${escapeHtml(edge.id)}"
        d="M ${from.x} ${from.y} C ${(from.x + to.x) / 2} ${from.y}, ${(from.x + to.x) / 2} ${to.y}, ${to.x} ${to.y}"
        marker-end="url(#arrow)"
      ></path>
    `;
  }).join("");
}

function renderNodes() {
  nodeLayer.innerHTML = nodes.map((node) => {
    const type = nodeTypes[node.type];
    const active = state.selectedNodeId === node.id || isNodeActive(node.id);
    const dimmed = state.activeFlow && !active;
    return `
      <g class="node${active ? " active" : ""}${dimmed ? " dimmed" : ""}" data-node-id="${escapeHtml(node.id)}" transform="translate(${node.x} ${node.y})">
        <rect width="184" height="68" fill="${type.fill}" stroke="${type.color}"></rect>
        <text x="16" y="27">${escapeHtml(node.title)}</text>
        <text class="subtitle" x="16" y="49">${escapeHtml(node.subtitle)}</text>
      </g>
    `;
  }).join("");
}

function list(items) {
  return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderDetails() {
  const node = byId(state.selectedNodeId) || byId("overview");
  const type = nodeTypes[node.type];
  details.innerHTML = `
    <h2>${escapeHtml(node.title)}</h2>
    <p class="detail-muted">${escapeHtml(node.summary)}</p>
    <span class="tag" style="border: 1px solid ${type.color}; color: ${type.color};">${escapeHtml(type.label)}</span>
    <section class="detail-section">
      <h3>输入</h3>
      ${list(node.inputs)}
    </section>
    <section class="detail-section">
      <h3>输出</h3>
      ${list(node.outputs)}
    </section>
    <section class="detail-section">
      <h3>关联文件 / 文档</h3>
      ${list(node.links)}
    </section>
    <section class="detail-section">
      <h3>注意事项</h3>
      ${list(node.notes)}
    </section>
  `;
}

function renderGraph() {
  renderEdges();
  renderNodes();
  renderDetails();
}

updateTransform();
renderGraph();
```

- [ ] **Step 3: Verify initial rendering**

Run:

```powershell
Start-Process "H:\AI_test\face_api\architecture.html"
```

Expected:

- Nodes and curved edges render.
- The right panel shows "face_api 总览".
- No browser console syntax error appears.

- [ ] **Step 4: Commit graph rendering**

Run:

```powershell
git add -- architecture.html
git commit -m "docs: render interactive architecture graph"
```

Expected:

- Commit succeeds.

## Task 3: Add Role Switching, Flow Highlighting, Pan, Zoom, And Drag

**Files:**
- Modify: `architecture.html`

- [ ] **Step 1: Add role and flow data after `edges`**

```javascript
const roles = {
  newcomer: {
    label: "新同事",
    title: "新同事视图",
    subtitle: "先理解系统边界和主链路。",
    focusNode: "overview"
  },
  frontend: {
    label: "前端 / 业务后端",
    title: "前端接入视图",
    subtitle: "重点看摄像头页面、接口、X-API-Key 和登录注册链路。",
    focusNode: "frontend"
  },
  ops: {
    label: "运维人员",
    title: "运维视图",
    subtitle: "重点看启动方式、CPU/GPU 切换、健康检查、日志和备份。",
    focusNode: "ops"
  },
  owner: {
    label: "负责人",
    title: "负责人视图",
    subtitle: "重点看产品边界、版本路线、风险和文档入口。",
    focusNode: "docs"
  }
};

const flows = {
  register: { label: "注册流程", focusNode: "fastapi" },
  login: { label: "登录流程", focusNode: "auth" },
  search: { label: "搜索流程", focusNode: "sqlite" },
  startup: { label: "启动监控", focusNode: "health" },
  backup: { label: "备份恢复", focusNode: "sqlite" }
};
```

- [ ] **Step 2: Add control rendering functions after `renderGraph`**

```javascript
function renderControls() {
  const roleButtons = document.getElementById("roleButtons");
  const flowButtons = document.getElementById("flowButtons");

  roleButtons.innerHTML = Object.entries(roles).map(([id, role]) => `
    <button type="button" class="choice${state.activeRole === id ? " active" : ""}" data-role="${id}">
      ${escapeHtml(role.label)}
    </button>
  `).join("");

  flowButtons.innerHTML = Object.entries(flows).map(([id, flow]) => `
    <button type="button" class="choice${state.activeFlow === id ? " active" : ""}" data-flow="${id}">
      ${escapeHtml(flow.label)}
    </button>
  `).join("");

  const role = roles[state.activeRole];
  document.getElementById("viewTitle").textContent = role.title;
  document.getElementById("viewSubtitle").textContent = role.subtitle;
}

function setRole(roleId) {
  const role = roles[roleId];
  if (!role) {
    return;
  }
  state.activeRole = roleId;
  state.activeFlow = "";
  state.selectedNodeId = role.focusNode;
  renderControls();
  renderGraph();
}

function setFlow(flowId) {
  const flow = flows[flowId];
  if (!flow) {
    return;
  }
  state.activeFlow = flowId;
  state.selectedNodeId = flow.focusNode;
  renderControls();
  renderGraph();
}

function clearFocus() {
  state.activeFlow = "";
  state.selectedNodeId = roles[state.activeRole].focusNode;
  renderControls();
  renderGraph();
}

function resetView() {
  state.transform = { x: 0, y: 0, scale: 1 };
  updateTransform();
}
```

- [ ] **Step 3: Add event handling after the control functions**

```javascript
function clientPoint(event) {
  const rect = graph.getBoundingClientRect();
  return {
    x: (event.clientX - rect.left - state.transform.x) / state.transform.scale,
    y: (event.clientY - rect.top - state.transform.y) / state.transform.scale
  };
}

document.getElementById("roleButtons").addEventListener("click", (event) => {
  const button = event.target.closest("[data-role]");
  if (button) {
    setRole(button.dataset.role);
  }
});

document.getElementById("flowButtons").addEventListener("click", (event) => {
  const button = event.target.closest("[data-flow]");
  if (button) {
    setFlow(button.dataset.flow);
  }
});

document.getElementById("resetView").addEventListener("click", resetView);
document.getElementById("clearFocus").addEventListener("click", clearFocus);

graph.addEventListener("wheel", (event) => {
  event.preventDefault();
  const scaleDelta = event.deltaY > 0 ? 0.92 : 1.08;
  const nextScale = Math.min(1.8, Math.max(0.55, state.transform.scale * scaleDelta));
  const rect = graph.getBoundingClientRect();
  const mouseX = event.clientX - rect.left;
  const mouseY = event.clientY - rect.top;
  const worldX = (mouseX - state.transform.x) / state.transform.scale;
  const worldY = (mouseY - state.transform.y) / state.transform.scale;
  state.transform.x = mouseX - worldX * nextScale;
  state.transform.y = mouseY - worldY * nextScale;
  state.transform.scale = nextScale;
  updateTransform();
}, { passive: false });

graph.addEventListener("pointerdown", (event) => {
  const nodeElement = event.target.closest(".node");
  state.moved = false;
  graph.setPointerCapture(event.pointerId);
  graph.classList.add("dragging");

  if (nodeElement) {
    state.draggingNodeId = nodeElement.dataset.nodeId;
    const point = clientPoint(event);
    const node = byId(state.draggingNodeId);
    state.dragStart = { x: point.x - node.x, y: point.y - node.y };
    return;
  }

  state.draggingCanvas = true;
  state.dragStart = {
    x: event.clientX - state.transform.x,
    y: event.clientY - state.transform.y
  };
});

graph.addEventListener("pointermove", (event) => {
  if (state.draggingNodeId) {
    const point = clientPoint(event);
    const node = byId(state.draggingNodeId);
    node.x = point.x - state.dragStart.x;
    node.y = point.y - state.dragStart.y;
    state.moved = true;
    renderGraph();
    return;
  }

  if (state.draggingCanvas) {
    state.transform.x = event.clientX - state.dragStart.x;
    state.transform.y = event.clientY - state.dragStart.y;
    state.moved = true;
    updateTransform();
  }
});

graph.addEventListener("pointerup", (event) => {
  const nodeElement = event.target.closest(".node");
  graph.classList.remove("dragging");
  graph.releasePointerCapture(event.pointerId);

  if (nodeElement && !state.moved) {
    state.selectedNodeId = nodeElement.dataset.nodeId;
    renderGraph();
  }

  state.draggingNodeId = "";
  state.draggingCanvas = false;
});
```

- [ ] **Step 4: Update initialization**

Replace the final two lines:

```javascript
updateTransform();
renderGraph();
```

with:

```javascript
renderControls();
updateTransform();
renderGraph();
```

- [ ] **Step 5: Manual interaction verification**

Run:

```powershell
Start-Process "H:\AI_test\face_api\architecture.html"
```

Expected:

- Clicking each role changes the title and selected node.
- Clicking each flow highlights related lines and dims unrelated nodes.
- Mouse wheel zooms around the pointer.
- Dragging empty canvas pans the graph.
- Dragging a node moves it and connected lines follow it.
- "复位视图" resets pan and zoom.
- "清除高亮" removes flow highlighting.

- [ ] **Step 6: Commit interactions**

Run:

```powershell
git add -- architecture.html
git commit -m "docs: add architecture graph interactions"
```

Expected:

- Commit succeeds.

## Task 4: Polish Responsive Behavior And Offline Verification

**Files:**
- Modify: `architecture.html`

- [ ] **Step 1: Add responsive CSS near the end of the style block**

```css
    @media (max-width: 1180px) {
      body {
        overflow: auto;
      }

      .app {
        grid-template-columns: 250px minmax(520px, 1fr);
        grid-template-rows: 68vh auto;
        height: auto;
        min-height: 100vh;
      }

      .details {
        grid-column: 1 / -1;
        border-width: 1px 0 0;
        min-height: 320px;
      }
    }
```

- [ ] **Step 2: Add keyboard accessibility helper after event handlers**

```javascript
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    clearFocus();
  }
  if (event.key.toLowerCase() === "r") {
    resetView();
  }
});
```

- [ ] **Step 3: Run JavaScript syntax check**

Run:

```powershell
$html = Get-Content -Raw -Path "H:\AI_test\face_api\architecture.html"
$script = [regex]::Match($html, '(?s)<script>(.*?)</script>').Groups[1].Value
node -e "new Function(process.argv[1]); console.log('JS syntax OK')" $script
```

Expected:

```text
JS syntax OK
```

- [ ] **Step 4: Check that the page has no external dependencies**

Run:

```powershell
Select-String -Path "H:\AI_test\face_api\architecture.html" -Pattern "https?://|cdn|script src|link rel=.*stylesheet"
```

Expected:

- No matches.
- If `http://localhost:8000/docs` appears inside graph data, that is acceptable because it is displayed as text in the details panel, not loaded as a dependency.

- [ ] **Step 5: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected:

- No output.

- [ ] **Step 6: Commit polish**

Run:

```powershell
git add -- architecture.html
git commit -m "docs: polish interactive architecture page"
```

Expected:

- Commit succeeds.

## Task 5: Update Documentation Entry Points

**Files:**
- Modify: `README.md`
- Modify: `docs/01_document_index.md`
- Modify: `docs/05_architecture/01_architecture.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Update `README.md`**

Add this near the beginning, after the existing "不知道该看哪份文档" block:

```markdown
如果你想先用一张图理解整体架构，可以直接双击：

- `architecture.html`
```

- [ ] **Step 2: Update `docs/01_document_index.md`**

In section "5. 想看架构", change the "看：" list to include:

```markdown
- `architecture.html`
- `docs/05_architecture/01_architecture.md`
- `docs/05_architecture/02_face_api_rest_architecture.svg`
```

Add this under the "作用：" list:

```markdown
- `architecture.html`：交互式架构图，适合给同事演示整体结构、角色视图和关键流程。
```

- [ ] **Step 3: Update `docs/05_architecture/01_architecture.md`**

Add this after the opening "优先看这一份。" paragraph:

```markdown
如果你想用可视化方式快速讲解项目，可以先打开根目录：

- `architecture.html`

它是交互式架构图，适合演示角色视图、注册 / 登录 / 搜索 / 运维 / 备份恢复流程。本文负责更详细的文字解释，静态 SVG 负责一页式归档，`architecture.html` 负责现场讲解。
```

- [ ] **Step 4: Update `AGENTS.md`**

In the "Documentation coupling" section, extend the list with:

```markdown
- `architecture.html` for visual architecture, role views, flow diagrams, and architecture walkthrough changes.
```

Add this sentence after the list:

```markdown
When module boundaries, route groups, startup scripts, runtime configuration, data storage, or documentation structure change, check whether `architecture.html` needs to be updated.
```

- [ ] **Step 5: Verify documentation references**

Run:

```powershell
Select-String -Path "H:\AI_test\face_api\README.md","H:\AI_test\face_api\docs\01_document_index.md","H:\AI_test\face_api\docs\05_architecture\01_architecture.md","H:\AI_test\face_api\AGENTS.md" -Pattern "architecture.html"
```

Expected:

- Each of the four files has at least one match.

- [ ] **Step 6: Commit documentation updates**

Run:

```powershell
git add -- README.md docs/01_document_index.md docs/05_architecture/01_architecture.md AGENTS.md
git commit -m "docs: link interactive architecture page"
```

Expected:

- Commit succeeds.

## Task 6: Final Verification And Handoff

**Files:**
- Verify: `architecture.html`
- Verify: `README.md`
- Verify: `docs/01_document_index.md`
- Verify: `docs/05_architecture/01_architecture.md`
- Verify: `AGENTS.md`

- [ ] **Step 1: Run final JavaScript syntax check**

Run:

```powershell
$html = Get-Content -Raw -Path "H:\AI_test\face_api\architecture.html"
$script = [regex]::Match($html, '(?s)<script>(.*?)</script>').Groups[1].Value
node -e "new Function(process.argv[1]); console.log('JS syntax OK')" $script
```

Expected:

```text
JS syntax OK
```

- [ ] **Step 2: Run final external dependency check**

Run:

```powershell
Select-String -Path "H:\AI_test\face_api\architecture.html" -Pattern "cdn|script src|link rel=.*stylesheet"
```

Expected:

- No matches.

- [ ] **Step 3: Run final whitespace check**

Run:

```powershell
git diff --check
```

Expected:

- No output.

- [ ] **Step 4: Open final page**

Run:

```powershell
Start-Process "H:\AI_test\face_api\architecture.html"
```

Expected:

- The page opens directly from the file system.
- 4 role buttons are visible and usable.
- 5 flow buttons are visible and usable.
- Clicking nodes updates the right-side detail panel.
- Drag, pan, zoom, reset, and clear highlight work.
- The page looks suitable for projector demonstration.

- [ ] **Step 5: Inspect final git status**

Run:

```powershell
git status --short
```

Expected:

- Only unrelated pre-existing workspace changes remain, or the working tree is clean.
- No generated temp files were added.

- [ ] **Step 6: Final handoff**

Report:

- Created `architecture.html`.
- Updated README, document index, architecture doc, and AGENTS maintenance rule.
- Verification commands and results.
- Any remaining unrelated workspace changes.
