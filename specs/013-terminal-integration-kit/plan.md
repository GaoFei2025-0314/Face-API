# 实施计划：终端接入规范包

## 范围

标准化 terminal 与业务系统接入方式：

- 注册和 login 都必须带 `terminal_id`。
- 业务系统主动调用 face_api，face_api 不 callback。
- audit/log/文档中统一 terminal identity。
- 提供接入示例和交付检查清单。

## 设计决策

- `terminal_id` 是诊断和接入字段，不替代用户鉴权。
- 缺少 `terminal_id` 的注册和 login 请求直接拒绝。
- 文档强调业务系统负责最终业务决策。

## 验证

- 测试注册缺少 `terminal_id` 被拒绝。
- 测试 login 缺少 `terminal_id` 被拒绝。
- 测试 audit 记录 terminal identity。
- 测试文档包含主动调用流程和失败映射。

