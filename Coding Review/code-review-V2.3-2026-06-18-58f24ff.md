# Code Review Report — face_api V2.3

**日期**: 2026-06-18  
**提交**: `58f24ff` — `feat: complete roadmap v2.3 lightweight anti-spoof governance`  
**变更文件**:
- `AGENTS.md`
- `CLAUDE.md`
- `README.md`
- `acceptance.html`
- `api_errors.py`
- `api_schemas.py`
- `app_config.py`
- `architecture.html`
- `business_demo/app.py`
- `business_demo/errors.py`
- `business_demo/face_api_client.py`
- `business_demo/schemas.py`
- `business_demo/static/index.html`
- `business_demo/static/terminal.html`
- `camera-integration.html`
- `docs/02_product/02_quarterly_plan.md`

---

## 概述

V2.3 核心交付：轻量防翻拍阈值治理 + 中风险一次重试机制。新增 `evaluate_anti_spoof_risk()` 多维度帧分析、`risk_retry_token` 签发/核销链路、五类样例现场验收台 `acceptance.html`。以下发现聚焦于核心逻辑的正确性和安全性，不涉及文档格式。

---

## HIGH

### H1 — 中风险 action="review" 在 face_login 无处理路径，静默变成无操作

**文件**: `main.py:1589-1636`

**问题**: `evaluate_anti_spoof_risk()` 返回 medium 风险时，`action` 字段由 `FACE_ANTI_SPOOF_MEDIUM_ACTION` 决定，可选值包括 `retry` / `review` / `block`。但在 `face_login()` 的路由处理中，只有 `retry` 和 `block` 有对应的处理逻辑：

```python
# main.py:1589-1636
if FACE_ANTI_SPOOF_MEDIUM_ACTION == "retry":
    # ... 签发 retry_token 并 raise ANTI_SPOOF_MEDIUM_RETRY_REQUIRED
if FACE_ANTI_SPOOF_MEDIUM_ACTION == "block":
    # ... raise ANTI_SPOOF_MEDIUM_RETRY_EXHAUSTED
# review 无 branch —— 直接落到后续正常 face login 流程
```

当 `FACE_ANTI_SPOOF_MEDIUM_ACTION=review` 时，medium 风险的人脸仍然能正常通过 login（只要能匹配到底库记录），与 `allow` 行为一致，完全失去了 "review" 的含义。

**建议**: 补充 `review` 分支，例如写入 audit 标记 `risk_review_required`，返回认证失败并要求人工复核，或者至少在 response 中通过 `anti_spoof_risk.action=review` 让业务侧能区分。

---

### H2 — `face_anti_spoof_block_level` 硬编码为 "high"，对应环境变量成为死代码

**文件**: `app_config.py:167-168`

```python
if settings.face_anti_spoof_block_level != "high":
    raise RuntimeError("FACE_ANTI_SPOOF_BLOCK_LEVEL V2.1 仅支持 high，避免轻量防翻拍过度打扰用户")
```

**问题**: `FACE_ANTI_SPOOF_BLOCK_LEVEL` 环境变量已在 README 的配置表中未列出（当前 README 缺少 V2.3 新增的多个防翻拍变量），但在 `app_config.py` 中读取和验证。该字段只能为 "high"，设其他值直接启动崩溃。在整个 `main.py` 的防翻拍逻辑中，`FACE_ANTI_SPOOF_BLOCK_LEVEL` 从未被实际使用 —— `evaluate_anti_spoof_risk()` 通过硬编码条件（`critical_count >= 2 AND static_face_box`）决定 high 风险，不依赖此配置。

这意味着：
1. 环境变量是摆设，操作人员调节它只会导致服务起不来
2. 如果未来要放开 block_level 为 "medium"，`evaluate_anti_spoof_risk()` 的高风险判定逻辑也需要同步改

**建议**: 要么从 `app_config.py` 和 `RuntimeSettings` 中删除此字段，要么在 `evaluate_anti_spoof_risk()` 中实际使用它来控制 high 风险阈值。当前状态是"伪可配"陷阱。

---

## MEDIUM

### M1 — `poor_capture_quality` 诊断原因不影响风险等级，成为纯日志噪音

**文件**: `main.py:579-580`

```python
if sharpness_variation < FACE_ANTI_SPOOF_MIN_SHARPNESS_VARIATION and frame_variation < FACE_ANTI_SPOOF_MIN_FRAME_VARIATION:
    reasons.append("poor_capture_quality")
```

**问题**: `poor_capture_quality` 不在 `critical_reasons` 集合（第 589 行）中，所以它永远只追加到 `reasons` 列表但从不影响风险等级决策。而且触发该条件时，`low_frame_variation` 已经同时会被加入 reasons（因为 `frame_variation < threshold`），所以 `poor_capture_quality` 提供的信息是冗余的。

**建议**: 要么将 `poor_capture_quality` 加入 `critical_reasons`（如果它确实应升级风险等级），要么删除这个条件分支以减少维护负担。

---

### M2 — 纹理差异度与清晰度变化阈值混用，指标名称不一致

**文件**: `main.py:576-577`

```python
if (
    max_frame_delta >= FACE_ANTI_SPOOF_MIN_FRAME_DELTA
    and frame_variation >= FACE_ANTI_SPOOF_MIN_FRAME_VARIATION
    and max_frame_delta_texture < max(1.0, FACE_ANTI_SPOOF_MIN_SHARPNESS_VARIATION)
):
    reasons.append("uniform_frame_delta")
```

**问题**: 第 562 行计算 `max_frame_delta_texture = float(np.std(delta))`，这是连续帧像素差异的**标准差**，度量的是纹理均匀性。但这里比较的阈值是 `FACE_ANTI_SPOOF_MIN_SHARPNESS_VARIATION`（环境变量名中带 "sharpness"）。`_frame_sharpness()` 用 Laplacian 方差衡量清晰度，而这里是像素差的 std —— 两者含义不同。

当前 `max(1.0, ...)` 作为安全下界让这个条件不容易触发，但语义混淆会在调参时误导运维人员——他们调整清晰度阈值却影响了一个纹理均匀性判断。

**建议**: 将这段独立配置项命名为 `FACE_ANTI_SPOOF_MIN_TEXTURE_VARIATION`，或直接复用 `FACE_ANTI_SPOOF_MIN_FRAME_DELTA` 放大系数。

---

### M3 — `purpose` 参数未在 API 层做枚举校验，仅依赖内部函数

**文件**: `main.py:1063-1064`

```python
if purpose not in {"login", "register"}:
    raise_api_error(422, "VALIDATION_ERROR")
```

**问题**: 这里 check 了 `purpose`，但 `submit_liveness_challenge()` (第 1096 行) 只做了 `req.purpose.strip().lower()` 后与 challenge 记录比对，没有做同样的枚举校验。如果客户端传 `purpose=admin`，会进入后续逻辑直到 `consume_liveness_challenge` 的 `purpose_mismatch` 分支才报错——错误码是 `LIVENESS_CHALLENGE_INVALID` 而不是 `VALIDATION_ERROR`，排查方向不够明确。

**建议**: 在 `submit_liveness_challenge()` 中同样添加 `purpose` 枚举校验，统一提前报 `VALIDATION_ERROR`。

---

### M4 — `acceptance.html` user_id 零值边界：允许 `0` 作为有效 user_id 可能导致误注册

**文件**: `acceptance.html:272-278`

```javascript
function parseTestUserId() {
    const raw = $("testUserId").value.trim();
    if (!raw) return null;
    const value = Number.parseInt(raw, 10);
    if (!Number.isInteger(value) || String(value) !== raw) {
        throw new Error("测试 user_id 必须是整数，或留空");
    }
    return value;
}
```

**问题**: 当输入 `"0"` 时，`parseTestUserId()` 返回 `0`（合法整数），但如果根本没填而输入框默认值是空字符串 → 返回 `null`。问题是 `registerTestUser()` 第 670 行把 `state.testUser.user_id` 作为 `user_id` 传入 `/faces/register`，值为 `0` 时会被 FastAPI 序列化为 `0` 写入数据库。后续 `face_login` 匹配到的 `user_id` 也是 `0`。在统计或 audit 中，`user_id=0` 和 `user_id=null` 容易混淆。

**建议**: 拒绝 `0` 作为测试 user_id，要求至少为 `1`，与业务系统的用户 ID 惯例一致：

```javascript
if (!Number.isInteger(value) || String(value) !== raw || value < 1) {
```

---

### M5 — `app_config.py` 验证错误信息引用旧版本号

**文件**: `app_config.py:168`

```python
raise RuntimeError("FACE_ANTI_SPOOF_BLOCK_LEVEL V2.1 仅支持 high，避免轻量防翻拍过度打扰用户")
```

**问题**: 当前代码基线是 V2.3，错误信息仍引用 `V2.1`。操作人员看到这个报错会困惑是否运行了错误版本。

**建议**: 改为 `V2.3` 或去掉版本号，仅描述约束。

---

## 安全检查清单

| 检查项 | 状态 | 说明 |
|---|---|---|
| 硬编码密钥/密码/Token | ✅ 通过 | `business-demo-dev-secret` 仅作默认值，生产环境强制校验拒绝 |
| SQL 注入 | ✅ 通过 | 所有 SQL 使用参数化查询 `?` 占位符 |
| XSS（HTML 页面） | ✅ 通过 | `escapeHtml()` / `sanitize()` 覆盖所有动态内容；API Key 不写入 DOM |
| embedding 泄露 | ✅ 通过 | `sanitize()` 和 `strip_embedding()` 过滤，`risk_retry_token` 在前端展示层剥离 |
| 认证绕过 | ✅ 通过 | face_login 强制 `require_api_key`；retry_token 校验 terminal_id |
| 输入校验 | ✅ 通过 | image_bytes / base64 长度、图片像素、帧数量均有校验 |
| 重放攻击 | ✅ 通过 | challenge 一次性消费（`used_at` + `BEGIN IMMEDIATE` 事务）；retry_token 一次性核销 |
| 时序攻击（token 比较） | ✅ 通过 | `hmac.compare_digest()` 用于 demo token；retry token hash 用 SHA256 |
| 权限提升 | ✅ 通过 | 无 |
| 日志敏感信息 | ✅ 通过 | `sanitize_log_payload()` 过滤 embedding / image / api_key |
| rate limiting | ⚠️ 未实现 | 无请求频率限制，但这是本地工作站部署，风险较低 |
| HTTPS | ⚠️ 未实现 | 纯 HTTP 部署；内网/本地工作站场景可接受 |

---

## 总结

- **安全**: 无 CRITICAL 安全问题。认证、token 核销、SQL 参数化、XSS 防护均到位。
- **质量**: 2 个 HIGH：中风险 `review` action 静默无操作（功能缺口），`block_level` 环境变量是伪可配陷阱（可能误导运维）。5 个 MEDIUM：诊断逻辑冗余、指标命名不一致、参数校验位置不统一、前端边界值和错误信息版本号。
- **亮点**: `evaluate_anti_spoof_risk()` 的多维度融合设计（亮度变化 + 逐帧像素差异 + 纹理均匀性 + 人脸框运动）覆盖了常见的静态翻拍攻击路径。`risk_retry_token` 的签发-核销链路通过 `BEGIN IMMEDIATE` 事务保证了 without-race 的一次性消费。`acceptance.html` 的五类样例验收界面覆盖了真人、打印照片、手机屏幕、电脑屏幕和视频播放的攻击面验证。
