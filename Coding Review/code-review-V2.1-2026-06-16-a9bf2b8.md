# Code Review Report — face_api V2.1

**日期**: 2026-06-16  
**提交**: a9bf2b8 — fix: address v2.1 code review findings  
**变更文件**:

- `.gitattributes`
- `README.md`
- `app_config.py`
- `business_demo/app.py`
- `business_demo/storage.py`
- `docs/04_usage/01_api_integration.md`
- `docs/04_usage/03_recognition_security_accuracy.md`
- `main.py`
- `scripts/post-commit`
- `tests/test_app_config.py`
- `tests/test_business_demo.py`
- `tests/test_main_api.py`
- `tests/test_scripts_smoke.py`

---

## CRITICAL

无。

---

## HIGH

### H1 — 日志脱敏仅处理顶层字段，嵌套敏感数据可绕过

**文件**: `main.py:121-128`

```python
def sanitize_log_payload(payload: dict) -> dict:
    safe = {}
    for key, value in payload.items():
        if key.lower() in SENSITIVE_LOG_FIELDS:
            safe[key] = "***"
        else:
            safe[key] = value
    return safe
```

`sanitize_log_payload` 只检查顶层 key，不递归处理嵌套 dict。如果调用方传入 `{"nested": {"image": "base64..."}}` 或 `{"quality_metrics": {"embedding": [...]}}`，内层的敏感字段会原样写入日志。当前 `log_event()` 的调用方（`request_logging_middleware`、`face_login` 等）传入的都是扁平 dict，暂未触发此问题，但函数签名未约束调用方不能传入嵌套结构。

**建议**: 增加递归脱敏，或至少在 docstring 中明确标注"仅处理扁平 dict，调用方不得传入嵌套结构"。

### H2 — `business_demo/app.py` 中 `int()` 直接转换环境变量，缺少清晰的错误提示

**文件**: `business_demo/app.py:66-68`

```python
token_ttl_seconds=int(os.getenv("BUSINESS_DEMO_TOKEN_TTL_SECONDS", "3600")),
port=int(os.getenv("BUSINESS_DEMO_PORT", "8010")),
```

与 `app_config.py` 中 `env_int()`（提供中文 `RuntimeError`）不一致。如果运维将 `BUSINESS_DEMO_PORT` 设为非数字值（如 `"eight thousand"`），启动时报错是原始 `ValueError: invalid literal for int() with base 10`，而非可读的 `"BUSINESS_DEMO_PORT 必须是整数，当前值为 ..."`。

**建议**: 使用与 `app_config.py` 一致的 `env_int()` 模式，或至少 `try/except ValueError` 后抛出带上下文的 `RuntimeError`。

---

## MEDIUM

### M1 — `env_list` 返回可变默认值引用

**文件**: `app_config.py:40-44`

```python
def env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default          # 返回的是传入对象的引用
```

调用方获得的是 `default` 列表的引用而非副本。虽然当前 `load_settings()` 每次传入全新 list literal（如 `["*"]`），不会被外部修改影响，但如果未来有人在其他模块调用 `env_list` 后修改返回值，会污染后续调用。函数签名也未约束 `default` 不可被修改。

**建议**: `return list(default)` 返回浅拷贝，或改用 `tuple` 作为返回类型。

### M2 — `business_demo/storage.py` 的 schema 迁移不是原子操作

**文件**: `business_demo/storage.py:81-96`

```python
if "terminal_event_id" not in existing_columns:
    conn.execute("ALTER TABLE business_login_audits ADD COLUMN terminal_event_id TEXT")
if "anti_spoof_risk" not in existing_columns:
    conn.execute("ALTER TABLE business_login_audits ADD COLUMN anti_spoof_risk TEXT")
self._dedupe_for_unique_indexes(conn)
conn.executescript("""CREATE UNIQUE INDEX IF NOT EXISTS ...""")
```

多条 `ALTER TABLE` 和索引创建在一个事务内执行（context manager 的 `commit()` 在 `yield` 之后），但 SQLite 的 `ALTER TABLE ADD COLUMN` 在某些版本中不是完全事务安全的——如果在两条 `ALTER` 之间进程崩溃，schema 可能处于半迁移状态。`CREATE UNIQUE INDEX IF NOT EXISTS` 前调用 `_dedupe_for_unique_indexes` 是正确的，但如果迁移中途失败，重试时列已存在但索引未创建。

**建议**: 在迁移开始前检查完整目标状态，如果已部分迁移则先补完再继续；或至少将迁移包装为幂等操作，失败后可安全重试。

### M3 — `admin_restore` 失败后未重新建立 DB 连接

**文件**: `main.py:1357-1369`

```python
def admin_restore(req: RestoreReq):
    ...
    db.close_all_connections()
    restored = restore_db_files(Path(req.backup_dir))
    db.invalidate_search_cache()
    ...
```

如果在 `close_all_connections()` 之后、`restore_db_files()` 或 `invalidate_search_cache()` 抛异常，SQLite 连接已关闭但未重新打开，后续所有需要 DB 的请求都会失败，相当于服务进入了不可恢复的状态，只能重启。

**建议**: 将 `close_all_connections()` + `restore_db_files()` 包在 `try/except` 中，失败时记录错误并尝试重新初始化 DB 连接（或至少返回明确错误告知运维需要重启服务）。

### M4 — 种子用户硬编码在 `business_demo/storage.py` 中

**文件**: `business_demo/storage.py:141-156`

```python
def _seed_users(self):
    seeds = [
        ("100001", "GAOFEI", "GAOFEI", "IT"),
        ("100002", "DEMO_ADMIN", "Demo Admin", "Ops"),
        ("100003", "VISITOR_01", "Visitor 01", "Guest"),
    ]
```

种子数据在 demo 场景下合理，但如果有人将 `business_demo` 的 `storage.py` 直接复用或误部署到类生产环境，这些预置账号会成为事实上的后门（`GAOFEI` 账号在 `face_api` 人脸库注册后即可登录）。当前有 `BUSINESS_DEMO_ENV=production` 拒绝默认 token secret 的保护，但没有阻止种子用户被创建。

**建议**: 当 `BUSINESS_DEMO_ENV=production` 时跳过 `_seed_users()`，或至少输出 warning 日志。

---

## 安全检查清单

| 检查项 | 状态 | 说明 |
|---|---|---|
| 硬编码密钥/密码 | ✅ 通过 | `business-demo-dev-secret` 在 production 模式被拒绝 |
| API Key 鉴权绕过 | ✅ 通过 | 强制鉴权路由使用 `require_api_key`，条件鉴权路由使用 `verify_api_key` |
| 路径遍历（备份恢复） | ✅ 通过 | `admin_ops.restore_db_files` 已验证备份路径在 `backups/` 下 |
| SQL 注入 | ✅ 通过 | 所有查询使用参数化 SQL（`?` placeholder） |
| XSS | ✅ 通过 | 纯 API 服务，无 HTML 渲染 |
| 日志泄露敏感数据 | ⚠️ 见 H1 | 脱敏仅处理顶层字段 |
| 图片上传 DoS | ✅ 通过 | `MAX_IMAGE_BYTES` / `MAX_IMAGE_PIXELS` / `MAX_BASE64_IMAGE_CHARS` 三重限制 |
| CSRF | N/A | API 服务，使用 `X-API-Key` 鉴权 |
| CORS 配置 | ✅ 通过 | Production 模式禁止 `*`，强制配置明确来源 |
| 维护模式安全操作 | ✅ 通过 | restore 要求 maintenance_mode + 二次确认 |
| Token 签名安全 | ✅ 通过 | HMAC-SHA256 + `compare_digest` + production 强制替换默认密钥 |
| 速率限制 | ⚠️ 未实现 | 当前无 rate limiting，高并发下 `POST /auth/face-login` 可被暴力调用 |
| 依赖版本 | ✅ 通过 | `numpy<2.0` 锁定，避免 ONNX Runtime 兼容性问题 |
