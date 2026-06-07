# Architecture Visual Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `architecture.html` from a usable interactive graph into a clearer, more polished presentation-grade architecture map.

**Architecture:** Keep the existing single-file HTML/CSS/JavaScript/SVG implementation. Improve visual clarity by adding lane data, larger module-card nodes, stronger primary edges, lane highlighting, compact side controls, and a more structured right-side explanation card while preserving all existing interactions.

**Tech Stack:** Native HTML, CSS, JavaScript, SVG, Chrome headless screenshot verification, existing unittest suite.

---

## File Structure

- Modify: `architecture.html`
  - Owns all visual layout, SVG graph rendering, node/edge data, interactions, and responsive behavior.
- Modify only if implementation changes page maintenance semantics: `docs/05_architecture/01_architecture.md`
  - Optional; not required for pure visual/style changes.
- Do not modify backend Python files.
- Do not add frontend dependencies.
- Do not add external image/font/icon assets.

## Task 1: Update Visual CSS Foundation

**Files:**
- Modify: `architecture.html`

- [ ] **Step 1: Replace core layout dimensions**

In the `<style>` block, adjust the main layout to reduce side-panel weight and release space to the graph:

```css
.app {
  display: grid;
  grid-template-columns: 260px minmax(620px, 1fr) 340px;
  height: 100vh;
  min-width: 1080px;
}
```

Expected:

- Left panel becomes narrower.
- Right panel becomes slightly narrower.
- Center graph gets more visual priority.

- [ ] **Step 2: Add lane, card, and edge CSS**

Add these CSS rules after the existing `.canvas-header p` rule:

```css
.lane {
  pointer-events: none;
}

.lane rect {
  fill: rgba(255, 255, 255, 0.025);
  stroke: rgba(255, 255, 255, 0.06);
  stroke-width: 1;
}

.lane.active rect {
  fill: rgba(255, 224, 130, 0.055);
  stroke: rgba(255, 224, 130, 0.20);
}

.lane text {
  fill: rgba(231, 237, 247, 0.42);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0;
}
```

Replace the existing `.edge`, `.edge.active`, `.edge.dimmed`, `.node`, `.node rect`, `.node.active rect`, `.node text`, and `.node .subtitle` rules with:

```css
.edge {
  stroke: rgba(145, 162, 186, 0.28);
  stroke-width: 2;
  fill: none;
  transition: stroke 160ms ease, opacity 160ms ease, stroke-width 160ms ease, filter 160ms ease;
}

.edge.primary {
  stroke: rgba(210, 224, 245, 0.48);
  stroke-width: 3;
}

.edge.active {
  stroke: var(--active);
  stroke-width: 5;
  filter: drop-shadow(0 0 10px rgba(255, 224, 130, 0.70));
}

.edge.dimmed,
.node.dimmed {
  opacity: 0.24;
}

.node {
  cursor: pointer;
  transition: opacity 160ms ease, filter 160ms ease;
}

.node rect.card {
  rx: 8;
  ry: 8;
  stroke-width: 1.6;
  filter: drop-shadow(0 14px 26px rgba(0, 0, 0, 0.30));
}

.node rect.accent {
  rx: 8;
  ry: 8;
}

.node.active rect.card {
  stroke: var(--active);
  stroke-width: 2.4;
  filter: drop-shadow(0 0 16px rgba(255, 224, 130, 0.52));
}

.node:hover rect.card {
  filter: drop-shadow(0 0 12px rgba(255, 255, 255, 0.16));
}

.node text {
  fill: var(--text);
  pointer-events: none;
}

.node .type-label {
  fill: rgba(231, 237, 247, 0.62);
  font-size: 10px;
  font-weight: 700;
}

.node .title {
  fill: var(--text);
  font-size: 15px;
  font-weight: 700;
}

.node.core .title {
  font-size: 16px;
}

.node .subtitle {
  fill: rgba(231, 237, 247, 0.70);
  font-size: 12px;
}

.node .file-label {
  fill: rgba(145, 162, 186, 0.78);
  font-size: 10px;
}
```

- [ ] **Step 3: Compact side controls**

Change `.sidebar` padding from `22px` to:

```css
padding: 20px;
```

Change `.brand` and `.control-group` spacing:

```css
.brand {
  margin-bottom: 18px;
}

.control-group {
  margin: 20px 0;
}
```

Change `.choice` padding:

```css
.choice {
  padding: 9px 11px;
}
```

- [ ] **Step 4: Verify CSS syntax manually**

Run:

```powershell
git diff --check -- architecture.html
```

Expected:

- No output.

## Task 2: Add Lane Data And Reposition Nodes

**Files:**
- Modify: `architecture.html`

- [ ] **Step 1: Add lane data before `nodeTypes`**

Inside the `<script>` block, before `const nodeTypes = {`, add:

```javascript
const lanes = [
  { id: "users", label: "使用者", y: 92, height: 116 },
  { id: "pages", label: "页面入口", y: 222, height: 116 },
  { id: "api", label: "API 层", y: 352, height: 126 },
  { id: "engine-data", label: "识别与数据", y: 492, height: 126 },
  { id: "ops-docs", label: "运维与文档", y: 632, height: 126 }
];
```

- [ ] **Step 2: Update node data fields**

For every object in `nodes`, add these fields:

```javascript
lane: "users",
size: "normal",
fileLabel: "README.md",
talkTrack: "演示时用它说明这个模块为什么存在。"
```

Use these exact values per node:

| Node | lane | size | fileLabel | talkTrack |
| --- | --- | --- | --- | --- |
| `overview` | `users` | `normal` | `README / PRD` | `先用它说明 face_api 是本地人脸识别模块底座，不是完整登录平台。` |
| `frontend` | `users` | `normal` | `camera-integration.html` | `讲前端只负责采集图片和交互，正式密钥应放在业务后端。` |
| `backend` | `users` | `normal` | `业务系统` | `讲业务后端负责用户主表、token 和权限，face_api 只做识别辅助。` |
| `pages` | `pages` | `normal` | `test / camera / admin` | `讲这些页面是调试、现场验收和运维观察工具。` |
| `fastapi` | `api` | `core` | `main.py` | `这是请求入口和编排中心，所有识别能力都从这里进入。` |
| `auth` | `api` | `normal` | `FACE_API_KEY / CORS` | `讲清楚 X-API-Key 是服务密钥，不是用户登录密码。` |
| `engine` | `engine-data` | `core` | `face_engine.py` | `这是识别核心，负责检测、人脸质量和 512 维 embedding。` |
| `models` | `engine-data` | `normal` | `buffalo_l / ONNX` | `讲模型和 provider，解释 CPU 默认、GPU 可切换。` |
| `sqlite` | `engine-data` | `core` | `storage.py / faces.db` | `这是本地人脸库和审计数据的持久化位置。` |
| `ops` | `ops-docs` | `normal` | `run-prod / scripts` | `讲 Windows 工作站如何启动、守护和维护服务。` |
| `health` | `ops-docs` | `normal` | `/health / logs` | `讲服务起来后如何确认它健康，以及出问题去哪看。` |
| `docs` | `ops-docs` | `normal` | `docs / specs` | `讲需求、计划、交付和后续维护都从文档入口开始。` |

- [ ] **Step 3: Reposition nodes**

Replace each node's `x` and `y` with:

| Node | x | y |
| --- | ---: | ---: |
| `overview` | 560 | 108 |
| `frontend` | 110 | 108 |
| `backend` | 340 | 108 |
| `pages` | 220 | 246 |
| `fastapi` | 520 | 372 |
| `auth` | 790 | 372 |
| `engine` | 520 | 514 |
| `models` | 790 | 514 |
| `sqlite` | 1060 | 514 |
| `ops` | 220 | 654 |
| `health` | 520 | 654 |
| `docs` | 820 | 654 |

- [ ] **Step 4: Add edge kind**

For every edge in `edges`, add `kind`.

Use `kind: "primary"` for:

- `frontend-pages`
- `frontend-backend`
- `backend-fastapi`
- `pages-fastapi`
- `fastapi-engine`
- `engine-models`
- `fastapi-sqlite`

Use `kind: "secondary"` for the remaining edges.

- [ ] **Step 5: Run JavaScript syntax check**

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

## Task 3: Render Lanes And Module Card Nodes

**Files:**
- Modify: `architecture.html`

- [ ] **Step 1: Add lane SVG group**

In the SVG viewport, change:

```html
<g id="edges"></g>
<g id="nodes"></g>
```

to:

```html
<g id="lanes"></g>
<g id="edges"></g>
<g id="nodes"></g>
```

After:

```javascript
const edgeLayer = document.getElementById("edges");
```

add:

```javascript
const laneLayer = document.getElementById("lanes");
```

- [ ] **Step 2: Add size helpers after `typeOf`**

```javascript
function sizeOf(node) {
  return node.size === "core"
    ? { width: 240, height: 106 }
    : { width: 210, height: 92 };
}

function activeLaneIds() {
  if (!state.activeFlow) {
    return new Set();
  }
  const ids = new Set();
  edges.forEach((edge) => {
    if (!edge.flows.includes(state.activeFlow)) {
      return;
    }
    const from = byId(edge.from);
    const to = byId(edge.to);
    if (from) ids.add(from.lane);
    if (to) ids.add(to.lane);
  });
  return ids;
}
```

- [ ] **Step 3: Update `centerOf`**

Replace `centerOf(node)` with:

```javascript
function centerOf(node) {
  const size = sizeOf(node);
  return { x: node.x + size.width / 2, y: node.y + size.height / 2 };
}
```

- [ ] **Step 4: Add `renderLanes` before `renderEdges`**

```javascript
function renderLanes() {
  const active = activeLaneIds();
  laneLayer.innerHTML = lanes.map((lane) => `
    <g class="lane${active.has(lane.id) ? " active" : ""}">
      <rect x="54" y="${lane.y}" width="1212" height="${lane.height}" rx="10" ry="10"></rect>
      <text x="72" y="${lane.y + 25}">${escapeHtml(lane.label)}</text>
    </g>
  `).join("");
}
```

- [ ] **Step 5: Update `renderEdges` class**

In `renderEdges`, change the `class` expression to include edge kind:

```javascript
class="edge ${edge.kind === "primary" ? "primary" : "secondary"}${active ? " active" : ""}${dimmed ? " dimmed" : ""}"
```

- [ ] **Step 6: Replace `renderNodes`**

Replace the current `renderNodes` with:

```javascript
function renderNodes() {
  nodeLayer.innerHTML = nodes.map((node) => {
    const type = typeOf(node);
    const size = sizeOf(node);
    const active = state.selectedNodeId === node.id || isNodeActive(node.id);
    const dimmed = state.activeFlow && !active;
    return `
      <g class="node ${node.size === "core" ? "core" : "normal"}${active ? " active" : ""}${dimmed ? " dimmed" : ""}" data-node-id="${escapeHtml(node.id)}" transform="translate(${node.x} ${node.y})">
        <rect class="card" width="${size.width}" height="${size.height}" fill="${type.fill}" stroke="${type.color}"></rect>
        <rect class="accent" width="${size.width}" height="4" fill="${type.color}"></rect>
        <text class="type-label" x="16" y="22">${escapeHtml(type.label)}</text>
        <text class="title" x="16" y="46">${escapeHtml(node.title)}</text>
        <text class="subtitle" x="16" y="68">${escapeHtml(node.subtitle)}</text>
        <text class="file-label" x="16" y="${size.height - 16}">${escapeHtml(node.fileLabel || "")}</text>
      </g>
    `;
  }).join("");
}
```

- [ ] **Step 7: Update `renderGraph`**

Replace:

```javascript
function renderGraph() {
  renderEdges();
  renderNodes();
  renderDetails();
}
```

with:

```javascript
function renderGraph() {
  renderLanes();
  renderEdges();
  renderNodes();
  renderDetails();
}
```

- [ ] **Step 8: Run syntax and diff checks**

Run:

```powershell
$html = Get-Content -Raw -Path "H:\AI_test\face_api\architecture.html"
$script = [regex]::Match($html, '(?s)<script>(.*?)</script>').Groups[1].Value
node -e "new Function(process.argv[1]); console.log('JS syntax OK')" $script
git diff --check -- architecture.html
```

Expected:

- `JS syntax OK`
- No `git diff --check` output.

## Task 4: Upgrade Right Detail Panel

**Files:**
- Modify: `architecture.html`

- [ ] **Step 1: Add detail panel CSS**

After `.tag` CSS, add:

```css
.detail-summary {
  margin: 14px 0 0;
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.045);
}

.detail-summary strong {
  display: block;
  margin-bottom: 6px;
  color: var(--text);
  font-size: 13px;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.detail-box {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.035);
}
```

- [ ] **Step 2: Add `listCompact` after `list`**

```javascript
function listCompact(items) {
  return `<ul>${items.slice(0, 3).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}
```

- [ ] **Step 3: Replace `renderDetails` body**

Inside `renderDetails`, replace `details.innerHTML = ...` with:

```javascript
details.innerHTML = `
  <h2>${escapeHtml(node.title)}</h2>
  <span class="tag" style="border: 1px solid ${type.color}; color: ${type.color};">${escapeHtml(type.label)}</span>
  <section class="detail-summary">
    <strong>模块定位</strong>
    <p class="detail-muted">${escapeHtml(node.summary)}</p>
  </section>
  <section class="detail-summary">
    <strong>为什么重要</strong>
    <p class="detail-muted">${escapeHtml(node.talkTrack || "演示时用它说明当前模块在系统里的职责。")}</p>
  </section>
  <section class="detail-section detail-grid">
    <div class="detail-box">
      <h3>输入</h3>
      ${listCompact(node.inputs)}
    </div>
    <div class="detail-box">
      <h3>输出</h3>
      ${listCompact(node.outputs)}
    </div>
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
```

- [ ] **Step 4: Verify details update after node click**

Run syntax check:

```powershell
$html = Get-Content -Raw -Path "H:\AI_test\face_api\architecture.html"
$script = [regex]::Match($html, '(?s)<script>(.*?)</script>').Groups[1].Value
node -e "new Function(process.argv[1]); console.log('JS syntax OK')" $script
```

Expected:

- `JS syntax OK`

## Task 5: Visual Screenshot Verification

**Files:**
- Verify: `architecture.html`

- [ ] **Step 1: Run final static checks**

```powershell
$html = Get-Content -Raw -Path "H:\AI_test\face_api\architecture.html"
$script = [regex]::Match($html, '(?s)<script>(.*?)</script>').Groups[1].Value
node -e "new Function(process.argv[1]); console.log('JS syntax OK')" $script
Select-String -Path "H:\AI_test\face_api\architecture.html" -Pattern "cdn|script src|link rel=.*stylesheet|import |require\(|fetch\("
git diff --check
```

Expected:

- `JS syntax OK`
- No external dependency matches.
- No `git diff --check` output.

- [ ] **Step 2: Capture desktop screenshot**

```powershell
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$out = "H:\AI_test\face_api\architecture-upgrade-desktop.png"
Remove-Item -LiteralPath $out -Force -ErrorAction SilentlyContinue
& $chrome --headless=new --disable-gpu --window-size=1440,900 --screenshot=$out "file:///H:/AI_test/face_api/architecture.html"
Get-Item -LiteralPath $out | Select-Object FullName,Length
```

Expected:

- Screenshot file exists.
- File length is greater than 20 KB.
- Visual inspection shows lanes, larger module cards, and clear main chain.

- [ ] **Step 3: Capture narrow screenshot**

```powershell
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$out = "H:\AI_test\face_api\architecture-upgrade-mobile.png"
Remove-Item -LiteralPath $out -Force -ErrorAction SilentlyContinue
& $chrome --headless=new --disable-gpu --window-size=420,900 --screenshot=$out "file:///H:/AI_test/face_api/architecture.html"
Get-Item -LiteralPath $out | Select-Object FullName,Length
```

Expected:

- Screenshot file exists.
- File length is greater than 20 KB.
- Visual inspection shows content is readable and not horizontally crushed.

- [ ] **Step 4: Remove temporary screenshots**

```powershell
Remove-Item -LiteralPath "H:\AI_test\face_api\architecture-upgrade-desktop.png","H:\AI_test\face_api\architecture-upgrade-mobile.png" -Force
git status --short
```

Expected:

- Screenshot files are removed.
- Only intended source files remain modified.

- [ ] **Step 5: Run unit tests**

```powershell
D:\anaconda3\envs\face_api\python.exe -m unittest discover -s tests -v
```

Expected:

- All tests pass.

## Task 6: Commit And Final Review

**Files:**
- Modify: `architecture.html`
- Optional modify: `docs/05_architecture/01_architecture.md`

- [ ] **Step 1: Inspect final diff**

```powershell
git diff -- architecture.html docs/05_architecture/01_architecture.md
```

Expected:

- Diff only includes visual upgrade and optional page-maintenance wording.
- No backend files changed.

- [ ] **Step 2: Commit**

```powershell
git add -- architecture.html docs/05_architecture/01_architecture.md
git commit -m "docs: improve interactive architecture visual clarity"
```

Expected:

- Commit succeeds.

- [ ] **Step 3: Final status**

```powershell
git status --short
```

Expected:

- Working tree is clean.
