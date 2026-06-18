# Code Review Report — face_api V2.3

**日期**: 2026-06-17  
**Commit**: `60a9b1a` — `docs: plan wms capture loop baseline`  
**变更文件**:
- `docs/superpowers/plans/2026-06-17-face-api-wms-capture-loop-baseline.md`（新增，506 行）

---

## HIGH

### H1 — `cd /d` 在 PowerShell 中无效（第 491、494 行）

**问题**: 手动基线运行清单使用了 `cd /d`，这是 CMD 语法，PowerShell 不支持。执行到这两行时会直接报错，导致验收人员无法按清单启动服务。

```powershell
cd /d H:\AI_test\face_api          # 第 491 行 — 会报错
cd /d H:\AI_test\electron-wms\electron-wms  # 第 494 行 — 会报错
```

**修复**: 去掉 `/d`，PowerShell 的 `cd`（即 `Set-Location`）本身就能跨盘符切换。

```powershell
cd H:\AI_test\face_api
cd H:\AI_test\electron-wms\electron-wms
```

---

## MEDIUM

### M1 — 样例矩阵（9 类）与记录表（7 行）不一致（第 140–162 行）

**问题**: 第 4 节「样例矩阵」定义了 9 种样例类型，但第 5 节「单次样例记录表」只预置了 7 行，缺少以下 4 类：

- 真人弱光
- 真人侧脸或轻微遮挡
- 多人入镜
- 模糊抓拍

现场验收人员按模板填写时，需要手动补行，但模板没有任何提示说明。

**修复**: 在记录表中补全所有 9 类样例的预置行，或在表上方加一行说明「如需更多样例类型请自行追加行」。

### M2 — `event_id` 字段缺少填写说明（第 154 行）

**问题**: 记录表包含 `event_id` 列，但整篇文档没有解释这个字段的值从哪里获取、格式是什么。验收人员可能不知道该填什么，导致这一列在实操中被跳过。

**修复**: 在记录表上方补充一行说明，例如：

> `event_id` 取自 Face API 审计记录或 WMS 终端日志中的事件标识，用于关联单次抓拍/登录的算法结果与业务记录。如当前版本尚无 event_id，可暂填终端编号 + 序号。

### M3 — 跨仓库 git 操作缺少路径存在性校验（Task 2）

**问题**: Task 2 的 Step 1 用 `Get-ChildItem` 检查 WMS doc 目录，但如果 `H:\AI_test\electron-wms\electron-wms` 本身不存在，命令会直接失败，错误信息不够明确。

Task 1 有「neighboring records exist」的前置检查，Task 2 缺少对 WMS 仓库根路径的显式 `Test-Path`。

**修复**: 在 Task 2 Step 1 开头增加：

```powershell
Test-Path 'H:\AI_test\electron-wms\electron-wms'
```

### M4 — 硬编码绝对路径降低可移植性（全文）

**问题**: 所有路径均为 `H:\AI_test\...` 绝对路径。换一台机器或盘符变更时，整个计划文件需要批量替换路径才能执行。这虽然是一个面向特定工作站的计划，但路径出现次数过多（40+ 处），维护成本高。

**修复**: 计划开头定义一个路径变量约定，后续步骤引用变量。例如：

```markdown
> **路径约定**: `$FACE_API = 'H:\AI_test\face_api'`, `$WMS = 'H:\AI_test\electron-wms\electron-wms'`
```

这样后续命令改为 `cd $FACE_API` 等，路径变更时只需改一处。

---

## 安全性检查清单

| 检查项 | 状态 | 说明 |
|---|---|---|
| 硬编码密钥/密码/Token | 通过 | 无任何凭据泄露 |
| API Key 暴露 | 通过 | 文件中未出现 API Key |
| 数据库连接串暴露 | 通过 | 无连接串 |
| 内部 IP/域名泄露 | 通过 | 仅 `localhost`，属本地开发环境 |
| 敏感文件路径泄露 | 通过 | 路径均为开发/文档路径，非系统敏感路径 |
| 命令注入风险 | 通过 | 无用户可控输入拼接到命令中 |
| 不安全的 curl 调用 | 通过 | `curl http://localhost:8000/health` 仅本地回环 |
| 权限提升操作 | 通过 | 无 `sudo`/`runas` 操作 |
| 文件权限问题 | 通过 | 不涉及文件权限变更 |

---

## 总结

本次 commit 是一个纯文档计划文件，不涉及任何应用代码、API、数据库或运行时变更。**无 CRITICAL 问题**。

- 1 个 HIGH：`cd /d` 语法错误会导致验收人员无法按清单启动服务。
- 4 个 MEDIUM：模板完整性问题（样例行缺失、字段未说明）和跨仓库操作健壮性不足。

建议在计划执行前修复 H1，其余 MEDIUM 项可在执行过程中顺手修掉。
