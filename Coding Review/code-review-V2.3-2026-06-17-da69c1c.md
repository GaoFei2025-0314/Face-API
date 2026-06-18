# Code Review Report — face_api V2.3

**日期**: 2026-06-17  
**提交**: `da69c1c` — docs: add face api wms capture loop design  
**变更文件**:
- `docs/superpowers/specs/2026-06-17-face-api-wms-capture-loop-design.md`（新增 253 行）

---

## 概述

本次提交为纯设计文档，无执行代码。以下发现聚焦于设计层面的安全缺口和完整性不足，不涉及代码级缺陷。

---

## MEDIUM

### M1 — 数据流缺少认证环节

**文件**: `docs/superpowers/specs/2026-06-17-face-api-wms-capture-loop-design.md:161-171`  
**问题**: 第 5 节标准联动数据流描述了 WMS → Face API → WMS 的完整调用链，但完全省略了 API 认证步骤。根据项目现有实现，`face_api` 通过 `X-API-Key` 头进行认证（当 `FACE_API_KEY` 环境变量已设置时），这是整条链路的安全入口。

当前数据流：
```
WMS 摄像头采集 → WMS 本地预检查 → Face API 检测/活体/登录辅助 → ...
```

缺失的关键节点：WMS 携带 API Key 发起请求、Face API 校验 API Key、认证失败时的错误返回。

**建议**: 在数据流图中插入认证步骤，例如：
```
WMS 摄像头采集
-> WMS 本地预检查
-> WMS 附加 X-API-Key 发起请求        ← 补充
-> Face API 校验 API Key               ← 补充
-> Face API 检测/活体/登录辅助
-> Face API 返回结构化结果
-> ...
```

---

### M2 — 归因规则表缺少认证失败场景

**文件**: `docs/superpowers/specs/2026-06-17-face-api-wms-capture-loop-design.md:190-198`  
**问题**: 第 6 节错误归因规则表覆盖了无人脸、匹配失败、翻拍误放、WMS 提示不清、耗时异常等场景，但没有覆盖 API Key 缺失/错误/过期导致的认证失败。这类失败在联动调试阶段是高频问题（尤其是首次部署或环境变更后），缺少归因规则会导致排查方向错误。

**建议**: 在归因表中新增一行：

| 现象 | 优先归因 |
|---|---|
| Face API 返回 401/403 | WMS 配置的 `X-API-Key` 是否正确、Face API 的 `FACE_API_KEY` 环境变量是否已设置 |

---

### M3 — 验收 Trace 未包含 API Key 配置验证

**文件**: `docs/superpowers/specs/2026-06-17-face-api-wms-capture-loop-design.md:107`  
**问题**: 第 4.2 节现场验收 Trace 步骤 1 要求"启动 Face API 并记录配置"，但没有明确要验证 API Key 是否已配置、与 WMS 端是否一致。根据设计原则第 4 条（"Face API 的接口语义和 WMS 的终端表现必须一起验收"），认证配置应属于验收范围。

**建议**: 将步骤 1 细化为：`启动 Face API 并记录配置（包括 FACE_API_KEY 设置状态、模型名称、det_size、GPU/CPU 模式）`。

---

### M4 — 关键字段表缺少认证相关字段

**文件**: `docs/superpowers/specs/2026-06-17-face-api-wms-capture-loop-design.md:175-184`  
**问题**: 第 5 节关键字段表列出了 `terminal_id`、`event_id`、`similarity`、`risk_level`、`failure_reason` 等联动审计字段，但没有认证相关字段（如 `auth_status`、`api_key_hash`）。当出现认证失败或 API Key 泄漏排查时，缺失这些字段会导致无法追溯。

**建议**: 考虑补充一个可选的审计字段，例如 `auth_status`（success/failure/skipped），用于复盘时确认认证链路是否正常。

---

### M5 — 验收成功标准中"低风险"阈值未定义

**文件**: `docs/superpowers/specs/2026-06-17-face-api-wms-capture-loop-design.md:220`  
**问题**: 第 7 节验收成功标准要求"打印照片、手机屏幕照片、电脑屏幕照片和播放视频不得低风险静默成功"，这是一个正确的安全要求。但文档未引用或定义"低风险"的具体阈值。当前 `face_api` V2.3 的轻量防翻拍风险等级（low/medium/high）阈值应该在设计文档中与实现保持一致，否则验收时无法判断"低风险"的具体含义。

**建议**: 在验收标准中引用具体的风险等级定义，或添加注释说明阈值来源（如 `face_api` 配置中的 `RISK_THRESHOLD_LOW` 环境变量或代码常量）。

---

## 安全检查清单

| 检查项 | 状态 | 说明 |
|---|---|---|
| 认证链路是否在设计中被覆盖 | ⚠️ 部分缺失 | 数据流和归因表未包含 API Key 认证（见 M1、M2） |
| API Key / 密钥是否硬编码 | ✅ 通过 | 文档中无硬编码密钥 |
| 敏感路径是否暴露 | ⚠️ 信息级 | 第 5-7 行包含开发机绝对路径，属内部文档可接受 |
| 翻拍攻击验收是否纳入 | ✅ 通过 | 第 7 节明确要求翻拍样例不得低风险静默成功 |
| 审计日志完整性 | ⚠️ 可改进 | 缺少认证状态字段（见 M4） |
| 错误处理是否覆盖安全失败 | ⚠️ 部分缺失 | 归因表缺少认证失败场景（见 M2） |
| 网络通信安全 | ⚠️ 未提及 | 文档未说明 WMS 与 Face API 间通信是否限定 localhost 或内网 |
| 人臉數據隱私 | ✅ 通过 | 设计未要求传输或存储原始人脸图像到外部 |
| 输入校验 | ✅ 通过 | Face API 端已有输入校验（图片解码、人脸数量检查），文档确认保留 |

---

## 总结

- **安全**: 无 CRITICAL/HIGH 问题。主要缺口是认证链路在设计文档中的可见性不足——数据流、归因表、验收步骤均未显式覆盖 API Key 认证，可能导致联动调试阶段的安全配置被遗漏。
- **质量**: 设计文档结构清晰，三条 Trace（功能联动/现场验收/问题复盘）覆盖了 PDCA 闭环的关键环节。验收标准和归因规则具体可操作。建议补充认证相关场景后即可作为实施基线。
