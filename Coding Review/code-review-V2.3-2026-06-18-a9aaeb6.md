# Code Review Report — face_api V2.3

**日期**: 2026-06-18
**提交**: `a9aaeb6` — fix: close v2.3 medium action edge cases
**变更文件**:

- `main.py`
- `tests/test_main_api.py`
- `tests/test_scripts_smoke.py`

---

## CRITICAL

无。

---

## HIGH

无。

---

## MEDIUM

### 1. `else` 兜底分支复用了 retry 耗尽错误码，客户端无法区分"配置异常"与"重试次数用完"

**文件**: `main.py:1672`

**问题描述**:
当 `FACE_ANTI_SPOOF_MEDIUM_ACTION` 配置为未知值时，`else` 兜底分支返回的错误 `code` 是 `ANTI_SPOOF_MEDIUM_RETRY_EXHAUSTED`，与 retry 分支（第 1630 行）使用的 code 完全一致。

但两者的语义截然不同：
- retry 分支：用户行为问题（重试次数用完），用户换姿势/换光线后可能通过
- `else` 兜底：运维配置错误（env var 写成了不存在的值），无论用户怎么重试都过不了

前端如果按 `code` 做分支逻辑（如弹窗文案："重试次数已用完，请联系管理员"），会把配置错误的场景也当成重试耗尽来处理，误导用户和运维。

`message` 字段虽然写了"配置异常，已降级处理"，但不是所有客户端都会解析 `message` 做路由判断。

**修复建议**:
给 `else` 分支单独的错误码，与 retry 耗尽区分开：

```python
else:
    log_event("anti_spoof_medium_action_unknown", medium_action=FACE_ANTI_SPOOF_MEDIUM_ACTION)
    raise_with_audit(
        status_code=403,
        code="ANTI_SPOOF_CONFIG_INVALID",  # 独立错误码
        message="中风险未通过（配置异常，已降级处理）",
        ...
    )
```

如果担心新增错误码会破坏已有客户端的错误码映射表，至少确保 `message` 中"配置异常"这个关键词足够显眼，并在文档中说明该 code 可能对应两种场景。

---

## 变更评价

本次提交是一次干净的中等风险收尾修复，逐一回应了上一轮评审（`code-review-V2.3-2026-06-18-c7d3e46.md`）的全部 MEDIUM 发现：

- **MEDIUM #1（缺少 `else` 兜底）** → `face_login` 新增 `else` 分支（main.py:1668-1682），未知 action 走 fail-closed，安全优先。
- **MEDIUM #2（purpose 校验消息不一致）** → `create_liveness_challenge` 的 `purpose` 校验升级为详细错误消息（main.py:1068-1074），与 `submit_liveness_challenge` 保持一致。
- **MEDIUM #3（冒烟测试用字符串匹配替代行为验证）** → `test_face_login_medium_action_branches_are_explicitly_mutually_exclusive` 已删除（test_scripts_smoke.py）。

测试覆盖：

- `test_liveness_challenge_create_rejects_invalid_purpose_with_specific_message`（test_main_api.py:1251）：覆盖 `create_liveness_challenge` 的 purpose 校验新错误消息。
- `test_face_login_medium_anti_spoof_unknown_action_fails_closed`（test_main_api.py:1772）：覆盖 `else` 兜底分支，验证 403 + 正确 audit 记录，fail-closed 行为确认到位。

---

## 安全检查清单

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 无硬编码密钥 | ✅ | 未引入密钥或 token |
| 输入校验 | ✅ | `purpose` 白名单校验，`req` 为 Pydantic 模型 |
| SQL 注入 | ✅ | 未涉及 SQL 变更 |
| XSS 防护 | ✅ | 纯 JSON API |
| CSRF 防护 | N/A | 本地 API，API Key 认证 |
| 认证鉴权 | ✅ | 受影响端点均挂 `Depends(require_api_key)` |
| 敏感信息泄露 | ✅ | `purpose!r` 输出用户可控值，但属于校验报错场景，不泄露系统信息；`FACE_ANTI_SPOOF_MEDIUM_ACTION` 仅在服务端日志中出现 |
| 速率限制 | N/A | 当前无内置速率限制 |
| 依赖安全 | ✅ | 未引入新依赖 |
| 安全兜底 | ✅ | `else` 分支 fail-closed，未知配置走 403 而非放行 |
