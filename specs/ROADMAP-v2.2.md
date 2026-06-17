# face_api Roadmap v2.2

> 创建时间：2026-06-17
> 用途：定义 V2.2 现场算法验收与阈值调优台的范围、边界和执行入口
> 状态：自动验证已完成，待现场摄像头五类样例验收

## 1. 版本定位

V2.2 的目标是把 V2.1 已实现的人脸识别、活体和轻量防翻拍风险能力，变成一个现场可操作、可导出报告、可指导调参的本地验收台。

本版本定位为：

> 现场算法验收与阈值调优台。

V2.2 不继续扩大算法本身，不新增后端数据库表，不新增公开 API。它重点解决“当前算法能力完成得怎么样、现场样例结果如何复盘、后续阈值应该往哪个方向看”的问题。

## 2. 子版本范围

| 子版本 | Spec | 主题 | 目标 |
|---|---|---|---|
| V2.2.1 | `specs/023-field-algorithm-acceptance-console` | 验收台页面 | 新建 `acceptance.html`，跑通摄像头预览、测试用户注册/重绑和五类样例采集 |
| V2.2.2 | `specs/023-field-algorithm-acceptance-console` | 报告导出 | 支持 JSON/CSV 报告，不保存图片或连续帧 |
| V2.2.3 | `specs/023-field-algorithm-acceptance-console` | 调参建议 | 输出小白建议和开发/运维阈值方向，不自动改配置 |
| V2.2.4 | `specs/023-field-algorithm-acceptance-console` | 文档和架构同步 | 更新架构图、使用文档、验收记录和季度计划 |

## 3. 已确认决策

- 新建独立 `acceptance.html`。
- 页面直连 `face_api`，适用于本地工作站或受控内网验收。
- API Key 只保存在浏览器内存，不写入报告。
- 测试用户 `user_id` 使用数字或留空，避免违反 `/faces/register` 的整数约束。
- 固定五类样例：真人正脸、打印照片、手机屏幕照片、电脑屏幕照片、手机播放眨眼视频。
- 每类样例默认采集 3 次。
- 真人正脸完成 3 次后至少 2 次成功且无高风险才显示符合预期。
- 每次采集走完整登录链路：login challenge、连续帧提交、`/auth/face-login`。
- 活体失败时记录该次失败原因，不继续调用 `/auth/face-login`。
- 注册/重绑根据 `/system/status` 的注册活体开关决定是否先走 `register` challenge。
- 如通过 `http://localhost:8122` 打开验收页面，生产模式需通过 `FACE_CORS_ORIGINS` 允许该来源。
- 结果只保存指标和接口结果，不保存原图、缩略图或连续帧。
- 报告支持 JSON 和 CSV。
- 调参建议只给方向，不直接生成最终环境变量值。
- 同步更新 `architecture.html`。

## 4. 明确不做

- 不新增后端数据库表。
- 不新增验收记录 API。
- 不保存图片或视频帧。
- 不自动修改环境变量。
- 不引入前端框架、CDN 或远程依赖。
- 不承诺企业级强活体。

## 5. 推荐执行入口

```text
/goal Implement face_api Roadmap V2.2 - Field Algorithm Acceptance Console
```

实施前先阅读：

```text
docs/superpowers/specs/2026-06-16-v2.2-field-algorithm-acceptance-console-design.md
specs/023-field-algorithm-acceptance-console/spec.md
specs/023-field-algorithm-acceptance-console/plan.md
specs/023-field-algorithm-acceptance-console/tasks.md
```

## 6. 验收总则

- [ ] `acceptance.html` 可打开并显示摄像头预览。
- [ ] 页面可注册或重绑测试用户。
- [ ] 测试用户 `user_id` 使用数字或留空。
- [ ] 页面包含五类固定样例，每类默认 3 次。
- [ ] 每次样例可记录成功/失败、风险等级、中文原因和关键指标。
- [ ] 活体失败时只记录失败结果，不继续 face login。
- [ ] 注册/重绑兼容注册活体开关。
- [ ] 通过 `FACE_CORS_ORIGINS` 支持 `http://localhost:8122` 现场浏览器验收。
- [ ] 页面可下载 JSON 和 CSV 报告。
- [ ] 页面不保存原图、不保存连续帧、不导出 API Key。
- [ ] 页面输出小白建议和开发/运维阈值方向。
- [ ] `architecture.html`、README、识别安全文档和验收记录同步更新。
