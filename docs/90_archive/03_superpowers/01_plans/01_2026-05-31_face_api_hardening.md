# Face API Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the existing face recognition REST API with broader tests, uniform Chinese error reasons, image input limits, and clearer model initialization failures.

**Architecture:** Keep the current MVP shape: `main.py` owns FastAPI routes and request validation, `face_engine.py` owns InsightFace/ONNX Runtime initialization, and docs describe the public contract. Add small local helpers instead of new framework layers.

**Tech Stack:** Python 3.10.x, FastAPI, Pydantic v2, OpenCV, NumPy, InsightFace, ONNX Runtime, SQLite, `unittest`.

---

## Scope

This plan covers four agreed optimizations:

1. Extend the existing test suite.
2. Standardize API errors as `detail.code`, `detail.message`, and `detail.reason`.
3. Add Base64, byte-size, and decoded-pixel image limits.
4. Improve model initialization failure diagnostics while preserving startup-time model loading.

This plan does not add lazy model loading, token/session management, vector database storage, PyTorch, or a new app framework structure.

## File Structure

- Modify: `main.py`
  - Add centralized error definitions.
  - Add image input limit environment variables and validators.
  - Update auth and route errors to use `code/message/reason`.
  - Expose limits in `/config/effective`.
- Modify: `face_engine.py`
  - Store provider/model initialization context on the instance.
  - Wrap model preparation failures in a clear `RuntimeError`.
- Modify: `tests/test_main_api.py`
  - Extend fake-module API contract tests for the new error shape and image limits.
- Modify: `tests/test_storage_schema.py`
  - No required change unless test command discovery exposes ordering issues.
- Modify: `README.md`
  - Document new environment variables and startup diagnostics.
- Modify: `docs/04_usage/01_api_integration.md`
  - Document the unified error payload and frontend handling.
- Modify: `docs/05_architecture/01_architecture.md`
  - Document the validation boundary and startup-time model loading policy.

## Task 1: Centralize API Error Payloads

**Files:**
- Modify: `main.py`
- Test: `tests/test_main_api.py`

- [ ] **Step 1: Write failing tests for the new error shape**

Add these tests to `tests/test_main_api.py` inside `MainApiContractTests`:

```python
    def test_auth_errors_return_chinese_reason_payload(self):
        module = load_main_module()

        async def run_check():
            with self.assertRaises(HTTPException) as exc_info:
                await module.require_api_key(None)
            self.assertEqual(exc_info.exception.status_code, 401)
            self.assertEqual(
                exc_info.exception.detail,
                {
                    "code": "AUTH_INVALID_OR_MISSING",
                    "message": "认证失败",
                    "reason": "请求缺少有效的 X-API-Key，请检查前端或业务系统的接口配置",
                },
            )

        import asyncio
        asyncio.run(run_check())

    def test_known_error_detail_includes_reason(self):
        module = load_main_module(api_key="secret")
        module.decode_base64 = lambda _: object()
        module.engine.analyze = lambda _: []

        with self.assertRaises(HTTPException) as exc_info:
            module.register(module.RegisterReq(username="zhangsan", image="dummy"))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertEqual(exc_info.exception.detail["code"], "NO_FACE")
        self.assertEqual(exc_info.exception.detail["message"], "未检测到人脸")
        self.assertEqual(
            exc_info.exception.detail["reason"],
            "图片中没有检测到可用于识别的人脸，请调整光线、角度或距离后重试",
        )
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bat
python -m unittest tests.test_main_api.MainApiContractTests.test_auth_errors_return_chinese_reason_payload tests.test_main_api.MainApiContractTests.test_known_error_detail_includes_reason
```

Expected: failure because auth errors currently return a plain string and existing `NO_FACE` errors do not include `reason`.

- [ ] **Step 3: Add centralized error definitions**

In `main.py`, replace the current `error_detail(code: str, message: str) -> dict` helper with:

```python
ERROR_DEFINITIONS = {
    "AUTH_INVALID_OR_MISSING": {
        "message": "认证失败",
        "reason": "请求缺少有效的 X-API-Key，请检查前端或业务系统的接口配置",
    },
    "IMAGE_DECODE_FAILED": {
        "message": "无效图像，无法解码",
        "reason": "上传内容不是有效图片，或 Base64 内容损坏，请重新选择 jpg、png 或 webp 图片",
    },
    "IMAGE_TOO_LARGE": {
        "message": "图片数据过大",
        "reason": "上传图片超过服务允许的大小限制，请压缩图片或降低分辨率后重试",
    },
    "IMAGE_PIXELS_TOO_LARGE": {
        "message": "图片分辨率过高",
        "reason": "图片宽高像素总数超过服务限制，请降低分辨率后重试",
    },
    "NO_FACE": {
        "message": "未检测到人脸",
        "reason": "图片中没有检测到可用于识别的人脸，请调整光线、角度或距离后重试",
    },
    "MULTIPLE_FACES": {
        "message": "检测到多张人脸",
        "reason": "当前接口要求图片中只能有一张人脸，请使用单人照片后重试",
    },
    "INVALID_EMBEDDING_RESPONSE": {
        "message": "人脸特征提取失败",
        "reason": "模型返回的人脸特征不完整，请检查模型文件、推理环境或输入图片质量",
    },
    "INVALID_USERNAME": {
        "message": "username 不能为空",
        "reason": "注册人脸时必须传入非空 username，用于和业务系统用户记录对应",
    },
    "FACE_ID_NOT_FOUND": {
        "message": "该 ID 不存在",
        "reason": "请求删除的人脸 ID 不在当前本地人脸库中",
    },
    "NO_MATCH": {
        "message": "身份验证失败，未匹配到有效用户",
        "reason": "当前人脸与底库记录的相似度未达到登录阈值，请重新拍摄或先完成人脸注册",
    },
    "INVALID_MATCH_RECORD": {
        "message": "身份验证失败，匹配记录无效",
        "reason": "底库命中了人脸记录，但该记录缺少有效 username 或 user_id，请检查人脸库数据",
    },
}


def error_detail(code: str, message: Optional[str] = None, reason: Optional[str] = None) -> dict:
    definition = ERROR_DEFINITIONS.get(code, {})
    return {
        "code": code,
        "message": message or definition.get("message", "请求失败"),
        "reason": reason or definition.get("reason", "请求处理失败，请检查请求参数或联系服务维护人员"),
    }


def raise_api_error(status_code: int, code: str, message: Optional[str] = None, reason: Optional[str] = None):
    raise HTTPException(status_code=status_code, detail=error_detail(code, message, reason))
```

Ensure `Optional` is already imported from `typing`; if not, add it.

- [ ] **Step 4: Replace auth string errors**

Update `verify_api_key` and `require_api_key` in `main.py`:

```python
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """如果环境变量没设 FACE_API_KEY，则不强制校验（开发模式）"""
    if API_KEY and x_api_key != API_KEY:
        raise_api_error(401, "AUTH_INVALID_OR_MISSING")


async def require_api_key(x_api_key: Optional[str] = Header(None)):
    """认证接口必须显式配置并提供 API Key。"""
    if not API_KEY or x_api_key != API_KEY:
        raise_api_error(401, "AUTH_INVALID_OR_MISSING")
```

- [ ] **Step 5: Convert existing explicit `HTTPException(..., error_detail(...))` call sites**

For each existing call like:

```python
raise HTTPException(400, error_detail("NO_FACE", "未检测到人脸"))
```

replace it with:

```python
raise_api_error(400, "NO_FACE")
```

For dynamic multiple-face text in `register`, preserve a specific message while still adding `reason`:

```python
raise_api_error(400, "MULTIPLE_FACES", f"检测到 {len(faces)} 张人脸，注册需单人图片")
```

- [ ] **Step 6: Run focused tests**

Run:

```bat
python -m unittest tests.test_main_api.MainApiContractTests.test_auth_errors_return_chinese_reason_payload tests.test_main_api.MainApiContractTests.test_known_error_detail_includes_reason
```

Expected: both tests pass.

- [ ] **Step 7: Commit**

```bat
git add main.py tests/test_main_api.py
git commit -m "feat: standardize api error payloads"
```

## Task 2: Add Image Size and Pixel Validators

**Files:**
- Modify: `main.py`
- Test: `tests/test_main_api.py`

- [ ] **Step 1: Write failing tests for upload bytes, decoded bytes, and pixels**

Add these tests to `tests/test_main_api.py`:

```python
    def test_decode_base64_rejects_decoded_bytes_over_limit(self):
        module = load_main_module()
        module.MAX_IMAGE_BYTES = 3
        payload = "YWJjZA=="  # b"abcd"

        with self.assertRaises(HTTPException) as exc_info:
            module.decode_base64(payload)

        self.assertEqual(exc_info.exception.status_code, 413)
        self.assertEqual(exc_info.exception.detail["code"], "IMAGE_TOO_LARGE")
        self.assertIn("超过服务允许", exc_info.exception.detail["reason"])

    def test_decode_image_bytes_rejects_raw_upload_over_limit(self):
        module = load_main_module()
        module.MAX_IMAGE_BYTES = 3

        with self.assertRaises(HTTPException) as exc_info:
            module.decode_image_bytes(b"abcd")

        self.assertEqual(exc_info.exception.status_code, 413)
        self.assertEqual(exc_info.exception.detail["code"], "IMAGE_TOO_LARGE")

    def test_decoded_image_pixels_over_limit_returns_413(self):
        module = load_main_module()
        module.MAX_IMAGE_BYTES = 1024 * 1024
        module.MAX_IMAGE_PIXELS = 3
        module.cv2.imdecode = lambda *_args, **_kwargs: module.np.zeros((2, 2, 3), dtype=module.np.uint8)

        with self.assertRaises(HTTPException) as exc_info:
            module.decode_image_bytes(b"valid-image-bytes")

        self.assertEqual(exc_info.exception.status_code, 413)
        self.assertEqual(exc_info.exception.detail["code"], "IMAGE_PIXELS_TOO_LARGE")
        self.assertEqual(exc_info.exception.detail["message"], "图片分辨率过高")
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bat
python -m unittest tests.test_main_api.MainApiContractTests.test_decode_base64_rejects_decoded_bytes_over_limit tests.test_main_api.MainApiContractTests.test_decode_image_bytes_rejects_raw_upload_over_limit tests.test_main_api.MainApiContractTests.test_decoded_image_pixels_over_limit_returns_413
```

Expected: failure because only Base64 character length is currently checked.

- [ ] **Step 3: Add environment-backed limits**

In `main.py`, replace:

```python
MAX_BASE64_IMAGE_CHARS = 10 * 1024 * 1024
```

with:

```python
MAX_BASE64_IMAGE_CHARS = int(os.getenv("FACE_MAX_BASE64_CHARS", str(10 * 1024 * 1024)))
MAX_IMAGE_BYTES = int(os.getenv("FACE_MAX_IMAGE_BYTES", str(8 * 1024 * 1024)))
MAX_IMAGE_PIXELS = int(os.getenv("FACE_MAX_IMAGE_PIXELS", str(4_096_000)))
```

- [ ] **Step 4: Add validator helpers**

In `main.py`, place these helpers near the decode helpers:

```python
def validate_image_bytes(image_bytes: bytes) -> None:
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise_api_error(413, "IMAGE_TOO_LARGE")


def validate_decoded_image(image: np.ndarray) -> None:
    height, width = image.shape[:2]
    if height * width > MAX_IMAGE_PIXELS:
        raise_api_error(413, "IMAGE_PIXELS_TOO_LARGE")
```

- [ ] **Step 5: Apply validators to both Base64 and file upload paths**

Update `decode_image_bytes` and `decode_base64`:

```python
def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    validate_image_bytes(image_bytes)
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise_api_error(400, "IMAGE_DECODE_FAILED")
    validate_decoded_image(img)
    return img


def decode_base64(b64_str: str) -> np.ndarray:
    if len(b64_str) > MAX_BASE64_IMAGE_CHARS:
        raise_api_error(413, "IMAGE_TOO_LARGE")
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    try:
        image_bytes = base64.b64decode(b64_str)
    except Exception:
        raise_api_error(400, "IMAGE_DECODE_FAILED")
    return decode_image_bytes(image_bytes)
```

- [ ] **Step 6: Run focused tests**

Run:

```bat
python -m unittest tests.test_main_api.MainApiContractTests.test_decode_base64_rejects_decoded_bytes_over_limit tests.test_main_api.MainApiContractTests.test_decode_image_bytes_rejects_raw_upload_over_limit tests.test_main_api.MainApiContractTests.test_decoded_image_pixels_over_limit_returns_413
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bat
git add main.py tests/test_main_api.py
git commit -m "feat: enforce image input limits"
```

## Task 3: Expose Limits in Effective Configuration

**Files:**
- Modify: `main.py`
- Test: `tests/test_main_api.py`

- [ ] **Step 1: Write failing test for `/config/effective`**

Update `test_config_effective_returns_runtime_defaults` in `tests/test_main_api.py` so the expected body includes:

```python
                "max_base64_image_chars": 10485760,
                "max_image_bytes": 8388608,
                "max_image_pixels": 4096000,
```

The full expected payload should be:

```python
        self.assertEqual(
            body,
            {
                "face_login_threshold": 0.55,
                "auth_enabled": False,
                "force_cpu": False,
                "model": "buffalo_l",
                "det_size": [640, 640],
                "db_path": "faces.db",
                "max_base64_image_chars": 10485760,
                "max_image_bytes": 8388608,
                "max_image_pixels": 4096000,
            },
        )
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bat
python -m unittest tests.test_main_api.MainApiContractTests.test_config_effective_returns_runtime_defaults
```

Expected: failure because the new fields are not returned yet.

- [ ] **Step 3: Extend `EffectiveConfigResp`**

In `main.py`, add fields to `EffectiveConfigResp`:

```python
class EffectiveConfigResp(BaseModel):
    face_login_threshold: float
    auth_enabled: bool
    force_cpu: bool
    model: str
    det_size: list[int]
    db_path: str
    max_base64_image_chars: int
    max_image_bytes: int
    max_image_pixels: int
```

- [ ] **Step 4: Return the fields from `effective_config`**

Update the `effective_config()` return value in `main.py`:

```python
def effective_config():
    return {
        "face_login_threshold": DEFAULT_FACE_LOGIN_THRESHOLD,
        "auth_enabled": bool(API_KEY),
        "force_cpu": FORCE_CPU,
        "model": FACE_MODEL,
        "det_size": [FACE_DET_SIZE, FACE_DET_SIZE],
        "db_path": os.getenv("FACE_DB_PATH", "faces.db"),
        "max_base64_image_chars": MAX_BASE64_IMAGE_CHARS,
        "max_image_bytes": MAX_IMAGE_BYTES,
        "max_image_pixels": MAX_IMAGE_PIXELS,
    }
```

- [ ] **Step 5: Run focused test**

Run:

```bat
python -m unittest tests.test_main_api.MainApiContractTests.test_config_effective_returns_runtime_defaults
```

Expected: pass.

- [ ] **Step 6: Commit**

```bat
git add main.py tests/test_main_api.py
git commit -m "feat: expose image limits in config"
```

## Task 4: Improve FaceEngine Initialization Diagnostics

**Files:**
- Modify: `face_engine.py`
- Test: create `tests/test_face_engine.py`

- [ ] **Step 1: Write failing tests with fake dependencies**

Create `tests/test_face_engine.py`:

```python
import importlib
import sys
import types
import unittest


class FaceEngineInitializationTests(unittest.TestCase):
    def load_face_engine_module(self, prepare_error=None, providers=None):
        providers = providers or ["CPUExecutionProvider"]

        fake_onnxruntime = types.ModuleType("onnxruntime")
        fake_onnxruntime.get_available_providers = lambda: providers

        fake_insightface = types.ModuleType("insightface")
        fake_app_module = types.ModuleType("insightface.app")

        class FakeFaceAnalysis:
            def __init__(self, name=None, providers=None):
                self.name = name
                self.providers = providers

            def prepare(self, ctx_id=None, det_size=None):
                if prepare_error:
                    raise prepare_error

            def get(self, image):
                return []

        fake_app_module.FaceAnalysis = FakeFaceAnalysis
        fake_insightface.app = fake_app_module

        sys.modules["onnxruntime"] = fake_onnxruntime
        sys.modules["insightface"] = fake_insightface
        sys.modules["insightface.app"] = fake_app_module
        sys.modules.pop("face_engine", None)

        return importlib.import_module("face_engine")

    def test_initialization_failure_includes_runtime_context(self):
        module = self.load_face_engine_module(prepare_error=RuntimeError("prepare failed"))

        with self.assertRaises(RuntimeError) as exc_info:
            module.FaceEngine(model_name="buffalo_l", det_size=(640, 640), force_cpu=False)

        text = str(exc_info.exception)
        self.assertIn("FaceEngine initialization failed", text)
        self.assertIn("model=buffalo_l", text)
        self.assertIn("det_size=(640, 640)", text)
        self.assertIn("force_cpu=False", text)
        self.assertIn("CPUExecutionProvider", text)
        self.assertIn("prepare failed", text)

    def test_engine_exposes_provider_context_after_success(self):
        module = self.load_face_engine_module(providers=["CUDAExecutionProvider", "CPUExecutionProvider"])

        engine = module.FaceEngine(model_name="buffalo_l", det_size=(640, 640), force_cpu=False)

        self.assertEqual(engine.model_name, "buffalo_l")
        self.assertEqual(engine.det_size, (640, 640))
        self.assertEqual(engine.available_providers, ["CUDAExecutionProvider", "CPUExecutionProvider"])
        self.assertEqual(engine.selected_provider_names, ["CUDAExecutionProvider", "CPUExecutionProvider"])
        self.assertEqual(engine.device, "GPU (CUDA)")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bat
python -m unittest tests.test_face_engine
```

Expected: failure because `FaceEngine` does not expose all context and does not wrap initialization failures.

- [ ] **Step 3: Store initialization context in `FaceEngine`**

In `face_engine.py`, after deriving `model_name`, `det_size`, `available`, and `providers`, assign:

```python
self.model_name = model_name
self.det_size = det_size
self.force_cpu = force_cpu
self.available_providers = available
self.selected_provider_names = [p if isinstance(p, str) else p[0] for p in providers]
```

Update the existing provider log line:

```python
print(f"[FaceEngine] Using providers: {self.selected_provider_names}")
```

- [ ] **Step 4: Wrap `FaceAnalysis` construction and preparation**

Replace:

```python
self.app = FaceAnalysis(name=model_name, providers=providers)
self.app.prepare(ctx_id=ctx_id, det_size=det_size)
print(f"[FaceEngine] Ready. Running on {self.device}")
```

with:

```python
try:
    self.app = FaceAnalysis(name=model_name, providers=providers)
    self.app.prepare(ctx_id=ctx_id, det_size=det_size)
except Exception as exc:
    raise RuntimeError(
        "FaceEngine initialization failed: "
        f"model={model_name}, det_size={det_size}, force_cpu={force_cpu}, "
        f"available_providers={available}, selected_providers={self.selected_provider_names}. "
        f"Original error: {exc}"
    ) from exc

print(f"[FaceEngine] Ready. Running on {self.device}")
```

- [ ] **Step 5: Run focused tests**

Run:

```bat
python -m unittest tests.test_face_engine
```

Expected: pass.

- [ ] **Step 6: Commit**

```bat
git add face_engine.py tests/test_face_engine.py
git commit -m "feat: improve face engine startup diagnostics"
```

## Task 5: Update Existing Tests for `reason`

**Files:**
- Modify: `tests/test_main_api.py`

- [ ] **Step 1: Replace exact dict assertions that omit `reason`**

In `tests/test_main_api.py`, update assertions like:

```python
self.assertEqual(exc_info.exception.detail, {"code": "NO_FACE", "message": "未检测到人脸"})
```

to:

```python
self.assertEqual(exc_info.exception.detail["code"], "NO_FACE")
self.assertEqual(exc_info.exception.detail["message"], "未检测到人脸")
self.assertTrue(exc_info.exception.detail["reason"])
```

For auth tests, use the exact dict from Task 1.

- [ ] **Step 2: Run all API tests**

Run:

```bat
python -m unittest tests.test_main_api
```

Expected: pass.

- [ ] **Step 3: Run storage tests**

Run:

```bat
python -m unittest tests.test_storage_schema
```

Expected: pass.

- [ ] **Step 4: Commit**

```bat
git add tests/test_main_api.py
git commit -m "test: align api assertions with error reasons"
```

## Task 6: Update Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/04_usage/01_api_integration.md`
- Modify: `docs/05_architecture/01_architecture.md`

- [ ] **Step 1: Update `README.md` environment variables**

Add these rows to the existing environment variable table:

```markdown
| `FACE_MAX_BASE64_CHARS` | `10485760` | Base64 图片字符串最大长度 |
| `FACE_MAX_IMAGE_BYTES` | `8388608` | 解码后图片字节最大值 |
| `FACE_MAX_IMAGE_PIXELS` | `4096000` | 解码后图片最大像素数 |
```

- [ ] **Step 2: Update `README.md` startup troubleshooting**

Add this note near the GPU / CPU troubleshooting section:

```markdown
### 模型初始化失败怎么看

如果服务启动时报 `FaceEngine initialization failed`，优先看错误中的：
- `model`
- `det_size`
- `force_cpu`
- `available_providers`
- `selected_providers`
- `Original error`

这几个字段可以判断是模型下载/路径问题、CUDA provider 问题，还是输入配置问题。
```

- [ ] **Step 3: Update `docs/04_usage/01_api_integration.md` error section**

Replace the current “两种形态” explanation with:

```markdown
### 5.3 错误结构

错误统一走 FastAPI `detail` 字段，`detail` 是对象：

```json
{
  "detail": {
    "code": "NO_FACE",
    "message": "未检测到人脸",
    "reason": "图片中没有检测到可用于识别的人脸，请调整光线、角度或距离后重试"
  }
}
```

- `code`：稳定英文错误码，给前端和业务系统判断逻辑使用。
- `message`：短中文提示，适合 toast、弹窗标题。
- `reason`：较完整的中文原因和处理建议，适合详情提示、日志和客服排查。
```

- [ ] **Step 4: Update frontend error handling snippet**

In `docs/04_usage/01_api_integration.md`, update the frontend handling snippet to prefer `reason`:

```javascript
if (!res.ok) {
  const detail = data && data.detail;
  const errorMessage =
    (detail && typeof detail === "object" && detail.reason) ||
    (detail && typeof detail === "object" && detail.message) ||
    (typeof detail === "string" && detail) ||
    "请求失败";
  throw new Error(errorMessage);
}
```

- [ ] **Step 5: Update `docs/05_architecture/01_architecture.md`**

Add this policy text to the image input or API boundary section:

```markdown
### 图片输入保护

所有图片入口必须经过统一校验：
- Base64 字符串长度不能超过 `FACE_MAX_BASE64_CHARS`
- 解码后的图片字节不能超过 `FACE_MAX_IMAGE_BYTES`
- OpenCV 解码后的像素总数不能超过 `FACE_MAX_IMAGE_PIXELS`

文件上传和 Base64 输入共用同一套字节和像素校验，避免不同入口出现不同资源消耗边界。
```

- [ ] **Step 6: Commit**

```bat
git add README.md docs/04_usage/01_api_integration.md docs/05_architecture/01_architecture.md
git commit -m "docs: document api hardening behavior"
```

## Task 7: Full Verification

**Status:** Complete. Final verification was run after merging to `main`; `35` unittest tests passed.

**Files:**
- Read: `main.py`
- Read: `face_engine.py`
- Read: `tests/test_main_api.py`
- Read: `tests/test_face_engine.py`
- Read: `README.md`
- Read: `docs/04_usage/01_api_integration.md`
- Read: `docs/05_architecture/01_architecture.md`

- [x] **Step 1: Run the full unittest suite**

Run:

```bat
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [x] **Step 2: Verify OpenAPI imports without real model through existing fake tests**

Run:

```bat
python -m unittest tests.test_main_api.MainApiContractTests.test_system_status_returns_runtime_summary tests.test_main_api.MainApiContractTests.test_config_effective_returns_runtime_defaults
```

Expected: both pass.

- [x] **Step 3: Manually inspect changed error call sites**

Run:

```bat
Select-String -Path main.py -Pattern "HTTPException\\(|error_detail\\(|raise_api_error\\(" -Context 0,1
```

Expected:
- `HTTPException` appears only in imports, tests, or intentional direct FastAPI use if still needed.
- Route and helper errors use `raise_api_error(...)`.
- `error_detail(...)` is used by `raise_api_error` and any audit-specific helper that needs a payload.

- [x] **Step 4: Check docs mention all new fields**

Run:

```bat
Select-String -Path README.md,docs\04_usage\01_api_integration.md,docs\05_architecture\01_architecture.md -Pattern "FACE_MAX_BASE64_CHARS|FACE_MAX_IMAGE_BYTES|FACE_MAX_IMAGE_PIXELS|reason|FaceEngine initialization failed"
```

Expected: all patterns appear in the relevant docs.

- [x] **Step 5: Final commit if verification required fixes**

If Step 1 through Step 4 required any fixes, commit the fixes:

```bat
git add main.py face_engine.py tests README.md docs/04_usage/01_api_integration.md docs/05_architecture/01_architecture.md
git commit -m "chore: verify face api hardening"
```

If no files changed during verification, skip this commit.

## Self-Review

- Spec coverage: Tasks 1 and 5 cover unified tests and error structure. Tasks 2 and 3 cover image limits and config exposure. Task 4 covers startup diagnostics. Task 6 covers documentation. Task 7 covers verification.
- Placeholder scan: This plan contains concrete file paths, commands, expected outcomes, and code snippets for each code-changing step.
- Type consistency: Error payload fields are consistently `code`, `message`, and `reason`. Limit variables are consistently `MAX_BASE64_IMAGE_CHARS`, `MAX_IMAGE_BYTES`, and `MAX_IMAGE_PIXELS`. Config response fields are consistently `max_base64_image_chars`, `max_image_bytes`, and `max_image_pixels`.

## Execution Options

Plan complete and saved to `docs/90_archive/03_superpowers/01_plans/01_2026-05-31_face_api_hardening.md`. Two execution options:

1. **Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints.
