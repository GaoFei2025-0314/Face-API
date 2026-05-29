# face_api 模块化阶段成果与风险边界说明

## 1. 文档目的

本文用于说明本轮 `face_api` 模块化改造的阶段成果、当前版本范围、测试与验证结果，以及已经明确接受或暂不处理的风险边界，方便后续：

- 项目作者回看当前阶段做到了什么
- 后续接手同学快速理解当前能力边界
- 对外汇报时说明“这轮到底交付了什么，不交付什么”

---

## 2. 本阶段目标

本阶段的目标不是把 `face_api` 做成完整登录平台，而是把它从“通用人脸接口 demo”推进成一个更适合被终端项目复用的识别模块底座。

本阶段重点围绕 4 件事展开：

1. 建立统一识别原子接口
2. 收口错误码与失败语义
3. 增加最小可用的运维与配置读取能力
4. 为后续业务集成补足最小审计能力

---

## 3. 本阶段已完成能力

### 3.1 runtime primitives

本阶段已建立以下原子能力接口：

- `GET /health`
- `GET /system/status`
- `GET /config/effective`
- `POST /extract/base64`

其中：

- `/health` 用于探活
- `/system/status` 用于读取当前运行状态
- `/config/effective` 用于读取当前生效配置
- `/extract/base64` 用于提取单人脸特征并返回稳定失败语义

### 3.2 library helpers

本阶段保留并增强了以下能力：

- `POST /detect`
- `POST /detect/base64`
- `POST /compare`
- `POST /search`
- `POST /faces/register`
- `GET /faces`
- `DELETE /faces/{face_id}`

其中，`/compare` 与 `/search` 已开始接入统一失败语义模型。

### 3.3 auth helper

本阶段保留并增强了：

- `POST /auth/face-login`

增强点包括：

- 失败返回结构化错误码
- 单人脸约束收口
- 成功/失败写入登录审计

### 3.4 ops helpers

本阶段新增了最小可用的运维接口：

- `GET /audit/login/recent`
- `GET /audit/login/summary`

支持：

- 查看最近登录尝试记录
- 查看成功/失败汇总与成功率

---

## 4. 错误语义与契约收口

本阶段已经明确使用结构化失败语义的主要错误码包括：

- `IMAGE_DECODE_FAILED`
- `IMAGE_TOO_LARGE`
- `NO_FACE`
- `MULTIPLE_FACES`
- `INVALID_EMBEDDING_RESPONSE`
- `NO_MATCH`
- `INVALID_MATCH_RECORD`
- `FACE_ID_NOT_FOUND`
- `INVALID_USERNAME`

错误响应继续沿用 FastAPI 的 `detail` 字段，但对于业务型 primitive / helper 接口，`detail` 允许为结构化对象：

```json
{
  "detail": {
    "code": "NO_FACE",
    "message": "未检测到人脸"
  }
}
```

这意味着前端、桌面端或受控集成方可以稳定地按 `detail.code` 分流，而不是再依赖中文字符串匹配。

---

## 5. 鉴权边界

### 5.1 保持原有兼容行为的接口

以下接口保留“条件启用鉴权”语义：

- `POST /detect`
- `POST /detect/base64`
- `POST /compare`
- `POST /faces/register`
- `GET /faces`
- `DELETE /faces/{face_id}`
- `POST /search`

也就是说：

- 未设置 `FACE_API_KEY` 时，不强制鉴权
- 设置后，要求传 `X-API-Key`

这部分是为了保留项目原有契约，不破坏既有使用方式。

### 5.2 强制显式鉴权的接口

以下接口要求显式配置并正确传入 `FACE_API_KEY`：

- `POST /extract/base64`
- `GET /system/status`
- `GET /config/effective`
- `POST /auth/face-login`
- `GET /audit/login/recent`
- `GET /audit/login/summary`

这部分接口更偏：

- 受控集成能力
- 运维能力
- 认证辅助能力

不适合作为匿名或普通浏览器页面开放能力。

---

## 6. 审计与配置能力

### 6.1 登录审计

当前 `/auth/face-login` 已支持：

- 成功写审计
- 失败写审计
- 保存关键字段，包括：
  - `success`
  - `matched_user_id`
  - `matched_username`
  - `similarity`
  - `threshold`
  - `failure_reason`
  - `terminal_id`
  - `state`
  - `elapsed_ms`

### 6.2 当前生效配置

`GET /config/effective` 当前返回：

- `face_login_threshold`
- `auth_enabled`
- `force_cpu`
- `model`
- `det_size`
- `db_path`

这让外部项目接入时不必再靠猜当前阈值和运行配置。

---

## 7. 数据存储层变化

本阶段在 `storage.py` 中确认并收口了：

- `faces` 表继续作为底库主表
- `face_login_audit` 表作为登录审计表
- fresh schema 初始化可正常创建新库
- `FaceDB` 已补：
  - 审计写入
  - 审计列表查询
  - 审计汇总查询

这意味着当前模块已经不仅是“能识别”，还具备最小可观测和可调优基础。

---

## 8. 验证结果

本阶段已完成的验证包括：

- contract tests
- storage fresh schema 测试
- Python 语法检查
- review correctness / security / DX 收口

当前测试结果：

- **24 个测试，全绿**

覆盖范围包括：

- `/extract/base64`
- `/system/status`
- `/config/effective`
- `/compare`
- `/search`
- `/auth/face-login`
- `/audit/login/recent`
- `/audit/login/summary`
- sensitive route auth mode
- storage fresh schema

---

## 9. 当前阶段风险边界

### 9.1 已接受的主要风险边界

本阶段唯一明确接受的 major 风险边界是：

> `POST /extract/base64` 会向受控调用方返回 raw embedding。

这不是 bug，而是有意识接受的产品边界，原因是当前目标是支撑：

- Electron / WMS 这类受控终端集成
- 本地主进程 / 本地服务 / 受控后端模块
- 更灵活的后续匹配、审计和离线编排能力

### 9.2 使用约束

如果继续保留当前设计，必须同时接受以下使用约束：

- 不直接暴露给普通浏览器前端
- 不把对应 API key 下发给非受控调用方
- 更适合桌面端、主进程、服务端内部模块调用
- 将其视为“受控 primitive”，而不是开放前端接口

### 9.3 暂未纳入本阶段的能力

以下内容当前仍不在本阶段范围内：

- 活体检测
- 防重放机制
- 多终端集中化审计看板
- 配置写入接口
- 离线权限边界治理
- 更强的速率限制/风控层

---

## 10. 本阶段版本说明

如果为当前阶段起一个版本说明，可定义为：

> **face_api modularization phase-1**

### phase-1 的版本定义

它不是完整身份平台，也不是纯算法 demo，而是：

- 具备 primitive / helper / ops / storage contract 的可复用识别模块底座

### phase-1 交付重点

- primitive 立住
- helper 收口
- ops 起步
- contract 与测试跟上
- 风险边界被明确写清楚

---

## 11. 后续建议

如果继续推进 phase-2，最值得的方向有 4 个：

1. 更细的 audit summary（失败原因分布、终端维度）
2. 更完整的安全收口（特别是 `/extract/base64` 边界）
3. 配置层增强（可控写入、配置来源说明）
4. 文档进一步去重和精简

---

## 12. 结论

本阶段已经完成了从“通用人脸接口”到“可复用模块底座”的第一步。

当前 `face_api` 已具备：

- primitive 能力
- helper 能力
- 最小 ops 能力
- 最小审计能力
- 存储闭环
- 文档与测试闭环

如果按当前边界理解，它已经可以作为受控终端项目的人脸能力底座投入继续集成和下一阶段演进。
