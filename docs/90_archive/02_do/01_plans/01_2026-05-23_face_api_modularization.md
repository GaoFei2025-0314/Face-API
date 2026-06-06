# Face API Modularization Implementation Plan

> Required sub-skills: `do-build` will dispatch this task-by-task using subagents and TDD.

## CEO review

Decision: **HOLD SCOPE**

The wedge is right-sized. The highest-leverage step is to establish a reusable recognition primitive layer, not to expand toward a full login platform or reduce to a purely cosmetic refactor.

## Engineering review

### Data flow

```text
[client image base64]
        ↓
 [decode_base64]
        ↓
 [FaceEngine.analyze]
        ↓
 ┌──────────────────────────────────────┐
 │ single-face outcome router           │
 │ - no face                            │
 │ - multiple faces                     │
 │ - single face + embedding            │
 └──────────────────────────────────────┘
        ↓
 ┌──────────────────────┬──────────────────────────┬───────────────────────┐
 │ /extract/base64      │ /detect/base64          │ /auth/face-login      │
 │ primitive evidence   │ display-friendly faces  │ auth helper           │
 └──────────────────────┴──────────────────────────┴───────────────────────┘
        ↓                                      ↓
 [structured response + code]           [db.search + threshold]
        ↓                                      ↓
 [consumer app]                         [auth result / failure]

[system config/env] → [/system/status] → [consumer ops / diagnostics]
```

### Failure modes

1. **Image decode failure**
   - Detection: invalid base64 / OpenCV decode returns `None`
   - Recovery: return stable `IMAGE_DECODE_FAILED` code with HTTP 400

2. **No face / multiple faces ambiguity**
   - Detection: `engine.analyze()` returns `0` or `>1` faces
   - Recovery: return stable `NO_FACE` / `MULTIPLE_FACES` codes and avoid hidden fallback behavior

3. **Embedding response inconsistency**
   - Detection: single face exists but embedding is missing/invalid length
   - Recovery: return `INVALID_EMBEDDING_RESPONSE`; never silently coerce partial data

4. **Auth helper remains semantically inconsistent with primitive layer**
   - Detection: `/auth/face-login` still uses opaque `detail`-only failures
   - Recovery: refactor auth route to reuse the same outcome normalization logic and codes

5. **Status endpoint drifts from runtime truth**
   - Detection: `/system/status` duplicates config logic in multiple places
   - Recovery: centralize status assembly in one helper that reads engine/db/env once

### Test matrix

**Unit**
- Outcome normalization helper returns the correct code/message payload for:
  - image decode failure
  - no face
  - multiple faces
  - invalid embedding
  - success
- Status builder returns expected shape from current engine/db/env state.

**Integration**
- `POST /extract/base64`:
  - invalid image → 400 + code
  - no face → 400 + code
  - multiple faces → 400 + code
  - single face → 200 + embedding + face summary
- `GET /system/status` returns expected fields.
- `POST /auth/face-login` failure payload is upgraded to structured response.

**E2E / smoke**
- Start app, hit `/health`, `/system/status`, `/openapi.json`
- Verify `/extract/base64` is present in OpenAPI and reachable
- Verify docs remain coherent after route additions

## DX review

### Time to hello-world
Current “hello world” for consumers is not ideal because there is no single primitive endpoint that says: “Here is the one face embedding or why you did not get one.” Adding `/extract/base64` fixes the shortest path for integrators.

### Error message clarity
Current `detail`-only responses are readable for humans but weak for client logic. Introducing stable `code` fields gives downstream apps deterministic branching while preserving readable messages.

### Magical moment
The first magical moment should be: a consumer sends one base64 image and immediately gets either a usable embedding or an unambiguous reason it cannot proceed. That is the correct “hello world” for a reusable recognition module.

## Files touched

- `main.py` — modified, adds `/extract/base64`, `/system/status`, response normalization, and structured auth-helper failures
- `README.md` — modified, documents the new primitive/status endpoints and modular API layering

## Tasks

### Task 1: Add failing test notes for primitive extract contract

**Context**: There is no real test suite in this repo, so the first task establishes a test scaffold plan inside the main file-level implementation cycle and defines the exact contract to satisfy.

**RED** (write failing test):
- File: `main.py`
- [ ] Add a temporary test plan comment block or adjacent developer note describing `/extract/base64` expected cases before implementation work begins
- [ ] Exact cases: invalid image, no face, multiple faces, valid single face
- [ ] Verify current code does not expose such endpoint

**GREEN** (minimal implementation):
- File: `main.py`
- [ ] Add request/response model skeletons for `/extract/base64`
- [ ] Wire route placeholder that returns not-yet-correct behavior
- [ ] Confirm route exists in code path

**REFACTOR** (cleanup):
- [ ] Remove placeholder once real helper is in place
- [ ] Keep file readability intact

**Done when**: `/extract/base64` route and schema placeholders exist and prepare the real implementation without expanding scope.

### Task 2: Normalize image decode and face outcome codes

**Context**: All later tasks depend on one shared outcome vocabulary instead of ad hoc `HTTPException(detail=...)` strings.

**RED** (write failing test):
- File: `main.py`
- [ ] Define exact outcome codes in prose: `IMAGE_DECODE_FAILED`, `NO_FACE`, `MULTIPLE_FACES`, `INVALID_EMBEDDING_RESPONSE`
- [ ] Verify current route logic does not produce these codes

**GREEN** (minimal implementation):
- File: `main.py`
- [ ] Introduce a small helper for structured error payloads
- [ ] Introduce a helper that extracts exactly one face or returns structured failure metadata
- [ ] Reuse existing decode helpers where possible

**REFACTOR** (cleanup):
- [ ] Keep helpers compact and local to `main.py`
- [ ] Avoid duplicating logic between `/compare`, `/search`, `/auth/face-login`, and `/extract/base64`

**Done when**: one reusable path exists for single-face extraction outcomes and stable codes are defined in code.

### Task 3: Implement `/extract/base64` success path

**Context**: This is the core primitive endpoint consumers will call to obtain embedding evidence.

**RED** (write failing test):
- File: `main.py`
- [ ] Exact success contract: single face returns `count`, `code`, `message`, `embedding`, `face`, `elapsed_ms`
- [ ] Verify no existing route returns embedding in this consumer-friendly shape

**GREEN** (minimal implementation):
- File: `main.py`
- [ ] Implement `POST /extract/base64`
- [ ] Use existing `decode_base64`
- [ ] Use shared single-face outcome helper
- [ ] Return embedding only on valid single-face success

**REFACTOR** (cleanup):
- [ ] Reuse existing face stripping logic where useful without leaking embedding to display-oriented routes
- [ ] Keep route concise

**Done when**: `/extract/base64` can return a stable success payload for a single-face image.

### Task 4: Implement `/extract/base64` failure path

**Context**: The primitive is only valuable if failure semantics are deterministic and machine-readable.

**RED** (write failing test):
- File: `main.py`
- [ ] Exact failure cases in prose:
  - invalid image → 400 + `IMAGE_DECODE_FAILED`
  - no face → 400 + `NO_FACE`
  - multiple faces → 400 + `MULTIPLE_FACES`
  - invalid embedding → 500 or 400 + `INVALID_EMBEDDING_RESPONSE` (pick one and make it explicit)

**GREEN** (minimal implementation):
- File: `main.py`
- [ ] Return structured JSON for `/extract/base64` failures
- [ ] Preserve useful human-readable messages
- [ ] Keep HTTP status semantics aligned with current API style

**REFACTOR** (cleanup):
- [ ] Make sure failure payload keys are consistent
- [ ] Avoid accidental divergence from auth-helper failure codes

**Done when**: consumers can branch on `/extract/base64` failures without parsing free-form text.

### Task 5: Add `/system/status` endpoint

**Context**: Consumers need more than `/health`; they need runtime diagnostics and effective status.

**RED** (write failing test):
- File: `main.py`
- [ ] Define required fields in prose: `status`, `device`, `providers` if available, `model`, `det_size`, `auth_enabled`, `faces_count`, `force_cpu`
- [ ] Verify current `/health` and `/` together do not already provide this exact consolidated view

**GREEN** (minimal implementation):
- File: `main.py`
- [ ] Implement `GET /system/status`
- [ ] Assemble values from existing engine, db, and env state
- [ ] Keep `/health` unchanged for backward compatibility

**REFACTOR** (cleanup):
- [ ] Factor shared root/status assembly if needed
- [ ] Keep payload compact and stable

**Done when**: integrators can diagnose effective runtime state from one endpoint.

### Task 6: Upgrade `/auth/face-login` failure responses

**Context**: This route stays as an auth helper, but it should reuse the same machine-readable outcome model.

**RED** (write failing test):
- File: `main.py`
- [ ] Define exact failure branches to expose structured payloads for: no face, multiple faces, no match, missing valid username
- [ ] Verify current code emits only `HTTPException(detail=...)`

**GREEN** (minimal implementation):
- File: `main.py`
- [ ] Refactor `/auth/face-login` to reuse single-face outcome helper
- [ ] Return structured failure JSON with codes while preserving strict auth semantics
- [ ] Keep success payload backward compatible where possible

**REFACTOR** (cleanup):
- [ ] Avoid over-coupling auth helper to the primitive response shape
- [ ] Keep distinction between recognition evidence and auth judgment explicit

**Done when**: `/auth/face-login` remains a helper but exposes failure semantics suitable for client branching.

### Task 7: Update README for modular API layering

**Context**: The service contract is changing; the README must explain the new primitive and status endpoints clearly.

**RED** (write failing test):
- File: `README.md`
- [ ] Identify where current docs do not mention `/extract/base64` or `/system/status`
- [ ] Identify where API layering is still implied rather than stated

**GREEN** (minimal implementation):
- File: `README.md`
- [ ] Add `/extract/base64` and `/system/status` to API overview
- [ ] Add a short modular-layer explanation: primitive vs library vs auth helper
- [ ] Explain intended reuse model briefly

**REFACTOR** (cleanup):
- [ ] Keep README concise and non-redundant with `docs/05_architecture/01_architecture.md`
- [ ] Preserve existing startup guidance

**Done when**: a new integrator can understand the purpose of the new primitive endpoints from README alone.

### Task 8: Refresh technical guide contract notes

**Context**: The handoff doc should reflect the new modular direction and explain when to use `/extract/base64` vs `/detect/base64`.

**RED** (write failing test):
- File: `docs/05_architecture/01_architecture.md`
- [ ] Identify outdated route inventory and route semantics after adding `/extract/base64` and `/system/status`

**GREEN** (minimal implementation):
- File: `docs/05_architecture/01_architecture.md`
- [ ] Document `/extract/base64` as the business-oriented primitive
- [ ] Document `/detect/base64` as display/inspection-oriented detection
- [ ] Document `/system/status` as diagnostics/ops endpoint

**REFACTOR** (cleanup):
- [ ] Keep modular boundary explanation crisp
- [ ] Avoid drifting into future-phase features not implemented yet

**Done when**: the technical guide reflects the new service contract cleanly.

## Estimated build shape

- 8 tasks
- 2 files touched
- Estimated 30-45 min in subagent mode if implementation stays tight
