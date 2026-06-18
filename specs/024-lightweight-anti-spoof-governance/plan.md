# 实施计划：轻量防翻拍阈值治理与中风险重试机制

**分支/目录**：`024-lightweight-anti-spoof-governance`

**日期**：2026-06-17

## 技术上下文

- 后端：FastAPI `main.py` 现有活体、risk scoring 和 face login 链路。
- 配置：`app_config.py` 现有 `FACE_ANTI_SPOOF_*` 配置。
- 错误：`api_errors.py` 统一维护结构化错误码和中文原因。
- 存储：`storage.py` 现有 login audit、`anti_spoof_risk` JSON 字段和 `liveness_challenges` 表；V2.3 优先在现有 challenge/audit 存储上增加 retry token 状态，不新增独立业务表。
- 页面：`camera-integration.html` 和 `acceptance.html` 使用原生 HTML/CSS/JS。
- 业务接入：`business-demo` 和 Java / Spring Boot 文档需要说明中风险默认不是登录成功。
- 测试：`unittest`，重点使用 `tests/test_main_api.py`、`tests/test_app_config.py`、`tests/test_scripts_smoke.py`、`tests/test_business_demo.py`。

## 约束

- 不引入重型 anti-spoofing 模型。
- 不引入 PyTorch。
- 不新增复杂动作作为默认流程。
- 不保存原图、连续帧或 embedding。
- 不改变 `X-API-Key` 鉴权规则。
- 不新增独立数据库表，优先复用现有 audit JSON 字段。
- 不把中风险无限重试。
- 不依赖前端 `state`、浏览器本地变量或业务端自报次数判断重试次数。
- 不用 similarity 阈值替代防翻拍风险治理。

## 服务端重试判定设计

V2.3 采用后端签发的 `risk_retry_token` 作为“最多重试 1 次”的权威依据。

默认流程：

1. 第一次 `/auth/face-login` 触发中风险，且 `FACE_ANTI_SPOOF_MEDIUM_ACTION=retry`。
2. 后端写入失败 login audit，生成一次性 `risk_retry_token`，返回中风险重试错误和固定 `detail.retry` 结构。
3. 前端或 Java 业务端重新采集活体和登录图片，第二次调用 `/auth/face-login` 时携带新的 `challenge_id` 和该 `risk_retry_token`。
4. 后端校验 token 是否存在、未过期、未使用、绑定同一 `terminal_id` 和 login 重试组。
5. 第二次为低风险则可继续匹配并登录；第二次仍为中风险或高风险则失败或进入复核，不再签发新的 retry token。

错误响应契约：

```json
{
  "detail": {
    "code": "ANTI_SPOOF_MEDIUM_RETRY_REQUIRED",
    "message": "检测到中风险，请重试一次",
    "reason": "当前画面存在轻量防翻拍中风险，请重新面对摄像头完成一次采集",
    "retry": {
      "risk_retry_token": "<opaque-token>",
      "expires_at": "2026-06-17T12:00:00Z",
      "remaining_attempts": 1
    }
  }
}
```

`risk_retry_token` 不透明，客户端只能保存并在下一次 `/auth/face-login` 中原样回传；`expires_at` 使用 UTC ISO 8601；`remaining_attempts` 表示本次响应后还允许的中风险重试次数。V2.3 默认最多 1 次，第二次仍中风险时不得再签发新 token。测试必须断言 `detail.retry.risk_retry_token`、`detail.retry.expires_at`、`detail.retry.remaining_attempts` 的存在和语义。

实现建议：

- `FaceLoginReq` 增加可选 `risk_retry_token` 字段，保持向后兼容。
- token 使用高熵随机值；数据库只保存 token hash 或不可逆摘要。
- token 状态绑定到 `liveness_challenges` 或同等后端持久记录，包含 `terminal_id`、`retry_group_id`、`retry_count`、`expires_at`、`used_at`。
- `state` 只作为前端追踪字段，不参与服务端重试次数判定。
- 原始 token 不进入 audit、验收 JSON/CSV 或日志；如需审计只记录 retry 状态、过期时间和摘要后缀。

配置决策：

- `FACE_ANTI_SPOOF_MEDIUM_ACTION=retry`：默认中风险处理策略。可选值限定为 `retry`、`review`、`block`；V2.3 验收使用默认 `retry`。
- `FACE_ANTI_SPOOF_RETRY_TOKEN_TTL_SECONDS=300`：retry token 有效期，必须为正整数，建议保持在 60-600 秒。
- V2.3 不新增 `FACE_ANTI_SPOOF_MEDIUM_MAX_RETRIES`。最大重试次数固定为 1，避免现场把安全边界配置得过宽。

## 文件变更计划

- 修改 `app_config.py`：增加或调整 `FACE_ANTI_SPOOF_MEDIUM_ACTION`、`FACE_ANTI_SPOOF_RETRY_TOKEN_TTL_SECONDS` 配置解析和启动校验；最大重试次数固定为 1。
- 修改 `api_errors.py`：增加 `ANTI_SPOOF_MEDIUM_RETRY_REQUIRED` 错误码、中文原因和可携带 `retry` 元数据的错误构造方式。
- 修改 `storage.py`：保存并校验后端签发的中风险重试 token 状态。
- 修改 `api_schemas.py`：为 `/auth/face-login` 增加可选 `risk_retry_token` 请求字段，并在错误文档中说明 token 返回语义。
- 修改 `main.py`：增强轻量评分逻辑和 `/auth/face-login` 中风险处理。
- 修改 `camera-integration.html`：展示中风险重试提示。
- 修改 `acceptance.html`：报告中区分中风险重试和普通失败。
- 修改 `business_demo` 相关文档或代码：中风险 retry 时提示“请重试一次”，第二次仍中风险时显示失败或人工处理，不把 retry 错误当作登录成功。
- 修改 `README.md`：同步 V2.3 新增或默认值变化的环境变量说明。
- 修改 `docs/04_usage/01_api_integration.md`、`docs/04_usage/03_recognition_security_accuracy.md`、`docs/04_usage/05_spring_boot_integration_notes.md`。
- 修改 `architecture.html`：同步 V2.3 风险治理说明。
- 完成 `docs/90_archive/04_acceptance/07_v2.3_acceptance_record.md`。

## 实施策略

1. 先补失败测试，复现 V2.2 报告中的翻拍低风险成功和中风险放行问题。
2. 增加配置解析和启动校验，默认中风险动作为 `retry`，retry token TTL 默认 300 秒，最多重试固定 1 次。
3. 增加后端 retry token 存储和校验，确保重试次数不由客户端决定。
4. 调整轻量风险评分，减少 `normal_motion` 对移动照片和屏幕的误判。
5. 在 `/auth/face-login` 中按策略处理中风险。
6. 同步前端、business-demo 页面提示和验收报告语义。
7. 同步 README、使用文档、Java 接入说明、架构图和验收记录。

## 验证计划

- 聚焦测试：
  - `D:\anaconda3\envs\face_api\python.exe -m unittest tests.test_app_config tests.test_main_api -v`
  - `D:\anaconda3\envs\face_api\python.exe -m unittest tests.test_scripts_smoke tests.test_business_demo -v`
- 全量测试：
  - `D:\anaconda3\envs\face_api\python.exe -m unittest discover -s tests -v`
- 语法编译：
  - `D:\anaconda3\envs\face_api\python.exe -m compileall main.py app_config.py api_errors.py api_schemas.py storage.py business_demo tests scripts`
- 静态检查：
  - `git diff --check`
  - HTML 外部依赖扫描：`rg -n "cdn|script src|link rel=.*stylesheet|import |require\(" -g "*.html" .`
- 手工验收：
  - 使用 `acceptance.html` 按五类样例每类 3 次复验。

## 风险和缓解

- 风险：阈值过严导致真人误拒。缓解：验收标准要求真人至少 2/3 通过，并保留中风险一次重试。
- 风险：配置过多让现场难理解。缓解：默认策略固定为后端强制重试，文档只解释常用策略。
- 风险：前端和业务后端理解中风险不一致。缓解：统一错误码、audit 字段和 Java 接入说明。
