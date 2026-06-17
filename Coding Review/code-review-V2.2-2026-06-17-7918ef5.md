# Code Review Report — face_api V2.2

**日期**: 2026-06-17
**提交**: 7918ef5 — fix:address v2.2 code review hardening findings
**变更文件**:

- `Coding Review/code-review-V2.2-2026-06-17-0980a51.md`（新建，上一轮审查报告归档）
- `acceptance.html`（4 处 hardening）
- `main.py`（1 处 hardening）
- `tests/test_main_api.py`（新增 1 条单测）
- `tests/test_scripts_smoke.py`（新增 1 条冒烟测试）

---

## 概述

本提交是对上一轮代码审查（0980a51）全部 5 个 findings 的集中修复，外加 2 条回归测试。逐项验证结果如下：

| 原 Finding | 修复方式 | 验证结果 |
|---|---|---|
| H1 — CSV 公式注入 | `escapeCsv` 增加 `= + - @` 前缀检测，追加 `'` 前缀 | ✅ 正确修复 |
| H2 — checkServiceBtn 静默吞异常 | catch 分支改为 `setText` 显示错误信息 | ✅ 正确修复 |
| M1 — sanitize_log_payload 缺类型守卫 | 入口增加 `isinstance(payload, dict)` 检查，否则 `raise TypeError` | ✅ 正确修复 |
| M2 — onclick 内联事件处理器 | 改为 `data-sample-id` + 事件委托 | ✅ 正确修复 |
| M3 — challenge_id 边界值 | 改为 `liveness.challenge_id ?? challenge.challenge_id ?? null` 三级回退 | ✅ 正确修复 |

---

## CRITICAL

无。

---

## HIGH

无。

---

## MEDIUM

### M1 — `escapeCsv` 公式注入检测对前导空白不敏感

**文件**: `acceptance.html:420-427`

```javascript
function escapeCsv(value) {
  const text = String(value ?? "");
  const safeText = /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  if (/^[=+\-@]/.test(text)) {
    return `'${safeText}`;
  }
  return safeText;
}
```

正则 `/^[=+\-@]/` 从字符串起始位置匹配。如果某个字段值以空格开头后跟 `=`（如 `" =SUM(1,2)"`），检测会绕过，Excel / WPS 打开 CSV 时可能仍将单元格内容当作公式执行。

**风险面**: 极低。CSV 数据全部来自后端 API 返回值（`message`、`risk_reasons` 等），均由 `main.py` 中的 Python 常量或服务器端逻辑生成，不存在用户可控的公式注入入口。验收台运行在本地工作站内网。

**建议**: 可改为 `trim()` 后再检测，或改用 `/^\s*[=+\-@]/`。优先级不高，视防御纵深需求决定是否修：

```javascript
if (/^\s*[=+\-@]/.test(text)) {
```

---

### M2 — 冒烟测试 `test_acceptance_page_hardens_reviewed_frontend_edges` 与源码格式强耦合

**文件**: `tests/test_scripts_smoke.py:348-350`

```python
self.assertIn(
    'catch (error) {\n        setText("serviceStatus", `服务检查失败：${error.message}`);\n      }',
    html,
)
```

该断言依赖 JS 代码中精确的空白字符布局（`\n        ` 缩进）。任何对 `acceptance.html` 中该 catch 块的格式化调整（如 prettier 自动格式化）都会导致此测试误失败，但实际逻辑并未变更。

**建议**: 改为语义化断言，例如拆分为多个 `assertIn` 检测关键 token 的组合存在：

```python
self.assertIn('catch (error)', html)
self.assertIn('setText("serviceStatus"', html)
self.assertIn('服务检查失败', html)
```

---

## 安全检查清单

| 检查项 | 状态 | 说明 |
|---|---|---|
| 硬编码密钥/密码 | ✅ 通过 | 无新增硬编码密钥 |
| XSS（跨站脚本） | ✅ 通过 | `onclick` 已移除，改为 `data-*` + 事件委托；按钮文本仍走 `escapeHtml` |
| CSV 注入 | ✅ 通过 | `escapeCsv` 已增加 `= + - @` 前缀防护（见 M1 小优化建议） |
| 日志脱敏 | ✅ 通过 | `sanitize_log_payload` 新增非 dict 入参类型守卫，有对应单测 |
| 异常处理一致性 | ✅ 通过 | `checkServiceBtn` 与其他按钮对齐，失败时显示中文错误信息 |
| 活体 challenge_id 边界 | ✅ 通过 | 三级回退 `liveness.challenge_id ?? challenge.challenge_id ?? null` |
| 测试覆盖 | ✅ 通过 | 新增 `test_sanitize_log_payload_rejects_non_dict_payload` + `test_acceptance_page_hardens_reviewed_frontend_edges` 覆盖全部修复点 |
| 外部依赖（CDN / 远程脚本） | ✅ 通过 | 无新增外部依赖 |
| 浏览器存储泄露 | ✅ 通过 | 无变化，仍无 localStorage/sessionStorage/indexedDB 使用 |
| 报告中敏感数据泄露 | ✅ 通过 | 无变化，仍排除 apiKey/image/frames/embedding |
