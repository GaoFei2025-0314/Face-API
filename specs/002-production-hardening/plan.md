# Implementation Plan: Production Hardening

## Objective

Make `face_api` stable for production-like Windows workstation operation.

## Scope

- Production startup path without `--reload`
- Startup context logging
- Production API key guard
- Operator runbook

## Implementation Notes

- `run-prod.bat` is the production startup entry.
- `FACE_ENV=production` requires `FACE_API_KEY`.
- Startup config is logged to `FACE_LOG_PATH`.
- Detailed runbook is in `docs/deployment/RUNBOOK.md`.

## Verification

- Unit tests cover production API-key startup failure.
- Manual verification uses `scripts/health-check.ps1`.

