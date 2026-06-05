# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project snapshot

`face_api` is a local Windows REST API for face recognition. It uses FastAPI for HTTP routes, InsightFace for detection/recognition, ONNX Runtime GPU for inference, and SQLite for the face database. The deployment target is a single Windows workstation running Python 3.10.x, with GPU-first execution and CPU fallback.

Keep the MVP shape small: the business code currently lives in `main.py`, `face_engine.py`, and `storage.py`. Prefer extending these files while they remain focused and under roughly 500 lines. Do not framework-ize `test.html` or the `.bat` scripts.

## Common commands

Use Windows commands unless the user explicitly asks for another shell.

```bat
:: one-time setup, uses the Python path configured in setup.bat
setup.bat

:: start development server
run.bat

:: manual setup / install GPU dependencies
D:\dev\python3.1\python.exe -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

:: CPU-only install for machines without NVIDIA GPU
pip install -r requirements-cpu.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

:: run API manually
venv\Scripts\activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

:: multi-worker mode for higher throughput
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Verification commands:

```bat
:: health check; expected device is GPU (CUDA) on the target workstation
curl http://localhost:8000/health

:: OpenAPI should be reachable
curl http://localhost:8000/openapi.json

:: verify ONNX Runtime providers
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```

There is no test suite, linter config, or pytest configuration in the current repo. For endpoint checks, start the server and use `curl`, Swagger UI at `http://localhost:8000/docs`, or `test.html`.

## Runtime constraints

- Python target: 3.10.x.
- Default GPU dependencies come from `requirements.txt`; CPU fallback dependencies come from `requirements-cpu.txt`.
- Keep `numpy<2.0`; InsightFace/ONNX Runtime are not compatible with NumPy 2.x here.
- Do not install both `onnxruntime` and `onnxruntime-gpu` in the same environment.
- Do not introduce PyTorch; inference is pure ONNX Runtime.
- The default model is `buffalo_l`, downloaded by InsightFace into `~/.insightface/models/buffalo_l/` on first run.

Environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `FACE_MODEL` | `buffalo_l` | InsightFace model name |
| `FACE_DET_SIZE` | `640` | Detection input size |
| `FACE_DB_PATH` | `faces.db` | SQLite database path |
| `FACE_FORCE_CPU` | `0` | Set `1` to force CPU inference |
| `FACE_API_KEY` | empty | Enables `X-API-Key` auth when set |

## Architecture

### `main.py`

Contains the FastAPI app, Pydantic request/response models, CORS config, optional API-key auth, and all routes. Module import initializes global singletons:

```python
engine = FaceEngine(force_cpu=os.getenv("FACE_FORCE_CPU", "0") == "1")
db = FaceDB()
```

Do not create `FaceEngine()` inside request handlers; it loads a large InsightFace model. `/health` is intentionally unauthenticated. Authenticated routes use `Depends(verify_api_key)`, and auth is disabled when `FACE_API_KEY` is empty.

Current route groups:

- System: `GET /`, `GET /health`
- Detection: `POST /detect`, `POST /detect/base64`
- Comparison: `POST /compare`
- Face database: `POST /faces/register`, `GET /faces`, `DELETE /faces/{face_id}`
- Search: `POST /search`
- Auth: `POST /auth/face-login`

Image inputs are OpenCV BGR arrays after decoding. Base64 inputs support strings with or without a `data:image/...;base64,` prefix.

### `face_engine.py`

Wraps InsightFace `FaceAnalysis`. It chooses `CUDAExecutionProvider` when available unless `FACE_FORCE_CPU=1`; otherwise it uses CPU. GPU mode sets a 4 GB ONNX Runtime memory limit for the target 1080 Ti machine.

`FaceEngine.analyze(image)` returns face dictionaries with `bbox`, `det_score`, `landmarks`, `embedding`, `gender`, and `age`. Embeddings are 512-dimensional float vectors. Keep images in BGR; converting to RGB before analysis hurts recognition quality.

### `storage.py`

`FaceDB` owns SQLite persistence. It uses thread-local SQLite connections, WAL mode, a 64 MB cache, and periodic passive checkpoints after writes. Embeddings are stored as float32 BLOBs, not JSON arrays.

Use the `FaceDB` interface instead of direct SQLite access from routes:

- `add(username, embedding, metadata=None, user_id=None) -> str`
- `remove(face_id) -> bool`
- `list_all() -> list`
- `count() -> int`
- `search(query_embedding, top_k=5, threshold=0.5) -> list`
- `close()`

`search()` performs full-table NumPy vectorized cosine similarity. Do not replace it with per-row Python similarity loops.

## API behavior to preserve

- `/faces/register` requires exactly one detected face; zero or multiple faces return HTTP 400. It stores internal face `id` plus optional external `user_id` and required `username`.
- `/compare` returns HTTP 400 if either image has no face; if multiple faces exist, use the highest `det_score` face from each image.
- `/search` returns HTTP 400 if no face is detected; if multiple faces exist, use the highest `det_score` face.
- `/auth/face-login` requires `FACE_API_KEY`, requires exactly one detected face, and returns the matched `user_id` / `username` for the business system to query its user table.
- Never return `embedding` to the frontend; use `strip_embedding()` or equivalent filtering.
- Error responses should remain FastAPI `HTTPException` responses shaped as `{ "detail": "..." }`.
- Similarity fields are named `similarity` and use cosine similarity in `[-1, 1]`.
- Compute-heavy responses include `elapsed_ms`, rounded to two decimals.
- Do not add auth to `/health`.
- Keep writes transactional through `with self._conn() as c:` in `FaceDB`.

## Documentation coupling

When API behavior, request/response models, environment variables, setup, or frontend-facing semantics change, update the relevant docs together:

- `README.md` for setup/run/operator guidance.
- `docs/usage/API_INTEGRATION.md` for frontend contract changes.
- `HOW_TO_DELIVER.md` for deployment/hand-off changes when applicable.

## Adding or changing endpoints

For new endpoints, follow the existing `main.py` pattern: define Pydantic request/response models near the other schemas, add a route with a Chinese Swagger summary/docstring, include `dependencies=[Depends(verify_api_key)]` unless it is intentionally public, decode images through existing helpers, call the module-level `engine`, and return `elapsed_ms` for compute-heavy work.

If an endpoint accepts images, preserve both upload and Base64 support when it is part of the public API contract.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->
