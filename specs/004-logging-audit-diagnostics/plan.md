# Implementation Plan: Logging, Audit, and Diagnostics

## Objective

Make failures and runtime behavior diagnosable.

## Scope

- File logger
- Request logging middleware
- Sensitive field masking
- Audit filtering by success and terminal ID
- Search cache state visibility

## Implementation Notes

- Logs default to `logs/face_api.log`.
- `log_event()` masks API keys, images, and embeddings.
- Request logs include method, route, status code, and elapsed time.
- Login audit list supports `success` and `terminal_id` filters.

## Verification

- Unit tests cover sensitive log masking.
- Unit tests cover audit filtering.

