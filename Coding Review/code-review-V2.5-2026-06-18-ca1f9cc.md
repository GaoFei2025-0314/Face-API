# Code Review Report — face_api V2.5

**日期**：2026-06-18
**提交**：`ca1f9cc` — docs: add v2.4 wms capture loop baseline
**审阅范围**：仅审阅本次提交变更的文档文件，不涉及运行时代码

**变更文件列表**：

| # | 文件 |
|---|------|
| 1 | `docs/01_document_index.md` |
| 2 | `docs/02_product/02_quarterly_plan.md` |
| 3 | `docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md` |
| 4 | `specs/025-wms-capture-loop-baseline/plan.md` |
| 5 | `specs/025-wms-capture-loop-baseline/quickstart.md` |
| 6 | `specs/025-wms-capture-loop-baseline/spec.md` |
| 7 | `specs/025-wms-capture-loop-baseline/tasks.md` |
| 8 | `specs/README.md` |
| 9 | `specs/ROADMAP-v2.4.md` |

---

## 总体评价

本次提交是纯文档变更，建立 V2.4 Face API 与 WMS 现场联动验收基线。文档结构完整、spec/plan/tasks 三层对齐良好、安全边界声明清晰、跨仓库提交命令做了隔离处理。

未发现 CRITICAL 或 HIGH 级别问题。以下为 MEDIUM 级别问题。

---

## MEDIUM

### M1 — `quickstart.md:57`：`Select-String` 模式拼接错误，验证命令无法生效

**问题描述**：

```powershell
Select-String -LiteralPath 'H:\AI_test\electron-wms\electron-wms\tests\face-service-runtime.test.js' -Pattern 'env.FACE_API_KEY, service.apiKey' -SimpleMatch
```

`-Pattern` 接收的是一个**单字符串** `'env.FACE_API_KEY, service.apiKey'`（逗号在引号内，是字符串字面量的一部分），配合 `-SimpleMatch` 会把它当成**一个完整字面量**去搜索。

而测试文件中的断言大概率是类似 `expect(env.FACE_API_KEY).toEqual(service.apiKey)` 的形式，不会包含 `env.FACE_API_KEY, service.apiKey` 这个完整字面量，导致无论测试文件是否正确，这条验证命令都不会匹配到任何结果。

作为对比，前一行的命令是正确的（数组形式的两个独立模式）：

```powershell
# 正确：两个独立模式
Select-String ... -Pattern 'FACE_API_KEY: this.apiKey','x-api-key' -SimpleMatch
```

**修复建议**：将单字符串拆成数组，使两个模式独立匹配：

```powershell
Select-String -LiteralPath 'H:\AI_test\electron-wms\electron-wms\tests\face-service-runtime.test.js' -Pattern 'env.FACE_API_KEY','service.apiKey' -SimpleMatch
```

`quickstart.md:57`

---

### M2 — `quickstart.md:28`：文档中硬编码了弱示例 API Key

**问题描述**：

```powershell
$env:FACE_API_KEY="123456"
```

Quickstart 文档中把 API Key 设为 `123456`。虽然是开发/演示场景，但这个值过于简单，可能被阅读者直接复制到生产环境。

**修复建议**：使用明确的占位符，并加一句说明：

```powershell
# 开发环境用简单值即可，生产环境请替换为随机字符串
$env:FACE_API_KEY="dev-demo-key-change-in-production"
```

`quickstart.md:28`

---

### M3 — `quickstart.md:100-103`、`plan.md:130-134`：扫描词刻意拆分，意图不直观

**问题描述**：

```powershell
$scanTerms = @(
  ('TB' + 'D')
  ('TO' + 'DO')
  ('待' + '定')
  ('占' + '位')
)
```

将 `TBD` 拆成 `'TB' + 'D'`、`TODO` 拆成 `'TO' + 'DO'` 是为了避免扫描脚本匹配到自身的源码。这是实用技巧，但没有任何注释说明意图，后续维护者容易误以为这是笔误而"修复"回去，导致扫描脚本匹配到自身产生假阳性。

**修复建议**：加一行简短注释说明拆分原因：

```powershell
# 拆分以避免扫描脚本匹配到自身
$scanTerms = @(
  ('TB' + 'D')
  ('TO' + 'DO')
  ('待' + '定')
  ('占' + '位')
)
```

`quickstart.md:100`、`plan.md:130`

---

### M4 — `08_face_api_wms_capture_loop_baseline.md`：验收模板缺少填写后的处理指引

**问题描述**：

验收模板的第 2 节定义了"禁止写入"的安全边界（不保存原图、embedding、API Key 等），但**没有说明填写完成后的验收记录本身该如何处理**。填写后的模板会包含环境配置、终端编号、摄像头型号、网络状态、问题证据——这些信息组合起来可能暴露现场部署细节。

**修复建议**：在第 2 节末尾增加一条：

```markdown
- 填写完成的验收记录本身属于内部运维文档，不得外传到项目仓库之外的公开渠道。
```

`docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md` 第 2 节

---

## 安全检查清单

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 密钥/Token 硬编码 | ⚠️ 通过 | quickstart 中有弱示例 key `123456`（见 M2），非生产代码 |
| 敏感路径暴露 | ✅ 通过 | 文档中的路径为开发工作站本地路径，属预期范围内的文档引用 |
| 用户敏感信息 | ✅ 通过 | 验收模板明确禁止保存原图、embedding、API Key、真实姓名等 |
| API Key 传输安全 | ✅ 通过 | quickstart 正确记录了 WMS 端 `FACE_API_KEY` → `x-api-key` 的注入和对齐机制 |
| 鉴权绕过风险 | ✅ 通过 | 未新增公开端点，未修改鉴权规则 |
| 跨仓库提交隔离 | ✅ 通过 | tasks.md 明确区分 Face API 和 WMS 仓库的提交命令，禁止 `git add .` |
| 审计日志泄露 | ✅ 通过 | 验收模板明确 audit 和报告不得导出原始 token |
| 文档引用完整性 | ✅ 通过 | `docs/superpowers/` 引用路径经确认在仓库中存在 |

---

## 总结

| 级别 | 数量 |
|------|------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 4 |

本次提交为纯文档基线，无运行时代码变更。4 个 MEDIUM 问题均为文档质量改进建议，不影响安全性或正确性。建议在下次编辑相关文件时顺手修复 M1（验证命令 bug），其余可以随迭代自然收敛。
