# Code Review Report — face_api V2.2

**日期**: 2026-06-17
**提交**: 4f00d8a — fix: harden v2.2 csv export review follow-up
**变更文件**:

- `acceptance.html`（1 处修复：escapeCsv 正则增加前导空白敏感）
- `tests/test_scripts_smoke.py`（1 处修复：冒烟测试断言从精确空白匹配改为语义匹配）
- `Coding Review/code-review-V2.2-2026-06-17-7918ef5.md`（上一轮审查报告归档）

---

## 概述

本提交是对上一轮代码审查（7918ef5）中 2 个 MEDIUM findings 的集中修复，无新增功能代码。变更范围极小（总共 2 行逻辑变更 + 测试断言重构），风险面低。

| 原 Finding | 修复方式 | 验证结果 |
|---|---|---|
| M1 — escapeCsv 对前导空白不敏感 | 正则 `/^[=+\-@]/` → `/^\s*[=+\-@]/` | ✅ 正确修复 |
| M2 — 冒烟测试与源码格式强耦合 | 单条精确空白匹配断言 → 3 条语义化 `assertIn` | ✅ 正确修复 |

---

## CRITICAL

无。

---

## HIGH

无。

---

## MEDIUM

无。

> 两个修复均正确且最小化。`escapeCsv` 新增的 `\s*` 覆盖空格、制表符等 JS `\s` 字符类全部成员，不会引入回归。冒烟测试从依赖 `\n        ` 精确缩进改为检测 `catch (error)` + `setText("serviceStatus"` + `服务检查失败` 三个语义 token 的组合存在，不再受 Prettier 等格式化工具影响。

---

## 安全检查清单

| 检查项 | 状态 | 说明 |
|---|---|---|
| CSV 公式注入 | ✅ 通过 | `escapeCsv` 正则已补齐 `\s*`，`" =SUM(…)"` 等前导空白后跟公式字符的字段可被 `'` 前缀阻断 |
| XSS（跨站脚本） | ✅ 通过 | 无新增 DOM 操作；CSV 输出全部走 `escapeCsv`，HTML 渲染走 `escapeHtml` |
| 硬编码密钥/密码 | ✅ 通过 | 无变更涉及密钥 |
| 命令注入 | ✅ 通过 | `downloadBlob` 使用浏览器 Blob API，无 shell 调用 |
| 路径遍历 | ✅ 通过 | 无文件路径操作变更 |
| 敏感数据泄露 | ✅ 通过 | `buildReport()` 和 `normalizeAttempt()` 的 `apiKey/image/frames: undefined` 剥离逻辑未变动 |
| 日志脱敏 | ✅ 通过 | 无变更涉及日志 |
| 外部依赖（CDN） | ✅ 通过 | 无新增外部依赖，`acceptance.html` 仍为零外部引用 |
| 浏览器存储泄露 | ✅ 通过 | 无 localStorage/sessionStorage/indexedDB 使用 |
| 异常处理一致性 | ✅ 通过 | `checkServiceBtn`、`startCameraBtn` 等 catch 块未变动，错误信息仍正确显示中文消息 |
| 测试覆盖 | ✅ 通过 | 冒烟测试断言已从脆弱的空白依赖改为语义匹配，覆盖不降低 |
