# Implementation Plan: Search Performance Improvement

## Objective

Improve search performance through measured, low-complexity caching.

## Scope

- In-memory normalized embedding cache
- Cache invalidation after writes/deletes
- Cache status visibility

## Implementation Notes

- SQLite remains the durable source of truth.
- Cache is lazy-loaded on search/status access.
- Add/remove/remove-by-user mark cache dirty.

## Verification

- Storage tests cover cache readiness and record count.
- Full API status exposes cache state.

