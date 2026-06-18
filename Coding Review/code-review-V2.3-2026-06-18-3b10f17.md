# Code Review Report — face_api V2.3

**Date**: 2026-06-18
**Commit**: `3b10f17` — fix: address v2.3 anti-spoof review findings
**Changed files**:

- `Coding Review/code-review-V2.3-2026-06-18-58f24ff.md`
- `README.md`
- `acceptance.html`
- `api_errors.py`
- `app_config.py`
- `docs/04_usage/01_api_integration.md`
- `docs/04_usage/03_recognition_security_accuracy.md`
- `main.py`
- `tests/test_app_config.py`
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

### 1. `FACE_ANTI_SPOOF_MIN_SHARPNESS_VARIATION` 成为无效配置项

**文件**: `main.py:580-587`, `app_config.py:147`, `README.md`, `docs/04_usage/01_api_integration.md`, `docs/04_usage/03_recognition_security_accuracy.md`

**问题描述**:
本次提交在 `evaluate_anti_spoof_risk()` 中移除了 `poor_capture_quality` 判定条件（原逻辑：`sharpness_variation < threshold AND frame_variation < threshold`）。移除后 `sharpness_variation` 度量值仍在 metrics 中计算和返回，但不再参与任何防翻拍风险判定。

然而，`FACE_ANTI_SPOOF_MIN_SHARPNESS_VARIATION` 环境变量仍然保留在以下位置：
- `app_config.py:147` — `load_settings()` 加载并校验
- `app_config.py:87` — `RuntimeSettings` 字段定义
- `main.py:get_anti_spoof_policy()` — 返回给调用方的 policy API
- `README.md` — 环境变量参考表
- `docs/04_usage/01_api_integration.md` — API 集成文档
- `docs/04_usage/03_recognition_security_accuracy.md` — 安全策略文档
- `acceptance.html` — 验收台阈值提示

这会导致运维人员调整一个对防翻拍判定无任何影响的阈值，产生误导。

**修复建议**:
两个方向二选一：
1. **保留 sharpness 判定**: 在 `evaluate_anti_spoof_risk()` 中恢复基于 `sharpness_variation` 的判定逻辑（可以是新的独立条件，不必复用旧的 `poor_capture_quality` 组合条件）。
2. **彻底移除**: 从 `RuntimeSettings`、`load_settings()`、`get_anti_spoof_policy()`、README、文档、验收台中移除 `FACE_ANTI_SPOOF_MIN_SHARPNESS_VARIATION`。如果 `sharpness_variation` 度量仅用于观测，可以在 policy API 中将其移至 `metrics` 子对象而非 `thresholds`。

推荐方案 1，因为画面清晰度变化是翻拍检测的有效信号，完全丢弃会降低防翻拍的信号维度。

### 2. `face_login` 的三个 medium action 分支缺少显式互斥

**文件**: `main.py:1590-1651`

**问题描述**:
`retry`（L1591）、`block`（L1624）、`review`（L1638）三个分支使用独立 `if` 语句而非 `if/elif` 链。虽然当前每个分支都通过 `raise_with_audit()` 抛出异常来终止执行，功能上没有问题，但：

- 阅读者需要逐个确认每个分支是否会 fall through
- 如果将来有人在此区域添加代码（如在 `review` 分支后追加逻辑），可能意外地在已 raise 的分支后继续执行
- 三个独立 `if` 暗示这些条件可能同时为真，但实际上 `FACE_ANTI_SPOOF_MEDIUM_ACTION` 是单一值

**修复建议**:
```python
if FACE_ANTI_SPOOF_MEDIUM_ACTION == "retry":
    ...
elif FACE_ANTI_SPOOF_MEDIUM_ACTION == "block":
    ...
elif FACE_ANTI_SPOOF_MEDIUM_ACTION == "review":
    ...
```

> 注：`retry` 分支内部还有一个 `if retry_token_consumed:` 的子分支，改为 `elif` 不影响该内部逻辑。

### 3. `submit_liveness_challenge` 的 purpose 校验错误信息不够精确

**文件**: `main.py:1095-1097`

**问题描述**:
```python
purpose = req.purpose.strip().lower()
if purpose not in {"login", "register"}:
    raise_api_error(422, "VALIDATION_ERROR")
```

`VALIDATION_ERROR` 的通用 message 是"请求参数校验失败"，不指明具体是哪个字段。调用方在收到 422 时无法快速定位是 `purpose` 字段的问题还是其他字段的问题。对于调试和 API 集成不够友好。

**修复建议**:
```python
if purpose not in {"login", "register"}:
    raise_api_error(
        422,
        "VALIDATION_ERROR",
        message="purpose 必须是 login 或 register",
        reason=f"当前值为 {purpose!r}，仅支持 login 和 register",
    )
```

---

## 变更评审总结

本次提交质量较高，主要变更：

| 变更 | 评价 |
|------|------|
| 新增 `FACE_ANTI_SPOOF_MIN_TEXTURE_VARIATION` 独立阈值 | 合理，将纹理判定从 sharpness 阈值中解耦，语义更清晰 |
| 移除 `face_anti_spoof_block_level` 配置 | 正确清理，V2.1 起始终硬编码为 `high`，移除避免误配置 |
| 新增 `ANTI_SPOOF_MEDIUM_REVIEW_REQUIRED` 错误码 | 完整，有错误定义、API 抛出、审计记录、测试覆盖 |
| 新增 `submit_liveness_challenge` 的 purpose 校验 | 必要的输入校验，防止无效 purpose 流入后续逻辑 |
| 新增 `review` medium action 分支 | 逻辑正确，在实际人脸搜索前拦截，避免低置信度请求继续处理 |
| 移除 `poor_capture_quality` 判定 | 合理性存疑（见 MEDIUM #1），sharpness 信号被完全闲置 |
| `acceptance.html` user_id 校验收紧 | 合理，防止 0 和负数 user_id |
| 测试覆盖 | 新增 4 个测试用例覆盖所有新增/变更路径，测试质量良好 |

---

## 安全检查清单

| 检查项 | 状态 | 备注 |
|--------|------|------|
| API 密钥硬编码 | ✅ 通过 | 无硬编码密钥，通过 `FACE_API_KEY` 环境变量配置 |
| 输入校验 | ✅ 通过 | `purpose` 字段新增白名单校验；`user_id` 新增下限校验 |
| SQL 注入 | ✅ 通过 | 无 SQL 变更，继续使用参数化查询 |
| XSS | ✅ 通过 | `acceptance.html` 无新增 DOM 注入风险 |
| 认证/授权 | ✅ 通过 | 新增端点/分支均使用已有 `require_api_key` 依赖 |
| 敏感数据泄露 | ✅ 通过 | 错误响应无新增敏感信息泄露 |
| 审计日志 | ✅ 通过 | 新增 `review` 分支正确写入审计记录 |
| 权限控制 | ✅ 通过 | `purpose` 校验防止跨流程滥用 challenge |
| 线程安全 | ✅ 通过 | 无共享状态变更，`FACE_ANTI_SPOOF_MEDIUM_ACTION` 为模块级常量 |
| 配置安全 | ⚠️ 注意 | `FACE_ANTI_SPOOF_MIN_SHARPNESS_VARIATION` 成为无效配置（见 MEDIUM #1） |
| 速率限制 | ✅ 通过 | 无变更影响现有速率限制（如有） |
| 依赖安全 | ✅ 通过 | 无新增依赖 |
| 错误处理 | ✅ 通过 | 新增错误码有完整定义和处理路径 |
