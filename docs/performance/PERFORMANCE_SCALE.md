# 性能与规模化验证

本文档对应 Roadmap V1.6，用来指导 5 万人脸规模 benchmark、批量清单、index 进入条件和回退策略。

## 1. 默认策略

- 默认搜索模式仍然是 `exact`：SQLite 读取 embedding，NumPy 做矩阵化 cosine similarity。
- 默认不启用 ANN、Faiss 或外部向量数据库。
- 只有 benchmark 证明 5 万人脸规模不达标时，才进入 index 方案评估。
- 任何 index 方案都必须保留 exact 回退路径。

## 2. Benchmark 指标

目标规模：

```text
target_record_count = 50000
target_latency_ms = 1000
```

必须记录：

- `record_count`：当前底库记录数。
- `avg_ms`：平均搜索耗时。
- `p95_ms`：P95 搜索耗时。
- `min_ms` / `max_ms`：最小和最大耗时。
- `failure_count`：失败次数。
- `failure_reasons`：失败原因统计。
- `runtime`：Python、平台、数据库路径等运行配置。
- `index_decision`：是否需要进入 index 评估。

## 3. 运行 benchmark

只测试现有数据库：

```powershell
D:\anaconda3\envs\face_api\python.exe scripts\benchmark-scale.py --db-path faces.db --sample-count 100
```

使用合成 embedding 补齐到 5 万条后测试：

```powershell
D:\anaconda3\envs\face_api\python.exe scripts\benchmark-scale.py --db-path faces.db --target-count 50000 --seed-synthetic --sample-count 100
```

安全说明：

- 默认情况下，`--seed-synthetic` 会使用临时 SQLite benchmark 库，不会写入 `faces.db`。
- 如果确实要把合成数据写入 `--db-path` 指定的数据库，必须显式增加 `--write-db`。
- 不建议在生产人脸库上使用 `--write-db`。

默认报告输出：

```text
reports/performance/benchmark-scale.json
```

报告结论：

- `conclusion = pass`：精确搜索满足目标，继续保留默认 exact。
- `conclusion = needs_index_evaluation`：进入 index 方案评估，但不能直接切默认模式。

## 4. 批量清单流程

导出当前底库清单：

```powershell
D:\anaconda3\envs\face_api\python.exe scripts\bulk-manifest.py export --db-path faces.db --output exports\faces-manifest.jsonl
```

导出清单字段：

```text
id, user_id, username, metadata, created_at
```

导出清单不包含 `embedding`。

校验导入清单：

```powershell
D:\anaconda3\envs\face_api\python.exe scripts\bulk-manifest.py validate-import imports\faces.csv --output reports\bulk-import-validate.json
```

导入清单必填字段：

```text
image_path, username
```

导入清单可选字段：

```text
user_id, terminal_id, metadata
```

校验报告必须包含：

- `success_count`
- `failure_count`
- `skipped_count`
- `failed[].reasons`
- `required_fields`
- `optional_fields`

## 5. Index 进入条件

同时满足下面条件，才允许进入 index 方案设计或 PoC：

- 5 万人脸 benchmark 的 search 或 login P95 连续超过 `1000ms`。
- 已经排除图片过大、缓存未预热、CPU/GPU 配置错误、数据库 WAL 异常膨胀等运行问题。
- index 方案与 exact 搜索抽样对比，top-1 一致率达到验收阈值。
- 注册、删除、恢复数据库后能明确显示 index 是否 fresh 或 rebuild required。
- index 异常时 search/login 能回退 exact，或返回明确错误。

## 6. API 状态接口

查看 benchmark 目标：

```text
GET /search/benchmark-summary
```

查看 index 状态和回退策略：

```text
GET /search/index-status
```

查看 V1.6 scale 总方案：

```text
GET /performance/scale-plan
```

以上接口都需要 `X-API-Key`。
