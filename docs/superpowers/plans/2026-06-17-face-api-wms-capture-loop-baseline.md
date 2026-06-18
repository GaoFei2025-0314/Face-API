# Face API WMS Capture Loop Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first reusable Face API + Electron WMS intelligent capture acceptance baseline: a shared record template, WMS-side runbook, document index entry, and verification checklist.

**Architecture:** This first baseline is documentation and process infrastructure only. `face_api` remains the system of record for algorithm acceptance templates, while `electron-wms` gets the terminal-side runbook that explains camera, local face library, login, capture, and log collection steps. No backend, frontend, schema, API, or runtime behavior changes are included.

**Tech Stack:** Markdown documentation, existing `face_api` docs structure, existing `electron-wms` `doc/` structure, PowerShell, Git.

---

## Scope And Execution Notes

This plan implements the first "联动验收基线" from the approved design:

- Design document: `H:\AI_test\face_api\docs\superpowers\specs\2026-06-17-face-api-wms-capture-loop-design.md`
- Face API repo: `H:\AI_test\face_api`
- WMS repo: `H:\AI_test\electron-wms\electron-wms`

Path convention for commands:

```powershell
$FACE_API = 'H:\AI_test\face_api'
$WMS = 'H:\AI_test\electron-wms\electron-wms'
```

Current repo condition at plan creation:

- `face_api` has many unrelated modified and untracked files.
- The design document is already committed as `da69c1c`.
- Each task below must stage only the files named in that task.
- Do not use `git add .`.
- Do not modify application code in this baseline pass.

The implementation should produce two small documentation commits:

1. A `face_api` commit for the acceptance record template and index update.
2. An `electron-wms` commit for the WMS terminal runbook.

If the user asks to keep all docs in one repository, skip Task 2 and keep the WMS runbook content as a linked section in the Face API acceptance template instead.

## File Structure

Create in `face_api`:

- `docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md`
  - The reusable acceptance record template for linked Face API + WMS field checks.
  - Holds environment snapshot, sample matrix, API results, WMS observations, issue classification, and next actions.

Modify in `face_api`:

- `docs/01_document_index.md`
  - Add a link to the linked acceptance baseline under acceptance, field validation, or related operational documents.

Create in `electron-wms`:

- `doc/13-Face-API-WMS智能抓拍联动验收基线.md`
  - The WMS terminal-side runbook: startup checks, camera checks, local face library checks, capture/login flow, log collection, and issue evidence rules.

No code files are created or modified in this plan.

---

### Task 1: Create Face API Linked Acceptance Record Template

**Files:**
- Create: `H:\AI_test\face_api\docs\90_archive\04_acceptance\08_face_api_wms_capture_loop_baseline.md`

- [ ] **Step 1: Inspect neighboring acceptance records**

Run:

```powershell
Get-ChildItem 'H:\AI_test\face_api\docs\90_archive\04_acceptance'
Get-Content -LiteralPath 'H:\AI_test\face_api\docs\90_archive\04_acceptance\07_v2.3_acceptance_record.md' -TotalCount 180
```

Expected:

- The acceptance archive directory exists.
- Existing records use Chinese Markdown and versioned acceptance summaries.
- The new file number `08` is not already used.

- [ ] **Step 2: Create the linked baseline template**

Create `H:\AI_test\face_api\docs\90_archive\04_acceptance\08_face_api_wms_capture_loop_baseline.md` with:

```markdown
# Face API 与 WMS 智能抓拍联动验收基线

> 创建时间：2026-06-17
> 用途：记录 `face_api` 算法底座与 Electron WMS 智能抓拍/终端登录链路的一次完整联动验收
> 关联设计：`docs/superpowers/specs/2026-06-17-face-api-wms-capture-loop-design.md`

## 1. 验收目标

本记录用于验证一条真实现场链路：

```text
WMS 摄像头采集
-> Face API 检测 / 活体 / 登录辅助
-> WMS 终端提示或登录
-> 审计与日志回收
-> 问题分类
-> 下一轮改进项
```

验收重点不是单独证明某个接口能调用，而是证明算法底座、终端采集、业务提示和审计记录能够组成可复盘闭环。

## 2. 环境快照

| 项目 | 记录 |
|---|---|
| 验收日期 | 2026-06-17 |
| 验收人员 |  |
| 现场位置 |  |
| Face API 仓库路径 | `H:\AI_test\face_api` |
| Face API commit |  |
| Face API 版本 | V2.3 或当前运行版本 |
| Face API 启动方式 | `run.bat` / `uvicorn main:app --host 0.0.0.0 --port 8000 --reload` |
| Face API 地址 | `http://localhost:8000` |
| WMS 仓库路径 | `H:\AI_test\electron-wms\electron-wms` |
| WMS commit |  |
| WMS 启动方式 | `npm run dev` / packaged app |
| 终端编号 |  |
| 摄像头型号 |  |
| 网络状态 | 在线 / 弱网 / 离线 |
| 光照条件 | 正常 / 弱光 / 背光 / 强反光 |

## 3. 启动检查

| 检查项 | 命令或操作 | 期望结果 | 实际结果 | 结论 |
|---|---|---|---|---|
| Face API 健康检查 | `curl http://localhost:8000/health` | 返回 `status=ok` |  |  |
| Face API OpenAPI | 打开 `http://localhost:8000/docs` | Swagger 可访问 |  |  |
| Face API 配置 | `GET /config/effective` 或页面查看 | 可看到阈值、活体和防翻拍配置 |  |  |
| WMS 终端启动 | `npm run dev` 或打开安装包 | 主界面可打开 |  |  |
| 摄像头权限 | 打开抓拍、录制或人脸登录入口 | 可看到实时画面 |  |  |
| 本地人脸库 | WMS 运维入口或本地服务状态 | 至少 1 个测试用户为可用状态 |  |  |
| 审计记录 | Face API / WMS 审计入口 | 能看到最近记录或空列表 |  |  |

## 4. 样例矩阵

每类样例默认执行 3 次。真人正脸至少 2 次成功。翻拍类样例不得低风险静默成功。

| 样例类型 | 次数 | 操作说明 | 期望 |
|---|---:|---|---|
| 真人正脸 | 3 | 已注册测试用户正对摄像头 | 至少 2 次成功 |
| 真人弱光 | 3 | 降低环境光或背光 | 失败时要有可解释原因 |
| 真人侧脸或轻微遮挡 | 3 | 轻微偏转或遮挡 | 失败时要有可解释原因 |
| 打印照片 | 3 | 使用已注册用户打印照片 | 不得低风险静默成功 |
| 手机屏幕照片 | 3 | 手机显示已注册用户照片 | 不得低风险静默成功 |
| 电脑屏幕照片 | 3 | 电脑屏幕显示已注册用户照片 | 不得低风险静默成功 |
| 手机播放眨眼视频 | 3 | 手机播放已注册用户视频 | 不得低风险静默成功 |
| 多人入镜 | 3 | 两人以上进入画面 | 应提示多人或拒绝 |
| 模糊抓拍 | 3 | 快速晃动或失焦 | 应提示采集质量或识别失败 |

## 5. 单次样例记录表

`event_id` 取自 Face API 审计记录或 WMS 终端日志中的事件标识，用于关联单次抓拍、识别、登录或提交。如当前版本尚无 event_id，可暂填终端编号加序号。每类样例默认 3 次，下面先预置 9 类样例首行，实际执行时按次数追加对应行。

| 编号 | 样例类型 | 终端编号 | event_id | WMS 操作 | WMS 结果 | Face API 风险等级 | 相似度 | 错误码 / 原因 | 耗时 ms | 审计是否可查 | 结论 |
|---|---|---|---|---|---|---|---:|---|---:|---|---|
| 1 | 真人正脸 |  |  |  |  |  |  |  |  |  |  |
| 2 | 真人弱光 |  |  |  |  |  |  |  |  |  |  |
| 3 | 真人侧脸或轻微遮挡 |  |  |  |  |  |  |  |  |  |  |
| 4 | 打印照片 |  |  |  |  |  |  |  |  |  |  |
| 5 | 手机屏幕照片 |  |  |  |  |  |  |  |  |  |  |
| 6 | 电脑屏幕照片 |  |  |  |  |  |  |  |  |  |  |
| 7 | 手机播放眨眼视频 |  |  |  |  |  |  |  |  |  |  |
| 8 | 多人入镜 |  |  |  |  |  |  |  |  |  |  |
| 9 | 模糊抓拍 |  |  |  |  |  |  |  |  |  |  |

## 6. 问题分类表

| 问题编号 | 现象 | 证据来源 | 归因分类 | 处理建议 | 进入下一版本 |
|---|---|---|---|---|---|
| P1 |  | Face API 审计 / WMS 日志 / 现场样例 | 算法底座 / 终端采集 / 业务流程 |  | 是 / 否 |
| P2 |  | Face API 审计 / WMS 日志 / 现场样例 | 算法底座 / 终端采集 / 业务流程 |  | 是 / 否 |
| P3 |  | Face API 审计 / WMS 日志 / 现场样例 | 算法底座 / 终端采集 / 业务流程 |  | 是 / 否 |

归因规则：

- 算法底座：检测、特征、相似度、活体、防翻拍、错误码、审计字段。
- 终端采集：摄像头、权限、光照、角度、模糊、连续帧质量、Electron 主进程链路。
- 业务流程：用户底图、账号状态、token 换取、离线回退、页面提示和提交流程。

## 7. 验收结论

| 项目 | 结论 |
|---|---|
| 真人正脸是否达到 2/3 成功 |  |
| 翻拍样例是否避免低风险静默成功 |  |
| WMS 是否有可理解失败提示 |  |
| Face API 审计是否可追溯 |  |
| WMS 日志是否可追溯 |  |
| 问题是否完成三类归因 |  |
| 是否建议进入下一轮开发 |  |

## 8. 下一轮改进清单

| 优先级 | 改进项 | 所属项目 | 验收方式 |
|---|---|---|---|
| P0 |  | `face_api` / `electron-wms` |  |
| P1 |  | `face_api` / `electron-wms` |  |
| P2 |  | `face_api` / `electron-wms` |  |
```

- [ ] **Step 3: Verify the template file exists and has no red-flag placeholders**

Run:

```powershell
Test-Path 'H:\AI_test\face_api\docs\90_archive\04_acceptance\08_face_api_wms_capture_loop_baseline.md'
$scanTerms = @('TB' + 'D', 'TO' + 'DO', '待' + '定', '占' + '位')
Select-String -LiteralPath 'H:\AI_test\face_api\docs\90_archive\04_acceptance\08_face_api_wms_capture_loop_baseline.md' -Pattern $scanTerms -SimpleMatch
```

Expected:

- `Test-Path` returns `True`.
- `Select-String` returns no matches.

- [ ] **Step 4: Commit the Face API template**

Run:

```powershell
git -C 'H:\AI_test\face_api' status --short -- 'docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md'
git -C 'H:\AI_test\face_api' add -- 'docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md'
git -C 'H:\AI_test\face_api' commit -m "docs: add wms capture loop acceptance baseline" -- 'docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md'
```

Expected:

- The first command shows only the new baseline file.
- The commit includes only `docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md`.

---

### Task 2: Create WMS Terminal-Side Runbook

**Files:**
- Create: `H:\AI_test\electron-wms\electron-wms\doc\13-Face-API-WMS智能抓拍联动验收基线.md`

- [ ] **Step 1: Inspect WMS document naming and current face docs**

Run:

```powershell
Test-Path 'H:\AI_test\electron-wms\electron-wms'
Get-ChildItem 'H:\AI_test\electron-wms\electron-wms\doc'
Get-Content -LiteralPath 'H:\AI_test\electron-wms\electron-wms\doc\12-人脸算法功能介绍与后续迭代规划.md' -TotalCount 160
Get-Content -LiteralPath 'H:\AI_test\electron-wms\electron-wms\doc\09-终端人脸识别登录方案设计.md' -TotalCount 120
```

Expected:

- WMS 仓库路径存在；如果 `Test-Path` 返回 `False`，先确认仓库位置再继续。
- Existing WMS docs are numbered Chinese Markdown files.
- `13-Face-API-WMS智能抓拍联动验收基线.md` is not already present.

- [ ] **Step 2: Create the WMS runbook**

Create `H:\AI_test\electron-wms\electron-wms\doc\13-Face-API-WMS智能抓拍联动验收基线.md` with:

```markdown
# Face API 与 WMS 智能抓拍联动验收基线

> 创建时间：2026-06-17
> 用途：指导 WMS 终端侧完成摄像头采集、人脸登录、智能抓拍和日志回收的联动验收
> 对应 Face API 模板：`H:\AI_test\face_api\docs\90_archive\04_acceptance\08_face_api_wms_capture_loop_baseline.md`

## 1. 终端侧目标

WMS 终端侧负责证明现场业务链路成立：

```text
摄像头可用
-> 本地人脸库可用
-> 抓拍或登录入口可用
-> Face API 调用可追踪
-> 页面提示可理解
-> 日志可回收
```

这份基线不改 WMS 功能，只规定每次联动验收时终端侧应该怎么检查、记录和归因。

## 2. 启动前检查

| 检查项 | 操作 | 通过标准 |
|---|---|---|
| 代码版本 | `git -C H:\AI_test\electron-wms\electron-wms rev-parse --short HEAD` | 能记录当前 commit |
| 依赖状态 | `npm install` 已完成或安装包可运行 | 终端能启动 |
| 终端启动 | `npm run dev` 或打开安装包 | 主界面正常 |
| 摄像头权限 | 进入人脸登录、抓拍或视频录制入口 | 实时画面正常 |
| 本地用户 | 用户同步已完成 | 本地有测试用户 |
| 本地人脸库 | 人脸特征同步已完成 | 测试用户可用于本地匹配 |
| Face API 连通 | WMS 能访问 Face API 地址 | 调用无网络错误 |

## 3. 终端侧操作流程

1. 启动 Face API。
2. 启动 WMS 终端。
3. 确认摄像头画面稳定。
4. 确认本地测试用户和头像存在。
5. 执行本地人脸特征同步。
6. 使用真人正脸完成一次登录或识别。
7. 使用翻拍、弱光、模糊和多人样例重复测试。
8. 每次测试记录 WMS 页面提示、Face API 结果、WMS 日志和终端环境。
9. 将问题归入算法底座、终端采集或业务流程。

## 4. 日志与证据收集

| 证据 | 位置或入口 | 用途 |
|---|---|---|
| WMS 终端日志 | `H:\AI_test\electron-wms\electron-wms\logs` 或安装包日志目录 | 判断 Electron、IPC、服务调用问题 |
| Face API 审计 | Face API `/audit/login/recent` 或页面 | 判断算法结果、风险等级、相似度和失败原因 |
| 摄像头现场描述 | 验收记录表 | 解释弱光、背光、模糊和角度问题 |
| 本地人脸库状态 | WMS 运维入口或数据库状态 | 判断底图质量和同步问题 |
| 业务登录结果 | WMS 页面和后端 token 换取结果 | 判断认证链路问题 |

## 5. 问题归因规则

| 现象 | 优先检查 | 归因方向 |
|---|---|---|
| 摄像头没有画面 | 权限、设备占用、浏览器/Electron 权限 | 终端采集 |
| 真人清晰正脸仍失败 | 底图质量、相似度、阈值、Face API 审计 | 算法底座或业务底图 |
| 翻拍样例直接成功 | Face API 风险等级、中风险策略、连续帧质量 | 算法底座 |
| 页面只提示失败但无原因 | WMS 错误映射和提示语 | 业务流程 |
| Face API 成功但无法登录 | authCode、token 换取、用户状态、网络 | 业务流程 |
| WMS 很慢但 Face API 耗时正常 | 摄像头采集、前端压缩、IPC、主进程链路 | 终端采集 |
| Face API 耗时高 | CPU/GPU、模型、det_size、线程数 | 算法底座 |

## 6. 每次验收后必须输出

| 输出 | 写入位置 |
|---|---|
| 联动验收记录 | `H:\AI_test\face_api\docs\90_archive\04_acceptance\08_face_api_wms_capture_loop_baseline.md` 的副本或追加记录 |
| WMS 侧现象摘要 | 本文档同目录的阶段记录，或项目 issue |
| 问题分类表 | Face API 验收记录 |
| 下一轮改进项 | Face API Roadmap 或 WMS 需求文档 |

## 7. 不在本基线中做的事

- 不改 WMS 登录流程。
- 不改 Face API 接口。
- 不新增数据库表。
- 不保存现场原图或视频帧到文档。
- 不把一次现场结果直接当作最终算法结论。
```

- [ ] **Step 3: Verify the WMS runbook exists and has no red-flag placeholders**

Run:

```powershell
Test-Path 'H:\AI_test\electron-wms\electron-wms\doc\13-Face-API-WMS智能抓拍联动验收基线.md'
$scanTerms = @('TB' + 'D', 'TO' + 'DO', '待' + '定', '占' + '位')
Select-String -LiteralPath 'H:\AI_test\electron-wms\electron-wms\doc\13-Face-API-WMS智能抓拍联动验收基线.md' -Pattern $scanTerms -SimpleMatch
```

Expected:

- `Test-Path` returns `True`.
- `Select-String` returns no matches.

- [ ] **Step 4: Commit the WMS runbook**

Run:

```powershell
git -C 'H:\AI_test\electron-wms\electron-wms' status --short -- 'doc/13-Face-API-WMS智能抓拍联动验收基线.md'
git -C 'H:\AI_test\electron-wms\electron-wms' add -- 'doc/13-Face-API-WMS智能抓拍联动验收基线.md'
git -C 'H:\AI_test\electron-wms\electron-wms' commit -m "docs: add face api capture loop runbook" -- 'doc/13-Face-API-WMS智能抓拍联动验收基线.md'
```

Expected:

- The first command shows only the new WMS runbook.
- The commit includes only `doc/13-Face-API-WMS智能抓拍联动验收基线.md`.

---

### Task 3: Link the Baseline From the Face API Document Index

**Files:**
- Modify: `H:\AI_test\face_api\docs\01_document_index.md`

- [ ] **Step 1: Inspect the document index sections**

Run:

```powershell
Get-Content -LiteralPath 'H:\AI_test\face_api\docs\01_document_index.md'
```

Expected:

- The file contains a structured index of product, deployment, usage, architecture, and archive documents.
- There is an appropriate archive, acceptance, or operational section where the linked baseline can be listed.

- [ ] **Step 2: Add the linked baseline entry**

Modify `H:\AI_test\face_api\docs\01_document_index.md` by adding this entry under the most relevant acceptance/archive section:

```markdown
- `docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md`：Face API 与 Electron WMS 智能抓拍联动验收基线，记录环境快照、现场样例、审计回收、问题分类和下一轮改进项。
```

If the index uses a table instead of bullet entries, add the same content as one table row:

```markdown
| `docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md` | Face API 与 Electron WMS 智能抓拍联动验收基线，记录环境快照、现场样例、审计回收、问题分类和下一轮改进项。 |
```

- [ ] **Step 3: Verify the index link resolves**

Run:

```powershell
Select-String -LiteralPath 'H:\AI_test\face_api\docs\01_document_index.md' -Pattern '08_face_api_wms_capture_loop_baseline.md' -SimpleMatch
Test-Path 'H:\AI_test\face_api\docs\90_archive\04_acceptance\08_face_api_wms_capture_loop_baseline.md'
```

Expected:

- `Select-String` prints the new index entry.
- `Test-Path` returns `True`.

- [ ] **Step 4: Commit the index update**

Run:

```powershell
git -C 'H:\AI_test\face_api' status --short -- 'docs/01_document_index.md'
git -C 'H:\AI_test\face_api' add -- 'docs/01_document_index.md'
git -C 'H:\AI_test\face_api' commit -m "docs: link wms capture loop baseline" -- 'docs/01_document_index.md'
```

Expected:

- The commit includes only `docs/01_document_index.md`.

---

### Task 4: Perform Static Verification and Handoff

**Files:**
- Verify: `H:\AI_test\face_api\docs\90_archive\04_acceptance\08_face_api_wms_capture_loop_baseline.md`
- Verify: `H:\AI_test\face_api\docs\01_document_index.md`
- Verify: `H:\AI_test\electron-wms\electron-wms\doc\13-Face-API-WMS智能抓拍联动验收基线.md`

- [ ] **Step 1: Run placeholder scans**

Run:

```powershell
$scanTerms = @('TB' + 'D', 'TO' + 'DO', '待' + '定', '占' + '位')
Select-String -LiteralPath 'H:\AI_test\face_api\docs\90_archive\04_acceptance\08_face_api_wms_capture_loop_baseline.md' -Pattern $scanTerms -SimpleMatch
Select-String -LiteralPath 'H:\AI_test\face_api\docs\01_document_index.md' -Pattern $scanTerms -SimpleMatch
Select-String -LiteralPath 'H:\AI_test\electron-wms\electron-wms\doc\13-Face-API-WMS智能抓拍联动验收基线.md' -Pattern $scanTerms -SimpleMatch
```

Expected:

- All three commands return no matches.

- [ ] **Step 2: Confirm required links and paths**

Run:

```powershell
Test-Path 'H:\AI_test\face_api\docs\superpowers\specs\2026-06-17-face-api-wms-capture-loop-design.md'
Test-Path 'H:\AI_test\face_api\docs\90_archive\04_acceptance\08_face_api_wms_capture_loop_baseline.md'
Test-Path 'H:\AI_test\electron-wms\electron-wms\doc\13-Face-API-WMS智能抓拍联动验收基线.md'
Select-String -LiteralPath 'H:\AI_test\face_api\docs\01_document_index.md' -Pattern '08_face_api_wms_capture_loop_baseline.md' -SimpleMatch
```

Expected:

- The three `Test-Path` commands return `True`.
- The `Select-String` command prints the document index entry.

- [ ] **Step 3: Confirm no unintended staged files**

Run:

```powershell
git -C 'H:\AI_test\face_api' diff --cached --name-only
git -C 'H:\AI_test\electron-wms\electron-wms' diff --cached --name-only
```

Expected:

- Both commands return no output after the task commits.

- [ ] **Step 4: Prepare manual baseline run**

Use this command checklist when the user is ready to run the actual linked acceptance:

```powershell
Set-Location H:\AI_test\face_api
run.bat

curl http://localhost:8000/health

Set-Location H:\AI_test\electron-wms\electron-wms
npm run dev
```

Expected:

- Face API health returns `status=ok`.
- WMS opens and the terminal camera flow can be tested manually.
- Results are recorded in `docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md` or a dated copy derived from it.

Do not mark the real field baseline as passed until sample rows are filled with actual Face API and WMS evidence.
