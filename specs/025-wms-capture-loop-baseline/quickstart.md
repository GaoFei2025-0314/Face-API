# Quickstart: Face API 与 WMS 现场联动验收基线

## 1. 实施前检查

```powershell
Set-Location H:\AI_test\face_api
git status --short

# 如果要走原生 /speckit-* 脚本，先切换到 feature 分支；
# 如果走 /goal，可使用显式路径，不依赖 check-prerequisites.ps1 推导。
git branch --show-current

Test-Path 'H:\AI_test\electron-wms\electron-wms'
git -C 'H:\AI_test\electron-wms\electron-wms' status --short
```

期望：

- Face API 工作区没有未预期变更。
- 当前分支策略明确：原生 spec-kit 使用 `025-wms-capture-loop-baseline` 分支；`/goal` 使用显式路径。
- WMS 路径存在。
- WMS 工作区没有未预期变更。

## 2. Face API 基础检查

```powershell
Set-Location H:\AI_test\face_api
$env:FACE_API_KEY="123456"
.\run.bat
```

另开终端：

```powershell
curl http://localhost:8000/health
curl http://localhost:8000/openapi.json
```

期望：

- `/health` 返回服务可用。
- OpenAPI 可访问。
- 启动日志显示 CPU 或 GPU 推理模式。

## 2.1 API Key 对齐检查

V2.4 联动验收需要确认 Face API 与 WMS 使用的是同一个 API Key 来源：

- Face API 独立启动时，本终端示例使用 `$env:FACE_API_KEY="123456"`。
- WMS 内嵌人脸服务启动时，`electron/service/faceService.js` 会把 `this.apiKey` 注入子进程 `FACE_API_KEY`。
- WMS 请求人脸服务时，同一个 `this.apiKey` 会作为请求头 `x-api-key` 发送。

只读确认命令：

```powershell
Select-String -LiteralPath 'H:\AI_test\electron-wms\electron-wms\electron\service\faceService.js' -Pattern 'FACE_API_KEY: this.apiKey','x-api-key' -SimpleMatch
Select-String -LiteralPath 'H:\AI_test\electron-wms\electron-wms\tests\face-service-runtime.test.js' -Pattern 'env.FACE_API_KEY, service.apiKey' -SimpleMatch
```

期望：

- `faceService.js` 同时出现 `FACE_API_KEY: this.apiKey` 和 `x-api-key`。
- 测试文件中有 `env.FACE_API_KEY` 等于 `service.apiKey` 的断言。
- 若现场出现 401/403，先检查 Face API 启动端 API Key 和 WMS 请求头是否来自同一个值。

## 3. WMS 终端检查

```powershell
Set-Location H:\AI_test\electron-wms\electron-wms
npm run dev
```

期望：

- WMS 主界面可打开。
- 摄像头入口能看到实时画面。
- 本地测试用户和本地人脸库状态可确认。

## 4. 联动验收记录

使用后续实施创建的模板：

```text
H:\AI_test\face_api\docs\90_archive\04_acceptance\08_face_api_wms_capture_loop_baseline.md
```

按模板记录：

- 环境快照
- 启动检查
- 样例矩阵
- 单次样例结果
- 问题分类
- 验收结论
- 下一轮改进项

## 5. 静态验证

```powershell
$scanTerms = @('TB' + 'D', 'TO' + 'DO', '待' + '定', '占' + '位')
$scanPaths = @(
  'H:\AI_test\face_api\specs\ROADMAP-v2.4.md',
  'H:\AI_test\face_api\specs\025-wms-capture-loop-baseline\spec.md',
  'H:\AI_test\face_api\specs\025-wms-capture-loop-baseline\plan.md',
  'H:\AI_test\face_api\specs\025-wms-capture-loop-baseline\tasks.md',
  'H:\AI_test\face_api\docs\90_archive\04_acceptance\08_face_api_wms_capture_loop_baseline.md',
  'H:\AI_test\electron-wms\electron-wms\doc\13-Face-API-WMS智能抓拍联动验收基线.md'
)
$missingScanPaths = $scanPaths | Where-Object { -not (Test-Path $_) }
if ($missingScanPaths) { throw "Missing scan path: $($missingScanPaths -join ', ')" }
Select-String -LiteralPath $scanPaths -Pattern $scanTerms -SimpleMatch

git -C 'H:\AI_test\face_api' diff --check
```

期望：

- 占位词扫描无输出。
- `git diff --check` 无输出。
