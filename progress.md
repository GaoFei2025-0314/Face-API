# progress

## Session log
- 已确认文档目标：同时服务作者自查与后续全栈接手。
- 已确认文件名：`docs/05_architecture/01_architecture.md`。
- 已读取并梳理现有资料：`README.md`、`docs/04_usage/01_api_integration.md`、`HOW_TO_DELIVER.md`、`main.py`、`face_engine.py`、`storage.py`、`test.html`。
- 已识别需要重点写清的部分：鉴权行为、单例初始化、数据库搜索策略、Base64 约定、单人脸约束、文档间差异。

## Clarified preferences
- 文档风格：综合型（先上手路径，再接口，再架构，再优化建议）
- 运行环境口径：两套都保留，但 conda 为主路径，venv 为备选/兼容路径
- 维护者内容：单独增加“后续维护与改动建议”章节

## Delivered
- 已创建并精修 `docs/05_architecture/01_architecture.md`。
- 已重写 `README.md` 与 `docs/04_usage/01_api_integration.md`，统一了运行口径、鉴权语义、GPU/CPU 说明与系统边界描述。
- 已补充 `docs/04_usage/01_api_integration.md` 的两处接手提醒：运行口径以 README/技术说明为准，以及 `/auth/face-login` 比其他接口更严格。
- 已按用户偏好直接给出完整结果，不再逐段确认。

## Notes
- 文档里明确了 conda 为主路径、venv 为备选路径。
- `/auth/face-login` 在三份文档中都明确为“必须显式启用 API Key”的更严格接口。
- 性能数字统一收敛为“历史经验值/参考值”，避免被误读为稳定承诺。
