# Code Review Report — face_api V2.5

**审查日期**：2026-06-19  
**提交哈希**：`79d9863`  
**提交信息**：docs: complete v2.5 general integration service baseline  
**审查范围**：仅本次提交变更的文件（全部为文档/spec 文件）

**变更文件列表**：

| 文件 | 变更类型 |
|------|----------|
| `.specify/feature.json` | 修改（指针更新） |
| `AGENTS.md` | 修改（规范细化 + 指针更新） |
| `README.md` | 修改（版本基线同步） |
| `docs/01_document_index.md` | 修改（新增 V2.5 索引） |
| `docs/02_product/02_quarterly_plan.md` | 修改（新增 V2.5 章节） |
| `docs/04_usage/06_general_integration_contract.md` | **新增**（通用接入契约） |
| `docs/90_archive/04_acceptance/09_v2.5_acceptance_record.md` | **新增**（验收记录） |
| `docs/superpowers/specs/2026-06-19-v2.5-general-integration-service-baseline-design.md` | **新增**（设计文档） |
| `specs/026-general-integration-service-baseline/spec.md` | **新增**（功能规格） |
| `specs/026-general-integration-service-baseline/plan.md` | **新增**（实施计划） |
| `specs/026-general-integration-service-baseline/quickstart.md` | **新增**（快速入门） |
| `specs/026-general-integration-service-baseline/tasks.md` | **新增**（任务清单） |
| `specs/README.md` | 修改（新增 V2.5 入口） |
| `specs/ROADMAP-v2.5.md` | **新增**（V2.5 路线图） |

---

## CRITICAL

无。

---

## HIGH

无。

---

## MEDIUM

### M1 · 验证命令硬编码绝对路径，不可移植

**文件**：`specs/026-general-integration-service-baseline/plan.md:120-163`  
**问题**：验证脚本中的 `Test-Path` 和 `Select-String` 命令全部使用硬编码的绝对路径 (`H:\AI_test\face_api\...`)，以及 Python 解释器路径 (`D:\anaconda3\envs\face_api\python.exe`)。这些路径仅在该开发机上有效，其他环境或 CI 中无法直接复用。

**建议**：将路径替换为相对路径或项目根变量（如 `$repoRoot`），Python 路径改用 `venv\Scripts\python.exe` 或 `python`（依赖 PATH）。如果这是 spec-kit 文档的内部验证脚本，至少应在文档顶部注明"以下命令假设工作区根目录为 `H:\AI_test\face_api`"。

### M2 · ROADMAP 子版本划分逻辑不一致

**文件**：`specs/ROADMAP-v2.5.md:52-58`  
**问题**：V2.5.1 至 V2.5.5 五个子版本全部指向同一个 spec 目录 `specs/026-general-integration-service-baseline`。这种结构意味着子版本只是逻辑拆解而非独立交付单元，但 ROADMAP 使用了"子版本"（semantic sub-version）的表述，读者可能期望每个子版本有独立的 spec 目录或分支。

**建议**：如果这五个子版本属于同一交付批次，改为"交付范围"或"功能模块"的表述即可，避免与 Git 分支/版本号体系产生歧义。

### M3 · 通用接入契约缺少 TLS/HTTPS 安全传输指引

**文件**：`docs/04_usage/06_general_integration_contract.md:72-98`  
**问题**：通用契约定义了"受控终端直连模式"，允许 Electron / 一体机 / 闸机通过网络直连 `face_api`。文档中所有示例均使用 `http://localhost:8000`，未提及当直连发生在真实网络环境下时，是否应启用 HTTPS/TLS 保护传输中的 `X-API-Key` 和活体帧数据。虽然当前定位为本地/边缘服务，但契约中"受控终端直连"场景已隐含跨网络调用。

**建议**：在 §2.2 或 §8 中增加一句说明："内网环境建议在网络层完成安全隔离；如跨网段使用，应在反向代理层启用 HTTPS。"

### M4 · quickstart 中排障入口引用的端点未做存在性说明

**文件**：`specs/026-general-integration-service-baseline/quickstart.md:204-206`  
**问题**：quickstart 中引用了 `/system/status` 和 `/config/effective` 两个端点，但这两个端点未在 CLAUDE.md（项目介绍文档）中列出。经核实，这两个端点确实存在于 `main.py` 中（行 893、899），但 CLAUDE.md 的路由列表已过期——新读者如果先看 CLAUDE.md 再看 quickstart，会以为文档引用了不存在的端点。

**建议**：这不是本提交的问题，但建议在后续提交中同步更新 CLAUDE.md 的路由表格，添加 `/system/status`、`/config/effective`、`/audit/login/recent` 等端点说明，避免文档之间的认知偏差。

---

## 安全性检查清单

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 是否包含硬编码密钥/密码 | ✅ 通过 | `123456`、`your-secret` 均为明确的示例占位符 |
| 是否暴露敏感端点细节 | ✅ 通过 | audit 端点引用合理，未暴露内部数据结构 |
| API Key 管理指导是否安全 | ✅ 通过 | 明确禁止浏览器保存 Key，区分三种存放策略 |
| Token 安全处理规则 | ✅ 通过 | `risk_retry_token` 标记为不透明、不可解析、不可记录明文 |
| 鉴权职责边界是否清晰 | ✅ 通过 | 明确 session/JWT/SSO 由业务系统签发，`face_api` 不接管 |
| 文档中是否有敏感内部路径 | ⚠️ 注意 | plan.md 含开发机绝对路径（见 M1），不涉及生产敏感信息 |
| 是否引用了不存在的安全配置 | ✅ 通过 | `FACE_USE_GPU`、`FACE_FORCE_CPU` 均在代码中存在 |
| 错误信息是否避免泄露内部状态 | ✅ 通过 | 错误码设计合理，`detail.message/reason` 均为前端可展示的中文 |

---

## 总体评价

本次提交是一次纯文档交付，1106 行新增内容全部为 Markdown 文档和 spec-kit 文件。文档质量整体良好：

- **接入模式划分清晰**：业务后端代理 / 受控终端直连 / 本地运维验收三种模式定义明确，API Key 存放策略合理。
- **安全设计意识到位**：明确拒绝浏览器持有 Key、`risk_retry_token` 不透明处理、业务 token 职责分离——这些安全决策在文档中表达一致且不模棱两可。
- **边界表达干脆**：反复强调 V2.5 不新增 API、不新增 SDK、不改 WMS、不做多租户——有助于防止范围蔓延。
- **Medum 问题主要是可移植性和文档一致性**：无安全硬伤，无逻辑错误。
