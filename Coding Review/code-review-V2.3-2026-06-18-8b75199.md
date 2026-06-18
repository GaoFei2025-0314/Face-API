# Code Review Report — face_api V2.3

**日期**: 2026-06-18
**提交**: `8b75199` — fix: distinguish anti-spoof config errors
**变更文件**:

- `api_errors.py`
- `main.py`
- `tests/test_main_api.py`
- `docs/04_usage/01_api_integration.md`
- `docs/04_usage/05_spring_boot_integration_notes.md`

---

## CRITICAL

无。

---

## HIGH

无。

---

## MEDIUM

### 1. `ANTI_SPOOF_CONFIG_INVALID` 的实际返回 message 与 ERROR_DEFINITIONS 和文档不一致

**文件**: `main.py:1673` vs `api_errors.py:129` vs `docs/04_usage/01_api_integration.md:235`

**问题描述**:
`raise_with_audit` 调用传入了自定义 `message="中风险未通过（配置异常，已降级处理）"`，这会覆盖 `ERROR_DEFINITIONS` 中定义的 `"防翻拍配置异常"`。

而 `api_integration.md` 的错误码映射表写的是"防翻拍配置异常，请联系管理员"，与 API 实际返回不一致。前端如果按文档做了 message 精确匹配，会匹配不上。

**修复建议**:
统一成一种。建议让 `raise_with_audit` 不传 `message`，走 `ERROR_DEFINITIONS` 的默认值，保持一致性：

```python
else:
    log_event("anti_spoof_medium_action_unknown", medium_action=FACE_ANTI_SPOOF_MEDIUM_ACTION)
    raise_with_audit(
        status_code=403,
        code="ANTI_SPOOF_CONFIG_INVALID",
        # 不传 message，走 ERROR_DEFINITIONS 默认 "防翻拍配置异常"
        threshold=threshold,
        ...
    )
```

如果"中风险未通过（配置异常，已降级处理）"这个信息确实需要传达给客户端，把它放到 `reason` 参数中，保持 `message` 与 ERROR_DEFINITIONS 一致。

---

### 2. `block` 策略分支仍复用 `ANTI_SPOOF_MEDIUM_RETRY_EXHAUSTED`，语义不匹配

**文件**: `main.py:1641-1653`

**问题描述**:
`elif FACE_ANTI_SPOOF_MEDIUM_ACTION == "block"` 分支返回的错误码是 `ANTI_SPOOF_MEDIUM_RETRY_EXHAUSTED`，message 是"中风险重试未通过"。

但 `block` 策略的含义是"直接拦截中风险，不提供重试机会"——用户根本没有被给过重试。`ERROR_DEFINITIONS` 中该码的 reason 是"本次中风险重试机会**已使用**"，对 `block` 场景不成立。

本轮 commit 的 `elif` 重构让三个分支的语义差异更明显了：`retry`（给一次机会）、`block`（直接拦）、`review`（转人工）。`block` 却用着 `retry` 的错误码和文案，前端和 audit 都容易混淆。

**修复建议**:
给 `block` 策略单独一个错误码，与 retry 耗尽区分：

```python
"ANTI_SPOOF_MEDIUM_BLOCKED": {
    "message": "中风险未通过",
    "reason": "当前画面存在轻量防翻拍中风险，当前策略不允许重试，请重新发起登录或转人工复核",
},
```

注意：这是 pre-existing 问题，不在本次 diff 的核心改动范围内，但 `elif` 重构后更显眼了。如果暂时不加新错误码避免破环客户端映射表，至少更新 `message` 为"中风险未通过"而非"中风险重试未通过"。

---

### 3. `ANTI_SPOOF_CONFIG_INVALID` 的 reason 暴露了内部环境变量名

**文件**: `api_errors.py:130`

**问题描述**:
```python
"reason": "服务端中风险处理策略配置无效，已按失败处理，请联系管理员检查 FACE_ANTI_SPOOF_MEDIUM_ACTION",
```

`reason` 字段会被返回给 API 调用方（通常是业务后端，但可能透传到前端）。暴露 `FACE_ANTI_SPOOF_MEDIUM_ACTION` 这个内部环境变量名属于信息泄露，虽然对本地/内网 API 风险较低，但不符合最小信息披露原则。

**修复建议**:
```python
"reason": "服务端中风险处理策略配置无效，已按失败处理，请联系管理员检查防翻拍策略配置",
```

---

## 变更评价

本次提交正确落实了上一轮评审（`code-review-V2.3-2026-06-18-a9aaeb6.md`）的 MEDIUM 发现：

- **MEDIUM #1（`else` 兜底复用 retry 错误码）** → 已修复。`else` 分支使用独立 `ANTI_SPOOF_CONFIG_INVALID` 错误码，与 `ANTI_SPOOF_MEDIUM_RETRY_EXHAUSTED` 完全区分。
- **MEDIUM #2（purpose 校验消息不一致）** → 已修复。`create_liveness_challenge` 的 purpose 校验现在返回详细消息。
- **MEDIUM #3（冒烟测试用字符串匹配）** → 已在上一轮处理。

额外附带的改进：

- `face_login` 中 `block`/`review` 分支的 `if` → `elif` 重构，修复了未知 `FACE_ANTI_SPOOF_MEDIUM_ACTION` 值时静默放行中风险的 fail-open 漏洞（这是一个隐含的安全修复，值得在 commit message 中明确提及）。
- `low_sharpness_variation` 检测逻辑加入 `evaluate_anti_spoof_risk`，作为 `critical_reasons` 之一，在已有其他风险信号时强化判定。这个阈值变动会让部分之前被判定为 medium 的场景升级为 high，是合理的收紧。

测试覆盖：

- `test_anti_spoof_low_sharpness_variation_strengthens_static_face_risk`：覆盖 low_sharpness_variation 检测和 high 风险升级。
- `test_face_login_medium_anti_spoof_unknown_action_fails_closed`：覆盖 `else` 分支的 fail-closed 行为，验证 403 + `ANTI_SPOOF_CONFIG_INVALID` + audit 记录。
- `test_liveness_challenge_create_rejects_invalid_purpose_with_specific_message`：覆盖 `create_liveness_challenge` 的 purpose 校验新消息格式。

---

## 安全检查清单

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 无硬编码密钥 | ✅ | 未引入密钥或 token |
| 输入校验 | ✅ | `purpose` 白名单校验带详细错误消息 |
| SQL 注入 | ✅ | 未涉及 SQL 变更 |
| XSS 防护 | ✅ | 纯 JSON API |
| CSRF 防护 | N/A | 本地 API，API Key 认证 |
| 认证鉴权 | ✅ | 受影响端点均挂 `Depends(require_api_key)` |
| 敏感信息泄露 | ⚠️ | `ANTI_SPOOF_CONFIG_INVALID` 的 reason 暴露了内部环境变量名 `FACE_ANTI_SPOOF_MEDIUM_ACTION`（MEDIUM #3） |
| 速率限制 | N/A | 当前无内置速率限制 |
| 依赖安全 | ✅ | 未引入新依赖 |
| 安全兜底 | ✅ | `else` 分支 fail-closed；`if`→`elif` 重构消除了未知配置静默放行的 fail-open 漏洞 |
| 信息一致性 | ⚠️ | `ANTI_SPOOF_CONFIG_INVALID` 的 message 在 ERROR_DEFINITIONS 和实际调用中不一致（MEDIUM #1） |
