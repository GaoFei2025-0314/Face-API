# face_api Product Requirements Document

> Version: 1.0  
> Date: 2026-06-05  
> Scope: Overall product direction for the local face recognition REST API

## Spec Kit Working Artifact

This PRD is the product source document. The Spec Kit planning artifact derived from it is:

- `specs/001-face-api-product/spec.md`

Use the Spec Kit artifact when creating implementation plans and task lists. Use this PRD when reviewing product direction, scope boundaries, and roadmap intent.

## 1. Project Positioning

`face_api` is a local Windows workstation REST API for face recognition.

It provides reusable face-recognition capabilities to frontend pages, business backends, desktop terminals, access-control systems, attendance systems, and login workflows.

The service is a face recognition capability base, not a complete user account, permission, or login platform.

The default runtime mode is CPU inference for stable workstation operation. GPU inference can be enabled explicitly with `FACE_USE_GPU=1`. `FACE_FORCE_CPU=1` has the highest priority and forces CPU inference even when GPU is enabled.

## 2. Ultimate Goal

The ultimate goal is to build a small, stable, deliverable, and maintainable face recognition API service that can be reused by multiple business systems.

The service should answer questions such as:

- Is there a face in this image?
- Is there exactly one face in this image?
- What is the extracted face embedding?
- Are two faces likely from the same person?
- Which registered person is most similar to this face?
- Can this face be used as evidence for a business login decision?

The service should not decide final business permissions. It returns recognition evidence and helper results. The caller decides whether a user can log in, enter a door, access a page, or perform a business action.

## 3. Target Users

### Frontend Developers

Frontend developers use Swagger and integration docs to call detection, registration, search, and face-login helper APIs.

They need stable request/response formats, clear Chinese error reasons, and predictable authentication behavior.

### Business Backend Developers

Business backend developers integrate face recognition with existing user tables and permission systems.

They need stable `user_id`, `username`, similarity, threshold, audit, and error semantics.

### Local Terminal / Desktop System Developers

Terminal systems can call `face_api` as a local recognition module.

They may use primitive APIs such as `/extract/base64` and perform their own business orchestration.

### Operators / Delivery Engineers

Operators need clear startup commands, health checks, effective configuration, logs, database backup rules, and troubleshooting guidance.

## 4. Core Use Cases

### 4.1 Health Check

As an operator or caller, I need to check whether the service is alive without authentication.

Required capability:

- `GET /health`

Expected result:

- Returns minimal service status for unauthenticated probing.
- Runtime device and current registered face count are exposed through authenticated `/system/status`.

### 4.2 Runtime Status and Configuration

As an operator or integrator, I need to know what configuration is currently active.

Required capabilities:

- `GET /system/status`
- `GET /config/effective`

Expected result:

- Returns model name, detection size, runtime device, provider information, auth status, CPU/GPU switch state, database path, and image limits.

### 4.3 Face Detection

As a frontend or test page, I need to detect faces in an uploaded image.

Required capabilities:

- `POST /detect`
- `POST /detect/base64`

Expected result:

- Returns face count and visible face attributes.
- Does not expose embedding in ordinary detection responses.

### 4.4 Single-Face Feature Extraction

As a trusted business integration, I need to extract one face embedding from a Base64 image.

Required capability:

- `POST /extract/base64`

Expected result:

- Requires exactly one detected face.
- Returns embedding and face summary when successful.
- Returns stable structured errors for no face, multiple faces, invalid image, or invalid model output.

### 4.5 Face Registration

As a business system, I need to register a user's face into the local face database.

Required capability:

- `POST /faces/register`

Expected result:

- Requires one and only one face.
- Stores `user_id`, `username`, optional metadata, and embedding.
- Returns internal face record ID.

### 4.6 Face Database Management

As an operator or business integration, I need to list and delete registered face records.

Required capabilities:

- `GET /faces`
- `DELETE /faces/{face_id}`

Expected result:

- Lists registered face metadata without exposing embeddings.
- Deletes a face record by internal ID.

### 4.7 One-To-One Face Comparison

As a caller, I need to compare whether two images are likely the same person.

Required capability:

- `POST /compare`

Expected result:

- Uses cosine similarity.
- Returns `similarity`, `threshold`, and `is_same_person`.
- Uses the highest-confidence face if multiple faces are detected.

### 4.8 One-To-Many Face Search

As a caller, I need to search the local face database for the most similar registered faces.

Required capability:

- `POST /search`

Expected result:

- Extracts the best face from the query image.
- Searches local SQLite embeddings.
- Returns top matches with similarity and metadata.

### 4.9 Face Login Helper

As a business system, I need a helper endpoint that performs single-face validation and top-1 matching for login-like flows.

Required capability:

- `POST /auth/face-login`

Expected result:

- Requires explicit API Key configuration.
- Requires exactly one face.
- Uses a minimum authentication threshold.
- Returns matched `user_id` and `username` on success.
- Does not issue token or session.
- Writes success and failure audit records.

### 4.10 Login Audit

As an operator or business system, I need to inspect recent face login attempts.

Required capabilities:

- `GET /audit/login/recent`
- `GET /audit/login/summary`

Expected result:

- Returns recent login audit records.
- Returns success/failure counts and success rate.

## 5. Functional Scope

### 5.1 In Scope

- FastAPI REST service.
- Local Windows workstation deployment.
- CPU-first inference with optional GPU switch.
- InsightFace model initialization.
- ONNX Runtime provider selection.
- OpenCV image decoding.
- Base64 and file upload image inputs.
- Image byte, Base64 length, and pixel limits.
- Face detection.
- Face embedding extraction.
- 1:1 comparison.
- 1:N search.
- Local SQLite face database.
- Face registration, listing, deletion.
- Face login helper.
- Login audit.
- Health, runtime status, and effective configuration endpoints.
- API Key authentication.
- Structured errors with `detail.code`, `detail.message`, and `detail.reason`.
- Tests for core API contracts and runtime behavior.
- Documentation for setup, integration, architecture, and delivery.

### 5.2 Out of Scope

- Full user account system.
- Password login.
- Token or session issuing.
- RBAC or business permission decisions.
- Business user table management.
- Complete frontend product.
- Centralized multi-tenant platform.
- Distributed deployment.
- Large-scale vector database by default.
- Liveness detection by default.
- Automatic face quality governance platform.
- Moving terminal-specific business rules into `face_api`.

## 6. Non-Functional Requirements

### 6.1 Stability

- The service should start predictably on a Windows workstation.
- Default inference should use CPU to reduce GPU dependency and startup risk.
- GPU inference should be opt-in through `FACE_USE_GPU=1`.
- Model initialization failures should include model, detection size, CPU/GPU flags, available providers, selected providers, and original error.
- The service should avoid creating `FaceEngine` inside request handlers.

### 6.2 Security

- `/health` remains public.
- Sensitive and business APIs should require API Key when `FACE_API_KEY` is configured.
- `/auth/face-login`, `/extract/base64`, `/system/status`, `/config/effective`, and audit APIs require explicit API Key behavior.
- Embeddings should not be exposed from ordinary detection, search, list, or login responses.
- Production deployments should restrict CORS to known frontend origins.
- Image inputs must be size-limited to reduce resource abuse.

### 6.3 Performance

- CPU is the default stability path.
- GPU can be enabled when higher throughput is required and CUDA is verified.
- Compute-heavy endpoints should return `elapsed_ms`.
- SQLite + NumPy search is acceptable for MVP and small-to-medium local face databases.
- If face database size grows significantly, add memory vector cache first before considering Faiss.

### 6.4 Maintainability

- Keep the MVP shape small.
- Core business code should remain understandable through:
  - `main.py` for API orchestration.
  - `face_engine.py` for model inference.
  - `storage.py` for SQLite persistence and search.
- Avoid introducing large frameworks unless the current structure becomes a real maintenance blocker.
- Update docs when API behavior, environment variables, response models, or deployment expectations change.

### 6.5 Deliverability

- New maintainers should be able to start with README.
- Frontend/backend integrators should be able to use `docs/04_usage/01_api_integration.md`.
- Architecture and operational boundaries should be documented in `docs/05_architecture/01_architecture.md`.
- Swagger should remain available at `/docs`.
- OpenAPI should remain available at `/openapi.json`.

### 6.6 Data Safety

- `faces.db` and related SQLite WAL files are core business assets.
- Backup guidance must clearly state which files to back up and when to stop the service.
- Recovery guidance should be simple enough for a delivery engineer to follow.

## 7. API Capability Layers

### 7.1 Runtime Primitives

These endpoints provide base runtime capabilities for integration and diagnostics:

- `GET /health`
- `GET /system/status`
- `GET /config/effective`
- `POST /extract/base64`

### 7.2 Library Helpers

These endpoints expose reusable face database and search capabilities:

- `POST /detect`
- `POST /detect/base64`
- `POST /compare`
- `POST /search`
- `POST /faces/register`
- `GET /faces`
- `DELETE /faces/{face_id}`

### 7.3 Auth Helpers

These endpoints assist login-like flows but do not replace business authentication systems:

- `POST /auth/face-login`

### 7.4 Ops Helpers

These endpoints support operational review and troubleshooting:

- `GET /audit/login/recent`
- `GET /audit/login/summary`

## 8. Error Contract

All business-facing errors should use FastAPI `detail` with a structured object:

```json
{
  "detail": {
    "code": "NO_FACE",
    "message": "未检测到人脸",
    "reason": "图片中没有检测到可用于识别的人脸，请调整光线、角度或距离后重试"
  }
}
```

Field meanings:

- `code`: stable English machine-readable error code.
- `message`: short Chinese display message.
- `reason`: longer Chinese cause and remediation guidance.

Frontend and business systems should branch on `code`, display `message`, and use `reason` for detailed hints, logs, and support.

## 9. Runtime Configuration

Key environment variables:

| Variable | Default | Purpose |
|---|---:|---|
| `FACE_MODEL` | `buffalo_l` | InsightFace model name |
| `FACE_DET_SIZE` | `640` | Face detection input size |
| `FACE_DB_PATH` | `faces.db` | SQLite database path |
| `FACE_USE_GPU` | `0` | Set `1` to allow GPU inference |
| `FACE_FORCE_CPU` | `0` | Set `1` to force CPU and override `FACE_USE_GPU` |
| `FACE_API_KEY` | empty | Enables API Key authentication when set |
| `FACE_MAX_BASE64_CHARS` | `11185068` | Max Base64 image string length |
| `FACE_MAX_IMAGE_BYTES` | `8388608` | Max decoded image bytes |
| `FACE_MAX_IMAGE_PIXELS` | `4096000` | Max decoded image pixels |

Runtime selection rule:

1. Default: CPU.
2. If `FACE_USE_GPU=1`: try CUDA provider when available.
3. If `FACE_FORCE_CPU=1`: force CPU regardless of `FACE_USE_GPU`.

## 10. Phased Roadmap

### Phase 1: MVP Capability Base

Status: mostly complete.

Goals:

- Provide detection, comparison, search, registration, and login helper APIs.
- Persist local face database in SQLite.
- Provide Swagger/OpenAPI for integration.
- Provide basic health check.

### Phase 2: Contract Hardening

Status: mostly complete.

Goals:

- Structured errors with Chinese reasons.
- Image input limits.
- Model initialization diagnostics.
- Unit tests for API contracts.
- Effective configuration endpoint.

### Phase 3: Workstation Production Hardening

Status: mostly complete.

Goals:

- File-based structured logs.
- Startup configuration validation.
- Production startup script without `--reload`.
- Windows service or scheduled-task guidance.
- CORS production configuration.
- Database backup and recovery instructions.

### Phase 4: Search Performance Improvement

Status: mostly complete for benchmark and scale planning; index remains optional.

Goals:

- Add in-memory embedding cache.
- Refresh cache after registration/deletion.
- Keep SQLite as durable source of truth.
- Measure search performance at target database sizes.

### Phase 5: Face Quality and Registration Governance

Status: mostly complete for current quality policy and tuning needs.

Goals:

- Reject low-quality registration images.
- Define duplicate registration policy.
- Clarify whether one `user_id` can have multiple faces.
- Add quality hints for detection score, face size, brightness, and pose if needed.

### Phase 6: Advanced Optional Capabilities

Status: explicitly optional.

Possible capabilities:

- Liveness detection.
- Faiss vector index.
- Larger deployment topology.
- Multi-terminal synchronization.
- Centralized management dashboard.

These should only be implemented after a real business need is confirmed.

### Phase 7: Field Acceptance and Windows Long Running

Status: complete for Roadmap V1.7.1 and V1.7.2.

Goals:

- Run the real camera register + login loop through `camera-integration.html`.
- Show liveness status, Chinese error reasons, and recent login audit in the same local page.
- Keep the local page as a field acceptance tool, not a full business frontend.
- Provide Task Scheduler and NSSM options for long-running Windows workstation operation.
- Provide install/uninstall scripts for both long-running options.
- Keep stronger anti-spoofing models and Faiss/ANN index out of V1.7 unless separately approved.

### Phase 8: Field Delivery And Maintainability

Status: complete for Roadmap V1.8.

Goals:

- Make the local acceptance and runtime status flow easier for field operators.
- Reduce `main.py` complexity without changing public API behavior.
- Keep the interactive architecture page useful for training and handoff.
- Keep documentation entry points aligned with actual completed versions.

### Phase 9: Field Acceptance Closure

Status: complete for Roadmap V1.9.

Goals:

- Verify Windows workstation startup, health, protected status, monitoring, and stop flows.
- Verify the real camera register + login loop through `camera-integration.html`.
- Verify Chinese error reasons, recent login audit, maintenance mode, backup, and restore.
- Fix only confirmed P1/P2 issues found during acceptance; record P3/P4 issues for later.
- Keep public APIs, environment variables, and authentication behavior stable unless a P1/P2 fix explicitly requires a documented change.

### Phase 10: Business System Integration Demo

Status: planned for Roadmap V2.0.

Goals:

- Provide an independent mock business backend that demonstrates the recommended production integration pattern.
- Keep `face_api` as a recognition service and keep business users, login state, permissions, and business audit in the business system.
- Demonstrate Web browser -> business backend -> `face_api` so browsers do not hold `X-API-Key`.
- Demonstrate controlled terminal -> `face_api` -> business backend for kiosk, gate, and Windows client scenarios.
- Provide binding, unbinding, face replacement, face login, demo JWT, terminal event reporting, and business login audit in the demo layer.
- Provide Java / Spring Boot pseudocode so a real Java backend can replace the mock backend.

## 11. Acceptance Criteria

The product direction is satisfied when:

- The service can be started on the target Windows workstation.
- Default inference uses CPU.
- GPU inference can be enabled with `FACE_USE_GPU=1`.
- `/health` works without authentication.
- Business-sensitive APIs support API Key protection.
- Swagger and OpenAPI are reachable.
- Core APIs return stable documented response shapes.
- Error responses include `code`, `message`, and `reason`.
- The service can register, list, delete, search, compare, and authenticate helper flows.
- Embeddings are not leaked from ordinary user-facing APIs.
- Login audit records can be queried.
- Tests cover core API contracts and device selection behavior.
- Documentation explains setup, integration, architecture, and operational boundaries.

## 12. Development Principles

- Build the recognition service as a reusable capability module, not a full business platform.
- Keep interfaces stable before adding more features.
- Prefer small, testable changes.
- Do not introduce PyTorch.
- Do not install both `onnxruntime` and `onnxruntime-gpu` in the same environment.
- Keep image processing in OpenCV BGR unless there is a verified reason to change.
- Keep SQLite as source of truth until scale requires a different design.
- Add performance complexity only after measuring a real bottleneck.
- Keep docs synchronized with API and environment changes.

## 13. Open Decisions

These decisions should be resolved before related development begins:

1. Whether one business `user_id` may register multiple face records.
2. Whether duplicate registration should reject, replace, or allow additional records.
3. What production CORS origins should be allowed.
4. Whether production must fail startup when `FACE_API_KEY` is empty.
5. What face database size should trigger memory cache work.
6. Whether liveness detection is required for the target business scenario.
7. Whether `/extract/base64` should remain trusted-backend-only because it returns embeddings.
