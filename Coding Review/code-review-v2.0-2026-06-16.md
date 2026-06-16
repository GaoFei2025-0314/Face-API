# Code Review Report — face_api V2.0

**日期**：2026-06-16
**Commit**：`608d0d5` — fix: v2.0
**变更文件**：17 个文件

### 变更文件列表

| 模块 | 文件 |
|---|---|
| 核心存储 | `storage.py` |
| 业务 Demo | `business_demo/app.py` |
| 脚本 | `scripts/post-commit` |
| 测试 | `tests/test_business_demo.py`, `tests/test_storage_schema.py` |
| Spec | `specs/022-lightweight-anti-spoofing/spec.md`, `specs/022-lightweight-anti-spoofing/plan.md`, `specs/022-lightweight-anti-spoofing/research.md`, `specs/022-lightweight-anti-spoofing/data-model.md`, `specs/022-lightweight-anti-spoofing/contracts/api-contract.md`, `specs/022-lightweight-anti-spoofing/quickstart.md`, `specs/022-lightweight-anti-spoofing/checklists/requirements.md`, `specs/README.md`, `specs/ROADMAP-v2.1.md` |
| 配置/索引 | `.specify/feature.json`, `AGENTS.md` |

---

## CRITICAL

暂无。

---

## HIGH

暂无。

---

## MEDIUM

### M1 — `storage.py:631`：f-string 拼接 SQL WHERE 子句，模式脆弱

**位置**：`storage.py:631`（`list_login_audits` 方法）

**问题描述**：

```python
where_sql = f"WHERE {' AND '.join(where)}" if where else ""
```

当前 `where` 列表元素均为硬编码字符串（`"success = ?"`、`"terminal_id = ?"`），参数值通过 `(*params, safe_limit)` 参数化传入，实际不存在注入风险。

但该模式容易在后续扩展时被误用——如果有人新增过滤条件时直接将用户输入拼入 `where.append(f"username = '{user_input}'")`，就会引入 SQL 注入。f-string 拼接 SQL 片段本身就是一种值得警惕的信号，暗示了"字符串拼 SQL"的思维惯性。

**修复建议**：

在方法上方添加注释，明确标注安全边界：

```python
# 安全约束：where 列表只能追加硬编码的 "column = ?" 片段；参数值通过 params 列表参数化。
# 禁止将任何外部输入拼入 where 片段。
def list_login_audits(self, limit: int = 20, ...):
```

当前规模下注释即可，无需重构。

---

### M2 — `scripts/post-commit:42`：git 提交信息未经过滤直接传入 Claude prompt

**位置**：`scripts/post-commit:16,42`

**问题描述**：

```bash
COMMIT_MSG="$(git log -1 --format='%s')"
# ...
nohup claude -p "$CLAUDE_PROMPT" > /dev/null 2>&1 &
```

`COMMIT_MSG`、`CHANGED_FILES`、`VERSION`（从 `README.md` 提取）均来自 git 仓库内容，未经过滤直接拼入 `CLAUDE_PROMPT`，然后传给 `claude -p` 执行。如果仓库接受非受信贡献，攻击者可在 commit message 或 README 中嵌入 prompt injection 指令。

**实际风险**：低。当前为单人本地仓库 + 本地 post-commit hook，且 Claude 被约束为"只读变更文件列表中的文件"。如果仓库未来开放外部协作，风险会上升。

**修复建议**：

对注入 prompt 的外部字段做截断：

```bash
COMMIT_MSG="$(git log -1 --format='%s' | head -c 200)"
sanitize() { echo "$1" | head -c 500; }
```

---

### M3 — `business_demo/app.py:219–232`：`unbind_face` 删除 face_api 侧人脸失败时静默降级，无后续清理机制

**位置**：`business_demo/app.py:219–232`

**问题描述**：

```python
try:
    client.delete_face(removed["face_id"])
except BusinessDemoError as exc:
    db.mark_binding_pending_cleanup(removed["id"], reason=exc.code)
    cleanup_status = "pending_cleanup"
```

当 face_api 不可用时，binding 被标记为 `pending_cleanup` 并从业务侧逻辑删除，但 face_api 侧的人脸记录未被物理删除。长期运行会积累孤儿人脸记录，导致 face_api 人脸库膨胀、search 性能下降。

**实际风险**：低。不影响业务正确性，但需运维关注。

**修复建议**：后续版本增加后台定时任务，重试 `pending_cleanup` 状态的清理操作；或在运维文档中说明需定期手动审计。

---

### M4 — `business_demo/app.py:288–339`：`face_login` 将 `challenge_id` 透传给 face_api 但不做本地预校验

**位置**：`business_demo/app.py:290–297`

**问题描述**：

```python
face_result = client.face_login({
    "image": req.image,
    "terminal_id": req.terminal_id,
    "challenge_id": req.challenge_id,
    ...
})
```

`challenge_id` 直接透传给 face_api，业务 demo 不验证 challenge 是否真实存在、是否已被消费、是否属于当前 terminal。完全信任 face_api 的验证结果。

**实际风险**：低。这是"业务 demo 是 thin proxy"的架构设计决策——活体验证的权威来源是 face_api。但如果 face_api 的 challenge 验证存在缺陷（例如接受任意 `challenge_id`），业务 demo 会跟着放行。

**修复建议**：在业务接入文档中明确声明：业务系统必须信任 face_api 的 challenge 验证结果；如需独立验证，可在业务侧额外查询 challenge 状态。

---

## 正向确认

以下变更属于安全加固 / 质量提升，确认无问题：

| 变更 | 文件 | 说明 |
|---|---|---|
| token 签名不再写入 audit | `business_demo/app.py:330` | `issued_token_id` 从 HMAC 签名片段改为 `uuid.uuid4().hex`（上轮 M4 已修复） |
| face_api_result 先于时间校验 | `business_demo/app.py:365-367` | 终端事件入口先校验 `face_api_result` 结构，通过后才进入时间窗口校验（上轮 M3 已修复） |
| logger 命名空间修正 | `storage.py:21` | 改为 `logging.getLogger("face_api")`，与 main.py 统一，checkpoint 错误可写入 `face_api.log`（上轮 M1 已修复） |
| 人脸库表结构迁移 | `storage.py:117-143` | `liveness_status`、`liveness_reason`、`quality_metrics`、`face_embedding`、`created_at_epoch` 列的条件式新增，向后兼容 |
| liveness_challenges 表 | `storage.py:97-112` | 新增 challenge 持久化，含过期时间和状态机（pending → passed/failed → used） |
| consume 事务原子化 | `storage.py:503-565` | `BEGIN IMMEDIATE` + 多条件 WHERE 防竞态消费 |
| login audit 审计表 | `storage.py:79-96,575-619` | 完整记录 login 结果、活体状态、质量指标，支持按 terminal 过滤 |
| 终端事件幂等 | `business_demo/app.py:401-422` | `IntegrityError` → 返回已有 audit 记录 |
| 终端事件时间窗口 | `business_demo/app.py:369-374` | 拒绝未来时间（5s 容差）和超过 120s 的过期事件 |
| 生产环境密钥阻断 | `business_demo/app.py:55-58` | `BUSINESS_DEMO_ENV=production` 时拒绝默认/空 `token_secret` |
| 测试覆盖 | `tests/test_business_demo.py`, `tests/test_storage_schema.py` | 存储 schema、终端事件、解绑降级、token 防篡改、迁移去重等场景 |

---

## 安全检查清单

| 检查项 | 状态 | 说明 |
|---|---|---|
| 密钥硬编码 | 通过 | `token_secret` 有 production 启动阻断 |
| SQL 注入 | 通过 | 全部参数化查询；`where_sql` 列名部分来自硬编码列表（见 M1） |
| XSS | 通过 | JSON API，无 HTML 渲染用户输入 |
| 路径穿越 | 通过 | `backup_to` 依赖调用方校验，不在本次变更范围 |
| 输入校验 | 通过 | Pydantic 模型校验请求体；终端事件时间窗口硬限制 |
| 日志敏感信息 | 通过 | audit 不记录原始图片、embedding 或连续帧 |
| 幂等性 | 通过 | `terminal_event_id` + UNIQUE INDEX + `IntegrityError` |
| 竞态条件 | 通过 | `consume_liveness_challenge` 使用 `BEGIN IMMEDIATE` |
| 认证绕过 | 通过 | `face_login` 必须 face_api 返回 `authenticated: true` |
| Token 安全 | 通过 | HMAC-SHA256 + `compare_digest` + TTL 过期 |
| 错误信息泄露 | 通过 | 返回 `detail.code/message/reason`，不暴露堆栈 |
| 依赖安全 | 通过 | 未新增外部依赖 |
