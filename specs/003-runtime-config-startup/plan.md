# Implementation Plan: Runtime Configuration and Startup Validation

## Objective

Make runtime configuration visible, validated, and beginner-readable.

## Scope

- Environment parsing helpers
- Numeric config validation
- Database path writability validation
- Effective configuration fields
- CPU/GPU switch visibility

## Implementation Notes

- Invalid integer environment values raise `RuntimeError` at startup.
- Production-like mode is `FACE_ENV=production` or `FACE_ENV=prod`.
- Effective config exposes environment, CORS origins, log path, duplicate policy, and image limits.

## Verification

- Unit tests cover invalid image limit and production API-key validation.
- API contract tests cover effective config output.

