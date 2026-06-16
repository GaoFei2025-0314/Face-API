# Code Review Report — face_api V2.1

**日期**：2026-06-16
**Commit**：`eb75fab` — feat: add lightweight anti-spoofing risk
**变更文件**：22 个文件

### 变更文件列表

| 模块 | 文件 |
|---|---|
| 核心 API | `main.py` |
| 错误定义 | `api_errors.py` |
| 请求/响应模型 | `api_schemas.py` |
| 配置加载 | `app_config.py` |
| 运维工具 | `admin_ops.py` |
| 核心存储 | `storage.py` |
| 业务 Demo | `business_demo/app.py`, `business_demo/errors.py`, `business_demo/storage.py`, `business_demo/face_api_client.py`, `business_demo/static/index.html`, `business_demo/static/terminal.html` |
| 脚本 | `scripts/terminal-demo.py` |
| 测试 | `tests/test_app_config.py`, `tests/test_business_demo.py`, `tests/test_main_api.py`, `tests/test_scripts_smoke.py`, `tests/test_storage_schema.py` |
| 文档/Spec | `specs/022-lightweight-anti-spoofing/spec.md`, `specs/022-lightweight-anti-spoofing/tasks.md`, `specs/022-lightweight-anti-spoofing/quickstart.md`, `specs/README.md`, `specs/ROADMAP-v2.1.md`, `docs/04_usage/01_api_integration.md`, `docs/04_usage/03_recognition_security_accuracy.md`, `docs/04_usage/04_business_integration_v2.md`, `docs/90_archive/04_acceptance/05_v2.1_acceptance_record.md` |
| 前端页面 | `architecture.html`, `camera-integration.html` |

---

## CRITICAL

暂无。

---

## HIGH

### H1 — `main.py:1429`：`exc.detail["code"]` 在未校验 dict 类型时直接取键，存在 TypeError 风险

**位置**：`main.py:1426-1431`（`face_login` 函数内 `get_single_face_or_raise` 的 except 分支）

**问题描述**：

```python
except HTTPException as exc:
    reason = exc.detail.get("reason") if isinstance(exc.detail, dict) else None  # ← 有守卫
    raise_with_audit(
        status_code=exc.status_code,
        code=exc.detail["code"],          # ← 无守卫，直接 dict 下标访问
        message=exc.detail["message"],
```

第 1426 行对 `reason` 做了 `isinstance(exc.detail, dict)` 守卫，但紧接着第 1429 行直接对 `exc.detail` 做 `["code"]` 下标访问。当前路径中 `exc` 来自 `get_single_face_or_raise` → `raise_api_error`，detail 始终为 dict，故实际不会触发。但代码结构不一致，未来如果有人在此 except 块捕获来自其他调用链的 `HTTPException`（detail 可能为字符串），会直接抛出 `TypeError`，导致 500 而非结构化的错误响应。

**修复建议**：统一提取 detail，与下面第 1461 行的写法保持一致：

```python
except HTTPException as exc:
    detail = exc.detail if isinstance(exc.detail, dict) else {}
    reason = detail.get("reason")
    raise_with_audit(
        status_code=exc.status_code,
        code=detail.get("code", "NO_FACE"),
        message=detail.get("message", "未检测到人脸"),
        reason=reason,
        ...
    )
```

---

### H2 — `business_demo/app.py:93-101`：`verify_demo_token` 未捕获 `binascii.Error`，畸形 Token 导致 500

**位置**：`business_demo/app.py:74-76`（`_b64url_decode`）→ `business_demo/app.py:93-101`（`verify_demo_token`）

**问题描述**：

```python
def _b64url_decode(data):
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))
    # ↑ binascii.Error 如果 base64 内容非法

def verify_demo_token(token, secret):
    try:
        body, signature = token.split(".", 1)
    except ValueError:                    # ← 只捕获了 ValueError
        raise_business_error("TOKEN_INVALID")
    ...
    payload = json.loads(_b64url_decode(body).decode("utf-8"))
    # ↑ _b64url_decode 内部可能抛出 binascii.Error，未被捕获
```

`base64.urlsafe_b64decode` 在输入包含非法 base64 字符时抛出 `binascii.Error`（不是 `ValueError` 的子类）。`verify_demo_token` 的 except 只捕获 `ValueError`，`binascii.Error` 会穿透到 FastAPI 默认异常处理器，返回 500。攻击者可通过发送畸形 Token 观察响应差异来探测服务端行为。

**修复建议**：扩宽捕获范围：

```python
def verify_demo_token(token, secret):
    try:
        body, signature = token.split(".", 1)
        payload_bytes = _b64url_decode(body)
    except (ValueError, Exception):
        raise_business_error("TOKEN_INVALID")
```

---

## MEDIUM

### M1 — `app_config.py:119-125`：5 个浮点配置项直接用 `float()` 取值，未使用已有的 `env_float()` 辅助函数

**位置**：`app_config.py:119-125`（`load_settings` 函数内 `RuntimeSettings` 构造）

**问题描述**：

```python
min_register_det_score=float(os.getenv("FACE_MIN_REGISTER_DET_SCORE", "0.5")),
min_register_brightness=float(os.getenv("FACE_MIN_REGISTER_BRIGHTNESS", "30")),
max_register_brightness=float(os.getenv("FACE_MAX_REGISTER_BRIGHTNESS", "225")),
min_login_det_score=float(os.getenv("FACE_MIN_LOGIN_DET_SCORE", "0.4")),
min_face_sharpness=float(os.getenv("FACE_MIN_FACE_SHARPNESS", "2")),
```

同文件第 27-37 行已定义 `env_float(name, default, minimum)` 辅助函数，提供非法值检测（`ValueError` → `RuntimeError` 带中文提示）和最小值校验。反翻拍相关的 3 个浮点配置（`min_frame_variation`、`min_face_motion`、`min_sharpness_variation`）正确使用了 `env_float`，但上面 5 个配置直接用 `float()` 取值。如果运维误设 `FACE_MIN_FACE_SHARPNESS=abc`，会得到一个无上下文的 `ValueError: could not convert string to float: 'abc'`，而非友好的 `FACE_MIN_FACE_SHARPNESS 必须是数字`。

**修复建议**：统一使用 `env_float`，并设定合理的最小值：

```python
min_register_det_score=env_float("FACE_MIN_REGISTER_DET_SCORE", 0.5, 0.0),
min_register_brightness=env_float("FACE_MIN_REGISTER_BRIGHTNESS", 30, 0.0),
max_register_brightness=env_float("FACE_MAX_REGISTER_BRIGHTNESS", 225, 0.0),
min_login_det_score=env_float("FACE_MIN_LOGIN_DET_SCORE", 0.4, 0.0),
min_face_sharpness=env_float("FACE_MIN_FACE_SHARPNESS", 2, 0.0),
```

---

### M2 — `main.py:537`：`repeated_frames` 判定阈值 `1.0` 硬编码，不可配置

**位置**：`main.py:537`（`evaluate_anti_spoof_risk` 函数内）

**问题描述**：

```python
if max_frame_delta < 1.0:          # ← 硬编码
    reasons.append("repeated_frames")
```

所有其他反翻拍阈值（`min_frame_variation`、`min_face_motion`、`min_sharpness_variation`）均已通过 `app_config.py` 的 env var 暴露为可配置项。唯独 `repeated_frames` 的帧间像素差异阈值固定为 `1.0`（0-255 尺度）。在不同光照条件或摄像头型号下，该阈值的敏感度可能不同——强逆光场景下轻微噪声就可能超过 1.0，暗光场景下真实变化可能不到 1.0。现场无法在不改代码的情况下调整。

**修复建议**：增加环境变量 `FACE_ANTI_SPOOF_MIN_FRAME_DELTA`（默认 `1.0`），与现有反翻拍阈值体系保持一致。

---

### M3 — `main.py:603`：`evaluate_blink_frames` 中亮度变化阈值 `5.0` 硬编码，不可配置

**位置**：`main.py:603`（`evaluate_blink_frames` 函数内）

**问题描述**：

```python
if variation < 5.0:               # ← 硬编码
    sampled_faces = _sample_faces_for_anti_spoof(decoded_frames)
    risk = evaluate_anti_spoof_risk(decoded_frames, sampled_faces)
```

这是眨眼活体的核心判定条件——亮度变化低于 5.0 即进入反翻拍评估流程。该阈值是整个活体检测链路上最关键的参数之一：设太低会让静态攻击漏过，设太高会导致真人频繁被误判进入反翻拍流程。与 M2 类似，所有同级阈值均可配置，唯独此值硬编码。

**修复建议**：增加环境变量 `FACE_LIVENESS_MIN_BRIGHTNESS_VARIATION`（默认 `5.0`），纳入 `app_config.py` 的 `RuntimeSettings`。

---

### M4 — `business_demo/storage.py:413-422`：`list_audits` 使用 `+=` 拼接 SQL WHERE 子句

**位置**：`business_demo/storage.py:413-422`（`list_audits` 方法）

**问题描述**：

```python
query = "SELECT * FROM business_login_audits WHERE 1=1"
params = []
if terminal_id:
    query += " AND terminal_id = ?"
    params.append(terminal_id)
if success is not None:
    query += " AND success = ?"
    params.append(1 if success else 0)
query += " ORDER BY created_at DESC, id DESC LIMIT ?"
```

当前实际安全——列名片段硬编码，参数值通过 `params` 参数化传入。但该模式与主 `storage.py:659` 的 `where_sql` f-string 拼接属于同类问题（上轮 Review 的 M1），且该文件没有类似主 `storage.py` 的安全注释。业务 Demo 的代码变更频率通常更高，后续扩展过滤条件时容易引入拼接漏洞。

**修复建议**：在方法上方添加安全边界注释，与主 `storage.py:658` 的处理方式一致。

---

## 正向确认

以下变更属于安全加固 / 质量提升，确认无问题：

| 变更 | 文件 | 说明 |
|---|---|---|
| 轻量防翻拍风险评分 | `main.py:506-576` | `evaluate_anti_spoof_risk` 基于帧亮度变化、帧差、人脸框位移、清晰度变化的多信号融合，逻辑清晰，判定层次分明（low/medium/high），不依赖外部模型 |
| AntiSpoofRisk 响应模型 | `api_schemas.py:100-106` | Pydantic 模型约束 level/reasons/action/message/metrics，metrics 不包含原始帧或 embedding |
| 反翻拍配置体系 | `app_config.py:137-142` | 5 个 env var 控制阈值和策略，启动时校验 `block_level` 和 `medium_action` 取值合法性 |
| 反翻拍结果全链路透传 | `main.py`, `storage.py`, `business_demo/` | challenge 存储、login audit、业务 audit 三级均持久化 `anti_spoof_risk`，前端页面展示但不暴露内部 metrics |
| 防翻拍错误码 | `api_errors.py:108-111` | `ANTI_SPOOF_HIGH_RISK` 带简短中文提示，用户端不暴露内部诊断细节 |
| 高风险阻断 + 审计 | `main.py:554-561` | high 级别直接 block，medium 级别动作可配置（review/retry），全部记录 audit |
| 反翻拍禁用模式 | `main.py:507-513` | 禁用时返回 `level: "low"` + `reasons: ["anti_spoof_disabled"]`，运维可审计 |
| 活体挑战生命周期 | `storage.py:430-589` | `BEGIN IMMEDIATE` 事务保护 consume 操作，防竞态重复消费；过期自动标记 |
| 防翻拍采样 | `main.py:579-588` | 从首/中/尾三帧采样人脸，减小全帧检测的计算开销 |
| 活体失败原因映射 | `main.py:457-468` | `liveness_failure_reason_text` 将内部原因码映射为用户可理解的中文提示 |
| 嵌入向量不泄露 | `main.py:295-296` | `strip_embedding` 过滤 embedding 字段，所有公开接口的响应均不包含特征向量 |
| 日志敏感字段脱敏 | `main.py:98,121-128` | `SENSITIVE_LOG_FIELDS` 包含 `api_key`/`embedding`/`image`/`image1`/`image2`，写入日志前替换为 `***` |
| Token 签名不写入 audit | `business_demo/app.py:343` | `issued_token_id` 使用 `uuid.uuid4().hex` 而非 HMAC 签名片段 |
| Token 防篡改 | `business_demo/app.py:91-101` | HMAC-SHA256 + `hmac.compare_digest` 常量时间比较 + TTL 过期检查 |
| 终端事件时间窗口 | `business_demo/app.py:381-386` | 拒绝未来时间（5s 容差）和超过 120s 的过期事件 |
| 终端事件幂等 | `business_demo/app.py:363-368,426-436` | `terminal_event_id` + UNIQUE INDEX + `IntegrityError` 回退查询 |
| 生产环境密钥阻断 | `business_demo/app.py:55-58` | `BUSINESS_DEMO_ENV=production` 时拒绝默认/空 `token_secret` |
| 路径穿越防护 | `admin_ops.py:30-40` | `ensure_backup_subdir` 校验备份路径必须在项目 `backups/` 子目录下 |
| FaceApiClient 错误映射 | `business_demo/face_api_client.py:30-49` | HTTPError → BusinessDemoError 逐层映射，区分 auth/unavailable/request 三类失败 |
| 维护模式互斥 | `admin_ops.py:20-22` | 写操作（注册/login/challenge）进入前检查维护模式 |
| 测试覆盖 | `tests/test_main_api.py`, `tests/test_storage_schema.py`, `tests/test_app_config.py`, `tests/test_business_demo.py` | 反翻拍风险评分（高/低）、challenge 提交带 anti_spoof_risk、审计持久化、配置校验、业务 Demo 登录阻断 |
| 能力边界声明 | `specs/022-lightweight-anti-spoofing/spec.md:88` | FR-010 明确 V2.1 不覆盖高清屏幕视频、深度伪造、虚拟摄像头流或专业攻击 |

---

## 安全检查清单

| 检查项 | 状态 | 说明 |
|---|---|---|
| 密钥硬编码 | 通过 | `token_secret` 生产环境启动阻断；API Key 仅从环境变量读取 |
| SQL 注入 | 通过 | 全部参数化查询；主 `storage.py:658` 有安全注释，业务 `storage.py:413` 模式类似（见 M4） |
| XSS | 通过 | JSON API，无用户输入直接渲染 HTML |
| 路径穿越 | 通过 | `admin_ops.py:30-40` 校验备份路径必须在项目 `backups/` 下 |
| 命令注入 | 通过 | 无 `subprocess` 或 `os.system` 调用用户输入 |
| 输入校验 | 通过 | Pydantic 模型校验所有请求体；图片尺寸/像素双重限制；终端事件时间窗口硬限制 |
| 日志敏感信息 | 通过 | embedding、api_key、image 字段写入日志前脱敏为 `***` |
| 认证绕过 | 通过 | 显式认证路由使用 `require_api_key`；业务 Demo 二次校验 `face_api` 返回的 `authenticated` |
| Token 安全 | 通过 | HMAC-SHA256 + `compare_digest` + TTL 过期；签名不在 audit 中泄露 |
| 幂等性 | 通过 | `terminal_event_id` + UNIQUE INDEX + `IntegrityError` |
| 竞态条件 | 通过 | `consume_liveness_challenge` 使用 `BEGIN IMMEDIATE` 事务 |
| 错误信息泄露 | 通过 | 返回 `detail.code/message/reason`，不暴露堆栈；反翻拍原因码不在用户端展示 |
| 依赖安全 | 通过 | 未新增外部依赖 |
| 嵌入向量安全 | 通过 | 所有公开接口通过 `strip_embedding` 过滤；audit 不记录 embedding |
| 维护模式安全 | 通过 | 写操作路由入口统一调用 `ensure_not_maintenance` |
