# 实施计划：现场算法验收与阈值调优台

**分支/目录**：`023-field-algorithm-acceptance-console`

**日期**：2026-06-17

## 技术上下文

- 页面：原生 `acceptance.html`，不引入框架或外部依赖。
- API：复用现有 `/health`、`/faces/register`、`/liveness/challenges`、`/liveness/challenges/submit`、`/auth/face-login`。
- 运行状态：通过 `/system/status` 获取注册活体开关和运行摘要。
- 鉴权：页面输入 `X-API-Key`，仅保存在运行时变量。
- 测试用户：`user_id` 使用数字或留空；留空时按 API 合约发送 `null`。
- 登录链路：活体 challenge 未通过时记录失败和中文原因，不继续调用 `/auth/face-login`。
- 注册/重绑链路：兼容注册活体开关；开启时先完成 `register` challenge。
- CORS：如果页面通过 `http://localhost:8122` 打开，生产模式需要把该来源加入 `FACE_CORS_ORIGINS`。
- 报告：浏览器本地生成 JSON/CSV Blob 下载。
- 测试：`tests/test_scripts_smoke.py` 静态检查 + 浏览器页面加载检查 + 手动摄像头验收。

## 约束

- 不新增后端接口。
- 不新增数据库表。
- 不保存图片或连续帧。
- 不输出 API Key。
- 不引入 CDN。
- 不新增后端 CORS 特例；使用现有 `FACE_CORS_ORIGINS` 配置。
- 不自动修改环境变量或自动提交。

## 文件变更

- 新建 `acceptance.html`。
- 修改 `tests/test_scripts_smoke.py`。
- 修改 `architecture.html`。
- 修改 `README.md`。
- 修改 `docs/04_usage/03_recognition_security_accuracy.md`。
- 修改 `docs/02_product/02_quarterly_plan.md`。
- 新建 `docs/90_archive/04_acceptance/06_v2.2_acceptance_record.md`。
