# Code Review Report — face_api V2.3

**日期**: 2026-06-18
**提交**: `c7d3e46` — fix: address v2.3 3b10f17
**变更文件**:

- `Coding Review/code-review-V2.3-2026-06-18-3b10f17.md`
- `docs/04_usage/01_api_integration.md`
- `docs/04_usage/03_recognition_security_accuracy.md`
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

### 1. `face_login` 中风险分支缺少 `else` 兜底

**文件**: `main.py:1601-1662`

**问题描述**:
本次提交将 `face_login()` 中的中风险动作判定从三个独立 `if` 改为 `if`/`elif`/`elif` 链，修正了逻辑互斥表达。但三个分支（`"retry"`、`"block"`、`"review"`）都没有命中时，代码会静默穿透到第 1663 行的 `db.search()`，中风险防翻拍检测被完全绕过。

虽然这是前置问题（改 `elif` 之前同样存在），但 `elif` 链使得缺少兜底更显眼。如果运维误将 `FACE_ANTI_SPOOF_MEDIUM_ACTION` 配成不存在的值（如 `"warn"` 或拼写错误），中风险攻击的活体提交会被当作低风险放行。

**修复建议**:
在三个分支后加 `else` 兜底，默认降级为 `"block"` 并记录告警日志：

```python
elif FACE_ANTI_SPOOF_MEDIUM_ACTION == "review":
    ...
else:
    # 配置异常时默认 block，安全优先
    logger.error("FACE_ANTI_SPOOF_MEDIUM_ACTION 未知值: %s，降级为 block", FACE_ANTI_SPOOF_MEDIUM_ACTION)
    raise_with_audit(
        status_code=403,
        code="ANTI_SPOOF_MEDIUM_RETRY_EXHAUSTED",
        message="中风险未通过（配置异常，已降级处理）",
        ...
    )
```

### 2. `create_liveness_challenge` 与 `submit_liveness_challenge` 的 `purpose` 校验错误消息不一致

**文件**: `main.py:1068-1069` vs `main.py:1101-1108`

**问题描述**:
两个端点都对 `purpose` 做相同的合法性校验（`not in {"login", "register"}`），但 `submit_liveness_challenge` 本次升级了详细错误消息（含实际值），`create_liveness_challenge` 仍然用旧版 `raise_api_error(422, "VALIDATION_ERROR")`，只返回固定文案"请求参数校验失败"。

前端对接时，同一个字段的同一类错误在不同接口返回不同格式的消息体，排查时容易困惑。

**修复建议**:
统一 `create_liveness_challenge` 的 `purpose` 校验错误消息，与 `submit_liveness_challenge` 保持一致：

```python
if purpose not in {"login", "register"}:
    raise_api_error(
        422,
        "VALIDATION_ERROR",
        message="purpose 必须是 login 或 register",
        reason=f"当前值为 {purpose!r}，仅支持 login 和 register",
    )
```

### 3. `test_face_login_medium_action_branches_are_explicitly_mutually_exclusive` 用字符串匹配替代行为验证

**文件**: `tests/test_scripts_smoke.py:401-406`

**问题描述**:
新增的冒烟测试通过读取 `main.py` 源文件、断言字符串 `elif FACE_ANTI_SPOOF_MEDIUM_ACTION == "block"` 和 `elif ... == "review"` 存在，来"验证"分支互斥性。这不是行为验证——它不测试运行时逻辑是否正确，只检查源码写了 `elif` 关键词。

如果将来改用字典分发或 `match`/`case`（Python 3.10+），这个测试会误报失败，而实际行为完全正确。

**修复建议**:
冒烟测试改成函数级行为验证更可靠。例如：构造一种场景（配置 retry/block/review 各一次），确认只有对应的分支执行。或者至少给这个测试名加注释说明它只管源码形态，不负责行为正确性。

当前提交中的单元测试 `test_main_api.py` 已有较充分的行为覆盖，冒烟测试可以作为辅助断言，但测试名建议改为 `test_face_login_medium_action_uses_elif_chain` 以明确其范围。

---

## 变更评价

本次提交质量整体良好：

- **`low_sharpness_variation` 强化信号**（main.py:580-585）: 设计合理，清晰度变化低不作为独立翻拍信号，仅在已有其他静态画面信号时作为增强因子。配合 `critical_reasons` 扩展（main.py:594），形成了一条新的 `high` 上升路径：`static_face_box` + `uniform_frame_delta` + `low_sharpness_variation` → `high`。与上一提交 `3b10f17` 中"`FACE_ANTI_SPOOF_MIN_SHARPNESS_VARIATION` 成为无效配置"的评审意见形成闭环。
- **`if` → `elif` 修正**（main.py:1635/1649）: 正确表达了三个动作的互斥语义，消除了阅读歧义。
- **测试覆盖**: 新增的单元测试 `test_anti_spoof_low_sharpness_variation_strengthens_static_face_risk` 覆盖了新信号的关键路径，变量隔离到位。
- **错误消息细化**（main.py:1102-1108）: `purpose` 校验返回具体值和中文提示，比旧版"请求参数校验失败"明显改善排查体验。

---

## 安全检查清单

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 无硬编码密钥 | ✅ | 密钥通过 `FACE_API_KEY` 环境变量管理 |
| 输入校验 | ✅ | `purpose` 白名单校验；`req.purpose` 为 Pydantic 必填字段 |
| SQL 注入 | ✅ | 本次提交未涉及 SQL，`storage.py` 使用参数化查询 |
| XSS 防护 | ✅ | 纯 JSON API，无 HTML 渲染 |
| CSRF 防护 | N/A | 本地 API，使用 API Key 认证 |
| 认证鉴权 | ✅ | 受影响端点均挂 `Depends(require_api_key)` |
| 敏感信息泄露 | ✅ | 未在响应中返回 embedding；错误消息未泄露系统路径或密钥 |
| 速率限制 | N/A | 当前无内置速率限制（本地部署，信任网络边界） |
| 依赖安全 | ✅ | 未引入新依赖 |
