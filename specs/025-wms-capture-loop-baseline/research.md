# Research: Face API 与 WMS 现场联动验收基线

## Decision 1: V2.4 采用 docs-only 联动验收基线

**Decision**：V2.4 第一阶段只建立规格、模板、runbook、索引和检查流程。

**Rationale**：V2.3 已经证明 Face API 自身固定摄像头链路可用。下一步最大的未知不是某个接口能不能调用，而是真实 WMS 终端采集、页面提示、业务登录和日志回收能不能形成闭环。先建立验收基线可以避免在没有现场证据的情况下盲目改算法或 WMS 逻辑。

**Alternatives considered**：

- 直接增强防翻拍算法：容易继续堆轻量规则，且可能伤害真人体验。
- 直接改 WMS 登录页面：没有统一验收模板时，难以判断问题到底属于采集、算法还是业务流程。

## Decision 2: Face API 保存联动验收模板

**Decision**：Face API 仓库新增 `docs/90_archive/04_acceptance/08_face_api_wms_capture_loop_baseline.md`。

**Rationale**：Face API 是算法底座和识别 audit 的来源，验收模板应靠近算法版本记录，便于后续 V2.5 复盘算法、阈值和错误码。

**Alternatives considered**：

- 只放在 WMS 仓库：算法版本和 Face API audit 语义容易断开。
- 放在聊天记录：不可复用，不适合交接。

## Decision 3: WMS 保存终端侧 runbook

**Decision**：WMS 仓库新增 `doc/13-Face-API-WMS智能抓拍联动验收基线.md`。

**Rationale**：摄像头权限、本地人脸库、Electron 日志、页面提示和业务登录链路都属于 WMS 终端侧知识，应放在 WMS 文档目录，方便终端开发者维护。

**Alternatives considered**：

- 只在 Face API 文档中描述 WMS：会让 WMS 开发者难以按项目习惯查找。
- 复制一份完整模板到两个仓库：容易产生内容分叉。

## Decision 4: 问题归因固定为三类

**Decision**：所有问题必须归到算法底座、终端采集、业务流程三类之一，并填写证据来源。

**Rationale**：现场反馈常把问题笼统归为“算法不准”或“现场问题”。固定归因维度能把下一轮工作分清楚：Face API 改算法或错误码，WMS 改采集或页面，业务系统改用户状态、token 或流程。

**Alternatives considered**：

- 使用开放标签：灵活但难统计。
- 使用更细分类：首次联动验收会增加填写负担。

## Decision 5: 不保存媒体和敏感数据

**Decision**：验收记录只保存结果、配置、错误码、风险等级、相似度、耗时、audit 和日志证据，不保存原图、视频帧、embedding、API Key 或真实用户敏感信息。

**Rationale**：人脸图像和 embedding 属于敏感数据。V2.4 的目标是流程基线，不需要收集原始生物特征数据。

**Alternatives considered**：

- 保存样例截图：便于复盘但隐私风险高，且会扩大交付边界。
- 保存 token 或 API Key 用于复现：不可接受，应只记录配置是否一致和认证状态。
