# Code Review Report — face_api V2.2

**日期**: 2026-06-17
**提交**: 0980a51 — feat: add v2.2 field algorithm acceptance console
**变更文件**:

- `AGENTS.md`
- `Coding Review/code-review-V2.1-2026-06-16-a9bf2b8.md`
- `README.md`
- `acceptance.html`（新建）
- `app_config.py`
- `architecture.html`
- `business_demo/README.md`
- `business_demo/app.py`
- `business_demo/storage.py`
- `docs/02_product/02_quarterly_plan.md`
- `docs/04_usage/03_recognition_security_accuracy.md`
- `docs/04_usage/04_business_integration_v2.md`
- `docs/90_archive/04_acceptance/06_v2.2_acceptance_record.md`（新建）
- `docs/superpowers/plans/2026-06-17-v2.2-field-algorithm-acceptance-console.md`（新建）
- `docs/superpowers/specs/2026-06-16-v2.2-field-algorithm-acceptance-console-design.md`（新建）
- `main.py`
- `specs/023-field-algorithm-acceptance-console/plan.md`（新建）
- `specs/023-field-algorithm-acceptance-console/spec.md`（新建）
- `specs/023-field-algorithm-acceptance-console/tasks.md`（新建）
- `specs/README.md`
- `specs/ROADMAP-v2.2.md`（新建）
- `tests/test_app_config.py`
- `tests/test_business_demo.py`
- `tests/test_main_api.py`
- `tests/test_scripts_smoke.py`

---

## CRITICAL

无。

---

## HIGH

### H1 — `acceptance.html` CSV 导出存在 Excel 公式注入风险

**文件**: `acceptance.html:420-423`

```javascript
function escapeCsv(value) {
    const text = String(value ?? "");
    return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}
```

`escapeCsv` 只在值包含逗号、双引号、回车或换行时添加引号包裹。当 CSV 中某个单元格值以 `=`、`+`、`-` 或 `@` 开头且不包含上述特殊字符时，Excel / WPS 打开该 CSV 会把单元格内容作为公式执行。虽然当前 `anti_spoof_risk.reasons` 和 `message` 由后端 API 生成（非用户直接输入），且验收台运行在本地内网，风险面很小，但作为防御纵深仍应修复。

**建议**: 在 `escapeCsv` 中对以 `=`、`+`、`-`、`@` 开头的值添加单引号前缀（`'`）：

```javascript
function escapeCsv(value) {
    const text = String(value ?? "");
    const escaped = /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
    return /^[=+\-@]/.test(text) ? `'${escaped}` : escaped;
}
```

### H2 — `checkServiceBtn` 错误处理静默吞掉所有异常

**文件**: `acceptance.html:713-718`

```javascript
$("checkServiceBtn").addEventListener("click", async () => {
    try {
        await checkService();
    } catch (_) {
        return;
    }
});
```

`catch (_)` 分支空返回，与页面其他按钮的错误处理不一致。`startCameraBtn`、`captureStillBtn`、`registerUserBtn` 都在 catch 中调用 `setText` 显示错误信息给用户，但 `checkServiceBtn` 失败时用户没有任何反馈，体验上像按钮点了没反应。

**建议**: 与其他按钮对齐，至少显示错误信息：

```javascript
$("checkServiceBtn").addEventListener("click", async () => {
    try {
        await checkService();
    } catch (error) {
        setText("serviceStatus", `服务检查失败：${error.message}`);
    }
});
```

---

## MEDIUM

### M1 — `sanitize_log_payload` 对非 dict/list/tuple 类型不做脱敏，且函数签名不再要求 dict 入参

**文件**: `main.py:119-130`

```python
def sanitize_log_payload(payload: dict) -> dict:
    def sanitize_value(value):
        if isinstance(value, dict):
            return {
                key: "***" if str(key).lower() in SENSITIVE_LOG_FIELDS else sanitize_value(nested_value)
                for key, nested_value in value.items()
            }
        if isinstance(value, list):
            return [sanitize_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(sanitize_value(item) for item in value)
        return value
    return sanitize_value(payload)
```

函数签名声明 `payload: dict` 且返回 `dict`，但 `sanitize_value` 的递归实现遇到叶子节点直接返回原值 `return value`。如果外部调用方误传入非 dict 类型（如纯字符串、int），函数会静默原样返回，不做任何脱敏。当前所有调用方确实传 dict，但防御宽度不如加上类型守卫。

**建议**: 在入口处增加类型断言：

```python
def sanitize_log_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise TypeError(f"sanitize_log_payload 只接受 dict，当前类型 {type(payload).__name__}")
    ...
```

### M2 — `renderSamples` 中使用 `onclick` 内联事件处理器拼接 `sample.id`

**文件**: `acceptance.html:305`

```javascript
`<button type="button" onclick="runSampleAttempt('${sample.id}')" ...>采集 1 次</button>`
```

`sample.id` 来自 `state.samples` 中的硬编码常量（`"real_face"`、`"printed_photo"` 等），实际不存在注入风险。但内联事件处理器在安全审计中是常见误报源，且如果未来有人新增动态 `sample.id`，会引入 XSS 入口。改为 `data-*` 属性 + 事件委托更安全。

**建议**: 改为事件委托模式：

```javascript
$("sampleGrid").addEventListener("click", (event) => {
    const btn = event.target.closest("[data-sample-id]");
    if (btn) runSampleAttempt(btn.dataset.sampleId);
});
```

并将按钮改为 `<button data-sample-id="${escapeHtml(sample.id)}">`。

### M3 — `acceptance.html` 中注册活体 `challenge_id` 边界情况处理不完整

**文件**: `acceptance.html:631-660`

```javascript
async function registerTestUser() {
    ...
    let challengeId = null;
    if (state.serviceStatus?.liveness?.register_enabled) {
        const challenge = await createChallenge("register");
        const frames = await captureFrames(24, 180);
        const liveness = await submitChallenge(challenge, frames);
        if (liveness.passed === false) {
            throw new Error(liveness.reason || liveness.result_reason || "注册活体未通过");
        }
        challengeId = liveness.challenge_id;
    }
    ...
}
```

活体 challenge 通过后，`challengeId` 从 `liveness.challenge_id` 取值。如果 `submitChallenge` 返回 `passed: true` 但没有 `challenge_id` 字段，`challengeId` 会是 `undefined`，传给 `/faces/register` 的 `challenge_id` 也是 `undefined`。后端是否能正确处理 `challenge_id: undefined`（即 `null`）取决于 API 实现。建议显式处理此边界。

**建议**: 如果 `liveness.challenge_id` 为 undefined，用 `challenge.challenge_id` 作为回退，或在注册时传 `null`：

```javascript
challengeId = liveness.challenge_id ?? null;
```

---

## 安全检查清单

| 检查项 | 状态 | 说明 |
|---|---|---|
| 硬编码密钥/密码 | ✅ 通过 | 无硬编码密钥；API Key 仅保存在浏览器内存变量 `state.apiKey` |
| API Key 鉴权绕过 | ✅ 通过 | `X-API-Key` 头部仅在 `state.apiKey` 非空时附加 |
| XSS（跨站脚本） | ✅ 通过 | `escapeHtml` 覆盖 `& < > " '` 五个关键字符；`setText` 使用 `textContent` |
| CSV 注入 | ⚠️ 见 H1 | `escapeCsv` 未防护 Excel 公式注入字符 `= + - @` |
| SQL 注入 | N/A | 纯前端页面，无直接 SQL 操作 |
| 路径遍历 | N/A | 无文件系统访问 |
| 外部依赖（CDN / 远程脚本） | ✅ 通过 | `acceptance.html` 无任何外部 CDN、script src、stylesheet、import 或 require |
| 浏览器存储泄露 | ✅ 通过 | 无 `localStorage`、`sessionStorage`、`indexedDB` 使用 |
| 报告中敏感数据泄露 | ✅ 通过 | `buildReport` 中 `apiKey/image/frames` 显式设为 `undefined`，报告不含原图、连续帧或 embedding |
| 日志脱敏 | ✅ 通过 | `sanitize_log_payload` 已改为递归脱敏（修复 V2.1 H1），新增嵌套脱敏单测 |
| 种子用户控制 | ✅ 通过 | `business_demo` 在 `BUSINESS_DEMO_ENV=production` 时跳过种子用户播种（修复 V2.1 M4） |
| 环境变量整数解析 | ✅ 通过 | `business_demo/app.py` 新增 `env_int` 提供中文错误提示（修复 V2.1 H2） |
| `env_list` 可变默认值 | ✅ 通过 | `app_config.py` 中 `env_list` 改为 `return list(default)` 返回拷贝（修复 V2.1 M1） |
| HTTPS / 传输加密 | N/A | 本地工作站单机部署，无网络传输 |
| CORS 配置 | ✅ 通过 | `acceptance.html` 从 `http://localhost:8122` 访问时需配置 `FACE_CORS_ORIGINS`，文档和 README 均已说明 |
| 摄像头权限控制 | ✅ 通过 | 使用标准 `getUserMedia` API，浏览器控制权限弹窗 |
