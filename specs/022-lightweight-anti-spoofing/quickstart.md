# Quickstart: V2.1 轻量防翻拍活体增强

## 1. 阅读范围

先确认本版本边界：

```text
specs/ROADMAP-v2.1.md
specs/022-lightweight-anti-spoofing/spec.md
specs/022-lightweight-anti-spoofing/plan.md
specs/022-lightweight-anti-spoofing/contracts/api-contract.md
```

## 2. 实施前基线检查

```powershell
git status --short --branch
D:\anaconda3\envs\face_api\python.exe -m unittest discover -s tests -v
git diff --check
```

当前还有上一轮 post-commit review 修复未提交时，先不要把 V2.1 实现和那批修复混在一个提交里。

## 3. 建议实施顺序

1. 增加 `AntiSpoofRisk` 响应模型和错误码。
2. 在现有活体 challenge 提交流程里增加轻量风险计算。
3. 将风险结果写入 liveness challenge 和 face login audit。
4. 在 `/auth/face-login` 成功和失败路径中透出风险结果。
5. 更新 `camera-integration.html`、`business-demo` 和 `terminal-demo.py` 的展示。
6. 增加真人、打印照片、手机屏幕、电脑屏幕和播放视频的验收记录模板。
7. 更新 API 文档、识别安全说明和架构图。

## 4. 测试重点

聚焦测试：

```powershell
D:\anaconda3\envs\face_api\python.exe -m unittest tests.test_main_api tests.test_storage_schema -v
D:\anaconda3\envs\face_api\python.exe -m unittest tests.test_scripts_smoke tests.test_business_demo -v
```

全量验证：

```powershell
D:\anaconda3\envs\face_api\python.exe -m unittest discover -s tests -v
D:\anaconda3\envs\face_api\python.exe -m compileall -q main.py app_config.py admin_ops.py api_errors.py api_schemas.py face_engine.py storage.py business_demo scripts tests
git diff --check
```

页面依赖扫描：

```powershell
rg -n "cdn|script src|link rel=.*stylesheet|import |require\(" -g "*.html" .
```

## 5. 验收样例

至少记录以下样例：

| 样例 | 预期 |
|---|---|
| 真人正脸 | 低风险或正常通过 |
| 打印照片 | 不应静默低风险成功 |
| 手机屏幕显示照片 | 不应静默低风险成功 |
| 电脑屏幕显示照片 | 不应静默低风险成功 |
| 手机播放眨眼视频 | 至少中风险或进入复核说明 |

## 6. 交付检查

- [x] 低风险真人登录不增加复杂动作。
- [x] 高风险结果有中文原因。
- [x] audit 能看到 `anti_spoof_risk`。
- [x] `business-demo` 和终端 demo 主流程不被破坏。
- [x] 文档明确说明 V2.1 不是企业级强活体。
