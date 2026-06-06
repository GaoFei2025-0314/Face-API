# Face API Modularization Review

## Scope reviewed

Changed files in this phase:

- `main.py`
- `storage.py`
- `tests/test_main_api.py`
- `tests/test_storage_schema.py`
- `README.md`
- `docs/04_usage/01_api_integration.md`
- `docs/05_architecture/01_architecture.md`

Verification performed:

- `D:/anaconda3/envs/face_api/python.exe -m unittest H:/AI_test/face_api/tests/test_main_api.py H:/AI_test/face_api/tests/test_storage_schema.py -v`
- `D:/anaconda3/envs/face_api/python.exe -m py_compile H:/AI_test/face_api/main.py H:/AI_test/face_api/storage.py H:/AI_test/face_api/tests/test_main_api.py H:/AI_test/face_api/tests/test_storage_schema.py`

## Findings summary

CRITICAL (0)
- None.

MAJOR (1)
- `main.py` — `/extract/base64` returns raw face embeddings to callers. This is a deliberate but high-sensitivity contract choice, not an accidental bug.

MINOR (resolved during review)
- Restored `faces` table creation for fresh databases in `storage.py`.
- Restored legacy conditional auth on `/faces/register`, `/faces`, `/faces/{face_id}`, `/search`.
- Unified structured error contracts for primitive and helper endpoints.
- Added login audit storage and query endpoints.
- Added `/config/effective` and `/system/status` contract coverage.
- Synced README / frontend doc / technical guide to current API contract.

NIT (not blocking)
- Documentation was heavily reflowed across multiple passes; a future cleanup pass could further reduce duplication.

## Correctness review

### Fixed in this phase
- Fresh schema initialization now creates both `faces` and `face_login_audit` before migrations/index creation.
- Sensitive new endpoints (`/extract/base64`, `/system/status`, `/config/effective`, audit endpoints, `/auth/face-login`) require explicit API key auth.
- Legacy routes that the project contract said should remain conditional auth were reverted to `verify_api_key`.
- `/compare` and `/search` now return structured `NO_FACE` failures.
- `/auth/face-login` now writes success/failure audit entries and exposes structured failure codes.

### Remaining architectural decision
- `/extract/base64` returns raw embeddings by design so controlled desktop/terminal consumers can perform local matching and higher-level workflows.
- This is useful and aligned with the modular primitive goal, but it is also the highest-risk contract in this phase.

## Security review

### Remaining major risk
- `POST /extract/base64` returns reusable biometric templates (`embedding`) to any caller that holds a valid `X-API-Key`.
- Exploit scenario: an attacker who gets a shared API key from a compromised terminal, leaked config, or internal misuse can upload employee photos, export embeddings, and build an offline shadow biometric index for cross-system correlation.
- This is not a code bug; it is a product/security boundary choice.

### Recommended boundary if keeping current design
If this endpoint remains:
- treat it as a controlled integration primitive only
- do not expose it to browser-facing apps directly
- do not embed its API key in ordinary frontend pages
- prefer desktop/main-process/server-side callers
- document the risk explicitly

## DX review

### Time-to-hello-world
Good. A consumer can now:
1. call `/system/status` to verify runtime state,
2. call `/config/effective` to discover active config,
3. call `/extract/base64` to get a single-face primitive,
4. choose `/auth/face-login` or their own matching flow.

### Error clarity
Improved. Structured `detail.code` / `detail.message` is now available on the key primitive/helper routes, and the frontend sample handles object-shaped `detail`.

### Magical moment
The new `POST /extract/base64` is the magical moment for integrators: one request yields either a usable single-face primitive or an unambiguous reason it cannot proceed.

## Recommendation

This phase is functionally solid and test-green.

Remaining decision required:
- **Accept** the controlled-risk design that `/extract/base64` may return embeddings to trusted callers, or
- **Tighten** the design in a follow-up phase by removing raw embedding output or replacing it with a more constrained evidence format.

## Reviewer conclusion

- All correctness blockers from this implementation phase were fixed.
- No CRITICAL issues remain.
- One MAJOR product/security decision remains open by design: raw embedding exposure in `/extract/base64`.

If the team explicitly accepts that boundary for trusted integrations, this phase is ready for `/do-ship`.
