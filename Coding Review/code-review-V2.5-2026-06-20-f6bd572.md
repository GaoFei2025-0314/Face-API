# Code Review Report — face_api V2.5

- **日期**: 2026-06-20
- **Commit**: `f6bd572` — `docs: address v2.5 review follow-ups`
- **变更文件**:
  - `CLAUDE.md`
  - `docs/04_usage/06_general_integration_contract.md`
  - `docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md`
  - `specs/026-general-integration-service-baseline/plan.md`
  - `specs/026-general-integration-service-baseline/tasks.md`
  - `specs/ROADMAP-v2.5.md`

## 概述

本次提交是一次纯文档跟进提交，无代码变更。主要内容：路由分组补全、TLS 安全提示、路径可移植性修复、术语修正（去掉误导性的 V2.5.1–V2.5.5 子版本号）、CLAUDE.md 纳入 spec-kit 指针范围。整体质量良好，均为正向改进。

---

## CRITICAL

无。

---

## HIGH

无。

---

## MEDIUM

### M1 — `specs/ROADMAP-v2.5.md:5` — 状态标记与提交意图不一致

**问题**: 文件头部 `> 状态：已完成`，验收总则所有条目均为 `[x]`。但本提交正是 review 跟进修正（commit message 写的是 "address v2.5 review follow-ups"），说明在上一次提交标记"已完成"时仍有遗漏项。

**风险**: 状态标记与实际交付节奏脱节。后续如果再有 review 发现遗漏，会产生同样的"已完成 → 又修正"循环，降低状态标记的可信度。

**建议**: review 全部关闭后再将状态改为"已完成"，或 review 期间标记为"已提交 review 待关闭"。

### M2 — `specs/026-general-integration-service-baseline/plan.md:130-136` — `$scanTerms` 拼接写法缺少注释

**问题**: `$scanTerms` 使用字符串拼接 `('TB' + 'D')` 来避开 `Select-String` 对扫描词自身的匹配：

```powershell
$scanTerms = @(
  ('TB' + 'D')
  ('TO' + 'DO')
  ('待' + '定')
  ('占' + '位')
)
```

**风险**: 写法隐蔽。后续维护者如果不知道意图，可能把 `('TB' + 'D')` 改成 `'TBD'`，导致扫描脚本把自己匹配进去产生误报。

**建议**: 加一行注释说明这是防止自匹配，或用变量名如 `$antiSelfMatchScanTerms` 暗示意图。此问题在上一个提交就存在，本提交未引入但值得修正。

### M3 — `docs/04_usage/06_general_integration_contract.md:241-242` — `FACE_USE_GPU` 环境变量未在 CLAUDE.md 中登记

**问题**: 通用接入契约第 8 节新增了 `FACE_USE_GPU` 环境变量作为 GPU 开关：

```
set FACE_USE_GPU=1
```

但 `CLAUDE.md` 的环境变量表只列了 5 个变量（`FACE_MODEL`、`FACE_DET_SIZE`、`FACE_DB_PATH`、`FACE_FORCE_CPU`、`FACE_API_KEY`），没有 `FACE_USE_GPU`。本提交的 CLAUDE.md 变更也未补上。

**风险**: 运维人员和 agent 从 CLAUDE.md 查环境变量时会漏掉 `FACE_USE_GPU`，导致 GPU 启停排障信息不全。

**建议**: 在 CLAUDE.md 环境变量表中补上 `FACE_USE_GPU`，或确认该变量是否仍有效。如果已废弃，通用契约中也不应引用。

---

## 提交变更中的正向改进

以下是本次提交的积极变更，无需修改：

- **CLAUDE.md 路由分组补全**: 从 4 组扩展为 7 组，覆盖所有现有路由，agent 和开发者能更快定位端点。
- **受控终端直连 TLS 提示** (`06_general_integration_contract.md`): 明确跨不可信网络时应启用 HTTPS/TLS，防止 `X-API-Key` 和图片帧明文传输。这是一条有价值的安全补充。
- **验收基线数据外传警告** (`08_face_api_wms_capture_loop_baseline.md`): 明确验收记录不得外传到公开渠道，加强了运维数据保密意识。
- **Verification Plan 路径可移植性** (`plan.md`): 将绝对路径（`H:\AI_test\face_api\...`、`D:\anaconda3\envs\face_api\python.exe`）替换为基于 `Resolve-Path` 的相对路径和通用 `python` 命令，脚本不再绑定特定机器。
- **ROADMAP 术语修正**: 移除 V2.5.1–V2.5.5 子版本编号，改为"服务定位/接入模式/契约规则/运行基线/文档同步"五个交付范围。原来编号容易让人误以为有 5 次独立发布，修正后表达更准确。
- **CLAUDE.md 纳入 spec-kit 指针范围**: plan.md、tasks.md、风险缓解文本同步更新，确保 `/goal` 和 agent 能找到当前计划。

---

## 安全检查清单

| 检查项 | 结果 | 说明 |
|---|---|---|
| 硬编码密钥/密码 | 通过 | 无新增密钥 |
| 敏感信息泄露（路径、用户名、IP） | 通过 | 绝对路径已替换为相对路径，无敏感信息暴露 |
| XSS / 注入风险 | 不适用 | 纯文档提交 |
| 认证/鉴权逻辑修改 | 不适用 | 无代码变更 |
| SQL 注入 | 不适用 | 无代码变更 |
| 明文传输敏感数据 | 通过 | 新增 TLS 安全提示（正向） |
| 错误信息泄露 | 不适用 | 无代码变更 |
| 依赖引入或版本漂移 | 不适用 | 无代码变更 |
| API 契约变更 | 通过 | 明确 V2.5 不新增公开 API |
| 日志/audit 敏感数据写入 | 通过 | 验收基线明确禁止写入密钥和 embedding |

---

> **总结**: 纯文档提交，无 CRITICAL 或 HIGH 问题。3 个 MEDIUM 建议均为文档一致性和可维护性改进。变更整体质量好，正向改进明显。
