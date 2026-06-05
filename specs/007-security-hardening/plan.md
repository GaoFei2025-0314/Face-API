# Implementation Plan: Security Hardening

## Objective

Reduce accidental exposure and misuse in local production-like use.

## Scope

- Configurable CORS origins
- Production API-key requirement
- Sensitive log masking
- Protected route policy preservation
- Image input limits preservation

## Implementation Notes

- `FACE_CORS_ORIGINS` controls browser origins.
- `/health` remains public.
- Sensitive routes continue to require explicit API-key behavior.
- Logs mask API keys, images, and embeddings.

## Verification

- Unit tests cover configured CORS origin parsing.
- Existing route dependency tests cover protected route policy.
- Existing image-limit tests continue to pass.

