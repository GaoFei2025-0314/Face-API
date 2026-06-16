# Code Review Report — face_api V2.0

**日期**：2026-06-16  
**Commit**：`e392184` — fix: harden business demo and runtime safeguards  
**变更文件**：25 个文件，+952 / -68 行

### 变更文件列表

| 模块 | 文件 |
|---|---|
| 核心 API | `main.py`, `api_schemas.py`, `app_config.py`, `storage.py` |
| 业务 Demo | `business_demo/app.py`, `business_demo/errors.py`, `business_demo/face_api_client.py`, `business_demo/schemas.py`, `business_demo/storage.py`, `business_demo/README.md` |
| 脚本 | `scripts/run-business-demo.bat`, `scripts/terminal-demo.py` |
| 文档 | `README.md`, `architecture.html`, `docs/02_product/01_prd.md`, `docs/03_deployment/01_runbook.md`, `docs/04_usage/01_api_integration.md`, `docs/04_usage/04_business_integration_v2.md`, `docs/04_usage/05_spring_boot_integration_notes.md` |
| Spec | `specs/021-business-integration-demo/plan.md` |
| 测试 | `tests/test_app_config.py`, `tests/test_business_demo.py`, `tests/test_main_api.py`, `tests/test_scripts_smoke.py`, `tests/test_storage_schema.py` |

---

## CRITICAL

暂无。

---

## HIGH

暂无。

---

## MEDIUM

### M1 — `storage.py:20`：模块级 logger 未配置 handler，checkpoint / 连接关闭错误不进入 `face_api.log`

**位置**：`storage.py:20`（`logger = logging.getLogger(__name__)`），调用点 `storage.py:166`, `storage.py:687`, `storage.py:699`, `storage.py:701`

**问题描述**：

本次 commit 将 storage.py 中原来静默吞掉的 `pass` 改为 `logger.exception(...)`，方向正确。但 `logger = logging.getLogger("storage")` 是一个独立 logger，没有配置任何 handler。它默认 propagate 到 root logger，root logger 的唯一 handler 是 `logging.lastResort`（写到 `sys.stderr`）。

`main.py` 中配置的是 `logging.getLogger("face_api")`，两个 logger 是平级关系，"storage" 不是 "face_api" 的子 logger。

**后果**：
- 在终端直接运行时：错误会出现在 stderr（终端输出）中，但不会写入 `logs/face_api.log`
- 在 Windows Service（NSSM）运行时：错误会进入 NSSM 的 stderr 日志（`logs/nssm-service.err.log`），但操作人员通常只看 `face_api.log`
- 在任何场景下，WAL checkpoint 失败和连接关闭失败都不会出现在统一的结构化日志文件中，排障时容易遗漏

**修复建议**：

方案 A（推荐）：让 storage 模块复用 face_api logger

```python
# storage.py — 删除模块级 logger 定义，改为在函数内获取
# 在 _maybe_checkpoint / close / close_all_connections 中：
import logging
logging.getLogger("face_api").exception("WAL checkpoint failed")
```

方案 B：在 `setup_app_logger` 中同时配置 storage logger

```python
# main.py setup_app_logger 末尾加上：
storage_logger = logging.getLogger("storage")
storage_logger.handlers = logger.handlers
storage_logger.setLevel(logger.level)
```

---

### M2 — `business_demo/storage.py:313–341`：`replace_binding` 事务内 helper 的隐式耦合

**位置**：`business_demo/storage.py:334` 调用 `_create_binding_in_conn`

**问题描述**：

`replace_binding` 先在同一事务内标记旧 binding 为 removed，再调用 `_create_binding_in_conn` 创建新 binding。`_create_binding_in_conn` 会检查是否已有 active binding（`SELECT ... WHERE bind_status = 'active'`）。由于旧记录已被标记为 removed，检查不会命中同一用户的旧记录。这个逻辑在当前上下文下正确，但 helper 和事务之间的耦合是隐式的——`_create_binding_in_conn` 不知道自己是在 replace 流程中被调用。

如果将来有人复用 `_create_binding_in_conn` 时忘记先清理旧记录，UNIQUE INDEX `idx_face_bindings_one_active_user` 会在 INSERT 时兜底报 `IntegrityError`（而非 `BusinessDemoError`），错误码不一致。

**当前风险**：低。UNIQUE INDEX 提供数据库级兜底保护，不会造成数据损坏。

**修复建议**（可选）：给 `_create_binding_in_conn` 加 `skip_check` 参数，在 replace 流程中跳过应用层检查，仅依赖 UNIQUE INDEX 兜底。

---

### M3 — `business_demo/app.py:361–370`：终端事件时间校验失败时跳过 `face_api_result` 结构校验

**位置**：`business_demo/app.py:361–370`

**问题描述**：

`terminal_login_event` 先校验时间窗口，只有时间通过才调用 `_validate_face_login_result`。时间不通过时，`req.face_api_result` 不被校验、不被存储、不被回显。

恶意终端可提交任意垃圾数据到 `face_api_result` 字段，配合过期时间戳绕过结构化校验。

**实际风险**：极低。`face_api_result` 不被存储也不被回显。

**修复建议**（防御性）：在函数开头添加基本结构校验：

```python
if not isinstance(req.face_api_result, dict) or not req.face_api_result:
    failure_reason = "FACE_API_LOGIN_REJECTED"
    accepted = False
```

---

### M4 — `business_demo/app.py:330`：token 签名泄露已修复（正向变更）

**位置**：`business_demo/app.py:330`

旧代码 `issued_token_id=token.split(".", 1)[1][:12]` 将 HMAC 签名片段写入 audit。本次改为 `uuid.uuid4().hex`，已修复。

---

## 正向确认

以下变更属于安全加固 / 质量提升，确认无问题：

| 变更 | 文件 | 说明 |
|---|---|---|
| Production CORS 校验 | `app_config.py:130-131` | `FACE_ENV=production` 时拒绝 `*` |
| Token Secret 生产校验 | `business_demo/app.py:55-58` | `BUSINESS_DEMO_ENV=production` 时拒绝默认密钥 |
| 终端事件 field 必填化 | `business_demo/schemas.py:40-43` | `event_id` 和 `recognized_at_epoch` 从 Optional 改为必填 |
| 终端事件时间窗口校验 | `business_demo/app.py:364-366` | 拒绝未来时间（`recognized_delta < -5`） |
| 终端事件幂等处理 | `business_demo/app.py:397-418` | `IntegrityError` → 返回已有 audit 记录 |
| 换脸事务原子化 | `business_demo/storage.py:313-341` | `replace_binding` 改为单事务内完成 |
| DB UNIQUE INDEX 约束 | `business_demo/storage.py:87-92` | 一用户一活跃绑定 + terminal_event 唯一 |
| 重复数据清理 | `business_demo/storage.py:95-136` | 启动时自动清理残留重复记录再建索引 |
| WAL 错误不再吞掉 | `storage.py` 多处 | `pass` → `logger.exception(...)` |
| 业务错误码细分 | `business_demo/errors.py` | 新增 5 个错误码 |
| face_login 响应补全 | `main.py:1367-1377` | 返回 `face_id`、`similarity`、`threshold` |
| Python 路径校验 | `scripts/run-business-demo.bat:15-20` | 启动前校验 `FACE_PYTHON` 是否存在 |
| Liveness 帧数入口校验 | `scripts/terminal-demo.py:106-107` | 文件帧模式至少 10 帧 |
| 测试覆盖 | 5 个测试文件 | 新增约 150 测试行 |

---

## 安全检查清单

| 检查项 | 状态 | 说明 |
|---|---|---|
| 密钥硬编码 | 通过 | 无硬编码密钥；`business-demo-dev-secret` 有 production 启动校验 |
| API Key 泄露 | 通过 | `index.html` 不含 `X-API-Key` / `FACE_API_KEY` / `faceApiKey` |
| Token 签名泄露 | 已修复 | `issued_token_id` 从签名片段改为 `uuid4().hex` |
| SQL 注入 | 通过 | 全部使用参数化查询；`where_sql` 拼接仅来自固定字符串 |
| XSS | 通过 | HTML 页面无外部 CDN、无 `import` / `require()` |
| CORS 生产限制 | 新增 | `FACE_ENV=production` 时禁止 `*` |
| 路径穿越 | 通过 | `RestoreReq.backup_dir` 由 `admin_ops` 在 `project_root` 范围内校验 |
| 输入校验 | 通过 | Pydantic 模型校验所有请求；`event_id` / `recognized_at_epoch` 改为必填 |
| 日志敏感信息 | 通过 | `sanitize_log_payload` 过滤 `api_key`、`embedding`、`image` 字段 |
| 幂等性 | 新增 | `terminal_event_id` + UNIQUE INDEX 保证终端上报幂等 |
| 绑定唯一性 | 新增 | UNIQUE INDEX + `replace_binding` 事务原子化 |
| 错误信息泄露 | 通过 | 错误返回 `detail.code/message/reason`，不暴露堆栈或内部路径 |
| 依赖安全 | 通过 | 未新增外部依赖 |
