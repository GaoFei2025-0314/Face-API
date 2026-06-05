# Implementation Plan: Face Database Governance

## Objective

Improve local face record quality and duplicate behavior.

## Scope

- Duplicate policy by `user_id`
- Registration quality checks
- Safe lookup by `user_id`
- Delete records by `user_id` for replacement policy

## Implementation Notes

- `FACE_DUPLICATE_POLICY` supports `allow`, `reject`, and `replace`.
- Registration quality checks use detection score, face box area, and image brightness.
- `/faces/by-user/{user_id}` returns safe face metadata without embeddings.

## Verification

- Unit tests cover reject duplicate policy.
- Unit tests cover low-quality registration rejection.
- Storage tests cover `list_by_user_id` and `remove_by_user_id`.

