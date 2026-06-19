# Code Review Report — face_api V2.5

**日期**: 2026-06-18
**提交**: `222ceb0` — fix: close v2.3 review and plan v2.4
**变更文件**:

- `api_errors.py`
- `main.py`
- `tests/test_main_api.py`
- `docs/04_usage/01_api_integration.md`
- `docs/04_usage/05_spring_boot_integration_notes.md`
- `.specify/feature.json`
- `AGENTS.md`
- `Coding Review/code-review-V2.3-2026-06-18-8b75199.md`
- `docs/01_document_index.md`
- `docs/02_product/02_quarterly_plan.md`
- `specs/README.md`
- `specs/ROADMAP-v2.4.md`
- `specs/025-wms-capture-loop-baseline/*` (8 个新文件)

---

## CRITICAL

无。

---

## HIGH

无。

---

## MEDIUM

无。

上一轮评审（`code-review-V2.3-2026-06-18-8b75199.md`）的三项 MEDIUM 发现全部在本提交中修复，逐一验证如下。

---

## 变更评价

本次提交有两个独立部分：**V2.3 评审修复**（`api_errors.py`、`main.py`、`tests/test_main_api.py`、文档）和 **V2.4 规划文档**（spec-kit、roadmap、索引）。

### V2.3 评审修复验证

**MEDIUM #1（`ANTI_SPOOF_CONFIG_INVALID` message 不一致）→ 已修复。**

- `main.py:800`: `raise_with_audit` 的 `message` 参数从 `str`（必填）改为 `Optional[str] = None`，允许回退到 `ERROR_DEFINITIONS` 默认值。
- `main.py:1669`: `else` 分支不再传自定义 `message`，走 `ERROR_DEFINITIONS` 的 `"防翻拍配置异常"`。
- 测试 `test_face_login_medium_anti_spoof_unknown_action_fails_closed`（lines 1882-1889）断言 `message` 为 `"防翻拍配置异常"`。

**MEDIUM #2（`block` 分支复用 `ANTI_SPOOF_MEDIUM_RETRY_EXHAUSTED`）→ 已修复。**

- `api_errors.py:120-123`: 新增 `ANTI_SPOOF_MEDIUM_BLOCKED` 错误定义，message `"中风险未通过"`，与 retry 耗尽语义完全区分。
- `main.py:1643`: `block` 分支改用 `code="ANTI_SPOOF_MEDIUM_BLOCKED"`，不再传 `message`（走 ERROR_DEFINITIONS 默认）。
- 新增测试 `test_face_login_medium_anti_spoof_block_uses_distinct_error_code`（lines 1782-1833），验证 403 + `ANTI_SPOOF_MEDIUM_BLOCKED` + audit 记录正确 + 未签发 retry token。

**MEDIUM #3（`ANTI_SPOOF_CONFIG_INVALID` reason 暴露内部环境变量名）→ 已修复。**

- `api_errors.py:134`: reason 从 `"..检查 FACE_ANTI_SPOOF_MEDIUM_ACTION"` 改为 `"..检查防翻拍策略配置"`。
- `docs/04_usage/01_api_integration.md:236` 和 `docs/04_usage/05_spring_boot_integration_notes.md:111` 同步更新。
- 测试新增 `assertNotIn("FACE_ANTI_SPOOF_MEDIUM_ACTION", exc_info.exception.detail["reason"])`（line 1889），防御性验证。

### V2.4 规划文档

新增 `specs/025-wms-capture-loop-baseline/` spec-kit 完整目录（spec、plan、tasks、research、data-model、quickstart、checklists），以及 `specs/ROADMAP-v2.4.md`。文档约束清晰：

- 不新增 API、环境变量、数据库表、业务逻辑。
- 不保存原图、视频帧、embedding、API Key。
- 问题归因固定为算法底座/终端采集/业务流程三类。
- 明确区分 Face API 仓库和 WMS 仓库提交范围，禁止 `git add .`。

其中 `quickstart.md` 的 API Key 对齐检查（Section 2.1）是一个实用的安全设计点——通过 `Select-String` 验证 `faceService.js` 中 `FACE_API_KEY` 注入与 `x-api-key` 请求头来源一致，避免现场联调时因 Key 不一致产生的 401/403 困惑。

---

## 安全检查清单

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 无硬编码密钥 | ✅ | `quickstart.md` 使用 `$env:FACE_API_KEY="123456"` 仅为文档示例 |
| 输入校验 | ✅ | 未新增用户输入路径 |
| SQL 注入 | ✅ | 未涉及 SQL 变更 |
| XSS 防护 | ✅ | 纯 JSON API |
| CSRF 防护 | N/A | 本地 API，API Key 认证 |
| 认证鉴权 | ✅ | 受影响端点均挂 `Depends(require_api_key)` |
| 敏感信息泄露 | ✅ | `ANTI_SPOOF_CONFIG_INVALID` reason 不再暴露 `FACE_ANTI_SPOOF_MEDIUM_ACTION`；V2.4 模板明确禁止保存原图/embedding/API Key |
| 速率限制 | N/A | 当前无内置速率限制 |
| 依赖安全 | ✅ | 未引入新依赖 |
| 安全兜底 | ✅ | `else` 分支 fail-closed 行为保持不变 |
| 错误码一致性 | ✅ | `block`、`config_invalid` 分支均走 ERROR_DEFINITIONS 默认 message，不再自定义覆盖 |
| 测试覆盖 | ✅ | 新增 `block` 策略测试 + `config_invalid` 测试更新了 reason 校验 |
