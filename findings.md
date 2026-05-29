# findings

## Repository findings
- 项目是单服务、本地部署导向的人脸识别 API，后端主入口在 `main.py`。
- 业务核心高度集中在 3 个文件：`main.py`、`face_engine.py`、`storage.py`。
- API 既服务前端联调，也承担轻量业务认证能力（`/auth/face-login`）。
- 文档已有分工：`README.md` 偏运行说明，`docs/usage/API_INTEGRATION.md` 偏前端对接，`HOW_TO_DELIVER.md` 偏交付方式。
- 新文档需要做的是“聚合 + 重组 + 明确边界”，而不是简单复制。

## API behavior findings
- `/health` 不鉴权，用于探活。
- 大部分业务接口通过 `verify_api_key` 控制：仅当 `FACE_API_KEY` 设置后才强制校验。
- `/auth/face-login` 更严格：使用 `require_api_key`，只有明确配置并传入 `X-API-Key` 才能调用。
- `Base64` 输入支持带和不带 `data:image/...;base64,` 前缀。
- `/compare`、`/search` 在多脸场景下取 `det_score` 最高的人脸。
- `/faces/register` 与 `/auth/face-login` 都要求画面中恰好 1 张脸。
- API 不返回 embedding 给前端，避免泄露高维特征向量。

## Architecture findings
- `FaceEngine` 在模块加载时初始化为单例，避免每个请求重复加载模型。
- `FaceEngine` 优先尝试 CUDAExecutionProvider，否则回落 CPU。
- `FaceDB` 使用 SQLite + WAL + 线程本地连接；embedding 以 float32 BLOB 存储。
- 1:N 搜索不是逐行 Python 循环，而是 NumPy 矩阵化余弦相似度计算。

## Documentation gaps / inconsistencies
- README 对当前运行状态的描述偏“作者机器实况”，而项目说明偏“目标架构”，两者需要在新文档里明确区分。
- `docs/usage/API_INTEGRATION.md` 中的性能参考与 README 中 CPU/GPU 耗时表述不完全一致，需标记为“历史经验值，仅供参考”。
- `test.html` 没有内置 `X-API-Key` 输入；一旦启用鉴权，除 `/health` 外很多操作不能直接测。
- `HOW_TO_DELIVER.md` 包含 Linux/Nginx 部署方式，但项目当前主目标仍是 Windows 单机，需在新文档里标注适用场景。

## Likely optimization topics
- 把接口契约、运行说明、架构约束统一收口，避免多份文档长期漂移。
- 增加真正可复现的基准测试与性能记录。
- 为 `test.html` 增加 API Key、阈值、错误提示和更多调试信息。
- 如果底库规模继续增长，`storage.py` 的全表向量搜索未来可升级为向量索引方案（如 Faiss）。
