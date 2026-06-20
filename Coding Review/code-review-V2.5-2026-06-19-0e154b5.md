# Code Review Report — face_api V2.5

**日期**：2026-06-19
**提交**：`0e154b5` — v2.4澄清wms是内置算法
**变更文件**：

- `Coding Review/code-review-V2.5-2026-06-18-222ceb0.md`
- `Coding Review/code-review-V2.5-2026-06-18-ca1f9cc.md`
- `docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md`
- `docs/90_archive/05_development_records/README.md`
- `specs/025-wms-capture-loop-baseline/spec.md`
- `specs/ROADMAP-v2.4.md`

---

## CRITICAL

无。

---

## HIGH

无。

---

## MEDIUM

### M1 — `08_face_api_wms_capture_loop_baseline.md` 第 2 节：上一轮 M4 建议未在本提交中修复

**问题描述**：

上一轮评审（`code-review-V2.5-2026-06-18-ca1f9cc.md`）的 M4 指出：验收模板第 2 节定义了"禁止写入"的安全边界，但缺少**填写完成后的验收记录本身该如何处理**的指引。本提交对第 1 节做了大幅改写（流程图改为三阶段、新增 WMS 内置算法说明），但第 2 节未触及，M4 的建议仍未落地。

填写后的模板会包含环境配置、终端编号、摄像头型号、网络状态、问题证据——这些信息组合起来可能暴露现场部署细节。

**修复建议**：在第 2 节末尾增加一条：

```markdown
- 填写完成的验收记录本身属于内部运维文档，不得外传到项目仓库之外的公开渠道。
```

`docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md` 第 2 节

---

## 变更评价

本提交是纯文档澄清提交，核心变更只有一个主题：**明确 WMS 当前使用内置人脸识别算法，尚未接入 face_api REST API**。改动覆盖了验收模板、spec、roadmap 三份文档的对应段落，措辞一致。

具体变更：

| 文件 | 变更内容 |
|------|----------|
| `08_face_api_wms_capture_loop_baseline.md` | 第 1 节新增"当前真实基线"三点说明；流程图从单链改为三阶段（WMS 内置识别 → Face API 独立验收 → 对比归因）；验收重点从"证明闭环"改为"对齐基线，不宣称已调用" |
| `spec.md` | 新增"当前 WMS 基线"声明；新增一条 Clarification Q&A（WMS 是否已接入 face_api）；范围边界末尾追加"不把 WMS 改造成调用 face_api 的模式" |
| `ROADMAP-v2.4.md` | 流程图同步改为三阶段；新增"不宣称 WMS 已经调用 face_api"；已确认决策新增 WMS 内置算法说明 |
| `development_records/README.md` | 新文件，定义开发记录命名规则和内容要求，明确禁止写入敏感信息 |
| 两份 code-review md | 上一轮评审结果归档入库 |

**评价**：

- 三份文档的措辞一致性好："WMS 内置人脸识别算法" / "尚未接入 face_api REST API" / "不宣称已调用" 在验收模板、spec、roadmap 中表述统一。
- `development_records/README.md` 内容简洁，安全条款（禁止写入 API Key、token、原图等）到位。
- 流程图从单链改为三阶段后，WMS 内置识别和 Face API 独立验收的边界比原来清晰得多。
- 代码评审文件归档到 `Coding Review/` 目录是合理的项目文档管理实践，文件中不含敏感信息。

---

## 安全检查清单

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 密钥/Token 硬编码 | ✅ | 纯文档变更，无新增代码；文档中无真实密钥 |
| 敏感路径暴露 | ✅ | 文档中的路径（`H:\AI_test\...`）为开发工作站本地路径，属项目内部文档预期范围 |
| 用户敏感信息 | ✅ | `development_records/README.md` 明确禁止写入 API Key、token、原图、视频帧、embedding、真实用户敏感信息 |
| API Key 传输安全 | N/A | 无代码变更 |
| 鉴权绕过风险 | ✅ | 未修改鉴权规则 |
| SQL 注入 | N/A | 无 SQL 变更 |
| XSS 防护 | N/A | 无前端代码变更 |
| 审计日志泄露 | ✅ | 验收模板安全边界明确禁止写入 audit 原始 token |
| 跨仓库提交隔离 | ✅ | roadmap 和 spec 明确区分 Face API 和 WMS 仓库范围 |
| 文档一致性 | ✅ | "WMS 内置算法"措辞在验收模板、spec、roadmap 中统一 |
| 依赖安全 | N/A | 未引入新依赖 |

---

## 总结

| 级别 | 数量 |
|------|------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 1 |

本提交是干净的文字澄清提交，改动聚焦、措辞一致。1 个 MEDIUM 为上一轮已识别但未在本提交中修复的遗留项，建议在下次编辑验收模板时顺手处理。
