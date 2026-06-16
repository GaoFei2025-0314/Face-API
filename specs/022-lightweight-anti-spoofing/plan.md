# Implementation Plan: 轻量防翻拍活体增强

**Branch**: `main` | **Date**: 2026-06-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/022-lightweight-anti-spoofing/spec.md`

## Summary

V2.1 在现有活体 challenge、face login 和 audit 链路上增加轻量防翻拍风险语义。实现方式保持保守：不新增重交互动作、不引入新硬件、不引入重型模型；优先使用连续帧稳定性、画面变化、人脸框变化、清晰度变化和可疑静态特征生成低/中/高风险结果。默认只阻断高风险，低风险无感通过，中风险记录并提示可复核，避免明显拉低真实用户体验。

## Technical Context

**Language/Version**: Python 3.10.x；原生 HTML/CSS/JS 页面；Windows `.bat`/PowerShell 运行脚本。

**Primary Dependencies**: FastAPI、Pydantic、OpenCV、NumPy、InsightFace、ONNX Runtime、SQLite；不新增 PyTorch 或重型 anti-spoofing 依赖。

**Storage**: SQLite。当前 `FaceDB` 已有 `liveness_challenges`、`face_login_audit` 和 JSON 字段能力；V2.1 采用向后兼容迁移增加风险结果存储。

**Testing**: `unittest`，继续使用 `tests/test_main_api.py`、`tests/test_storage_schema.py`、`tests/test_scripts_smoke.py`、`tests/test_business_demo.py`。

**Target Platform**: 单台 Windows 工作站，默认 CPU 推理，可配置 GPU。

**Project Type**: 本地 REST API + 本地静态摄像头页面 + 业务接入 demo。

**Performance Goals**: 真人登录主流程不增加明显等待；防翻拍风险计算复用已提交的连续帧，避免额外模型加载。V2.1 完成后，标准现场登录仍应保持秒级完成。

**Constraints**:

- 不默认增加多动作 challenge。
- 不破坏 `/auth/face-login`、`/liveness/challenges/submit`、`business-demo` 和 `terminal-demo.py` 的现有主流程。
- 不返回 embedding 给前端。
- 高风险失败必须有中文用户提示和可复核原因。
- 配置默认应保护用户体验：低风险通过，中风险可记录，高风险阻断。

**Scale/Scope**: 覆盖单工作站、普通摄像头、真人/打印照片/手机屏幕/电脑屏幕/播放视频五类验收样例；不覆盖企业级攻击、虚拟摄像头流或深度伪造。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` 仍是模板占位，没有可执行项目原则。实际 gate 使用仓库 `AGENTS.md` 和现有项目约束：

- **MVP 边界**：优先扩展 `main.py`、`storage.py`、`api_schemas.py`、`api_errors.py`，不做大框架重构。通过。
- **依赖边界**：不引入 PyTorch，不新增重型模型依赖。通过。
- **体验边界**：不默认增加多动作 challenge，只在高风险阻断。通过。
- **兼容边界**：公开接口仅做向后兼容字段增加，不删除现有字段。通过。
- **测试边界**：实现阶段必须先补失败测试，再最小实现。通过。
- **文档耦合**：接口语义、配置、页面和验收报告变化必须同步文档。通过。

## Project Structure

### Documentation (this feature)

```text
specs/022-lightweight-anti-spoofing/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md              # Phase 2 output, not created in this step
```

### Source Code (repository root)

```text
main.py                   # 活体风险计算、face login/register 接入、配置输出
api_schemas.py            # 响应模型增加 anti_spoof_risk 可选字段
api_errors.py             # 高风险阻断中文错误码
app_config.py             # 轻量防翻拍配置解析与启动校验
storage.py                # liveness challenge 与 login audit 风险字段持久化
camera-integration.html   # 摄像头联调页面展示风险提示
business_demo/
├── app.py                # 透传/展示 face_api 风险结果
├── schemas.py            # 业务 demo 请求/响应模型如需补充
└── static/
    ├── index.html
    └── terminal.html
scripts/
└── terminal-demo.py      # CLI 输出风险等级和原因
docs/
├── 04_usage/
│   ├── 01_api_integration.md
│   ├── 03_recognition_security_accuracy.md
│   └── 04_business_integration_v2.md
└── 90_archive/04_acceptance/
    └── 05_v2.1_acceptance_record.md
tests/
├── test_app_config.py
├── test_main_api.py
├── test_storage_schema.py
├── test_scripts_smoke.py
└── test_business_demo.py
```

**Structure Decision**: 使用现有单体 FastAPI + SQLite 结构，新增风险语义作为现有活体链路的兼容扩展。不新建独立服务，不引入前端框架，不拆路由模块。

## Complexity Tracking

无 constitution violation。V2.1 采用兼容字段和轻量规则，避免引入新服务、新模型或新硬件。

## Phase 0 Output

- [research.md](research.md)

## Phase 1 Output

- [data-model.md](data-model.md)
- [contracts/api-contract.md](contracts/api-contract.md)
- [quickstart.md](quickstart.md)

## Post-Design Constitution Check

- **MVP 边界**：设计仍在现有模块内完成。通过。
- **依赖边界**：设计不要求新增重型依赖。通过。
- **体验边界**：默认只阻断高风险，低风险无感通过。通过。
- **兼容边界**：合同定义为向后兼容字段增加。通过。
- **测试边界**：quickstart 和后续 tasks 必须包含失败测试优先。通过。
- **文档耦合**：已列入文档和验收记录更新。通过。
