# face_api Roadmap v1.0

> Created: 2026-06-05  
> Purpose: Versioned execution roadmap for future `/goal` work  
> Source: `docs/02_product/01_prd.md` and `specs/001-face-api-product/spec.md`

## 1. Roadmap Version

This roadmap version is:

```text
face_api Roadmap v1.0
```

Use this file as the execution order and scope reference for future `/goal` runs.

## 2. Product Direction

The project direction is to build a small, stable, deliverable, and maintainable local Windows workstation face recognition REST API.

The service is a reusable recognition capability base for business systems. It is not a full user account, permission, token, session, or platform-management system.

Current strategic target:

1. Make the service stable for Windows workstation operation.
2. Make runtime configuration visible and safe.
3. Make failures diagnosable through logs, audit, and documentation.
4. Make the service safe enough for production-like local use.
5. Make delivery, backup, recovery, and handoff repeatable.
6. Improve face database governance after operational foundations are in place.
7. Improve search performance only after measurement proves the need.

## 3. Execution Order

Execute phases in this order:

| Order | Spec | Phase | Reason |
|---:|---|---|---|
| 1 | `specs/002-production-hardening` | Production Hardening | Stabilize service runtime before deeper changes |
| 2 | `specs/003-runtime-config-startup` | Runtime Config and Startup Validation | Prevent hidden or unsafe configuration |
| 3 | `specs/004-logging-audit-diagnostics` | Logging, Audit, and Diagnostics | Make failures and performance visible |
| 4 | `specs/007-security-hardening` | Security Hardening | Reduce exposure before broader delivery |
| 5 | `specs/008-delivery-deployment` | Delivery and Deployment Standardization | Make handoff, backup, and recovery repeatable |
| 6 | `specs/005-face-database-governance` | Face Database Governance | Improve registration quality and record policy |
| 7 | `specs/006-search-performance` | Search Performance Improvement | Optimize only after measurement and operational basics |

Do not execute `005` or `006` before the operational and safety phases unless the user explicitly changes this roadmap version.

## 4. Standard Workflow Per Phase

Each phase MUST follow this sequence:

```text
spec -> clarify -> plan -> tasks -> implement -> verify -> document
```

For each phase:

1. Start from the phase `spec.md`.
2. Run a clarification pass for unresolved decisions.
3. Write an implementation plan.
4. Break the plan into actionable tasks.
5. Implement only that phase.
6. Run tests or explicit verification commands.
7. Update relevant docs.
8. Commit phase work separately from other phases.

Future `/goal` runs should execute one phase at a time.

## 5. Phase Details

### 5.1 Phase 002 - Production Hardening

Spec:

- `specs/002-production-hardening/spec.md`

Goal:

- Make the service suitable for stable production-like Windows workstation operation.

Main outcomes:

- Production startup path without development reload behavior.
- Startup context visible to operators.
- Start/stop/restart/health runbook.
- Clear startup failure messages.

Confirmation points before implementation:

1. Should production startup be a new `run-prod.bat` first, or immediately documented as a Windows service?
2. Should the service fail startup when production-like mode has no API key?
3. Where should production logs be written by default?

Definition of done:

- Operator can start and verify service with production instructions.
- Development reload is clearly excluded from production-like operation.
- Startup context includes device, model, database, auth state, and image limits.

### 5.2 Phase 003 - Runtime Config and Startup Validation

Spec:

- `specs/003-runtime-config-startup/spec.md`

Goal:

- Make effective runtime configuration clear, validated, and beginner-readable.

Main outcomes:

- Unified environment variable documentation.
- Startup validation for invalid numeric values.
- Database path writability validation.
- Clear CPU/GPU selection rules.
- Better protected effective configuration output.

Confirmation points before implementation:

1. Should missing `FACE_API_KEY` block startup in production-like mode or only warn?
2. What should count as production-like mode?
3. Which config values should be fatal versus warning-only?

Definition of done:

- Invalid key configuration errors are caught before business requests.
- Effective config output is sufficient for operator diagnosis.
- CPU/GPU behavior is documented and tested.

### 5.3 Phase 004 - Logging, Audit, and Diagnostics

Spec:

- `specs/004-logging-audit-diagnostics/spec.md`

Goal:

- Make service behavior observable enough for support, operations, and performance diagnosis.

Main outcomes:

- Structured log format.
- Request duration and route logging.
- Error code logging.
- Login audit completeness.
- No embeddings or API keys in logs.

Confirmation points before implementation:

1. Should logs be JSON lines or readable text format?
2. What is the default log directory?
3. Should log rotation be included now or deferred?
4. Should audit filtering by terminal ID and success state be included in this phase?

Definition of done:

- Failed requests can be diagnosed by route, error code, and duration.
- Login-helper outcomes are audit-recorded.
- Sensitive data is excluded from logs and audit output.

### 5.4 Phase 007 - Security Hardening

Spec:

- `specs/007-security-hardening/spec.md`

Goal:

- Reduce accidental exposure and misuse in production-like local use.

Main outcomes:

- Public/protected endpoint policy.
- Configurable CORS behavior.
- Production CORS guidance.
- Sensitive data rules.
- Basic abuse-control strategy.

Confirmation points before implementation:

1. What production frontend origins should be allowed?
2. Should CORS default stay open in development but require explicit setting in production-like mode?
3. Should basic request throttling be implemented now or only specified?
4. Should `/detect` remain optionally protected or become explicitly protected in production-like mode?

Definition of done:

- Protected route policy is testable.
- CORS can be configured without editing business logic.
- Sensitive endpoints remain protected.
- Embeddings and API keys are not exposed.

### 5.5 Phase 008 - Delivery and Deployment Standardization

Spec:

- `specs/008-delivery-deployment/spec.md`

Goal:

- Make setup, deployment, verification, backup, recovery, and handoff repeatable.

Main outcomes:

- Delivery checklist.
- Workstation setup guide.
- Health/config/auth verification checklist.
- Backup and recovery guide.
- Troubleshooting guide.

Confirmation points before implementation:

1. Should backup be documentation-only first or include a script?
2. Should recovery be manual steps only or include a restore script?
3. Should Windows service setup be documented with NSSM, Task Scheduler, or both?

Definition of done:

- New maintainer can locate setup/run/troubleshooting docs quickly.
- Delivery engineer can complete handoff checklist.
- Backup/recovery files and validation steps are clearly documented.

### 5.6 Phase 005 - Face Database Governance

Spec:

- `specs/005-face-database-governance/spec.md`

Goal:

- Improve registration quality and face record policy after operational foundations are in place.

Main outcomes:

- Duplicate registration policy.
- Multi-face-per-user policy.
- Basic registration quality checks.
- Safe lookup by business identity.
- Clear quality failure errors.

Confirmation points before implementation:

1. Can one `user_id` have multiple face records?
2. If the same user registers again, should the service reject, replace, or allow another record?
3. Which quality checks are mandatory for the first version?
4. Should update-by-user-id be added or should users delete then register?

Definition of done:

- Duplicate behavior is explicit and tested.
- Registration rejects unsuitable images with clear reasons.
- Face record management does not expose embeddings.

### 5.7 Phase 006 - Search Performance Improvement

Spec:

- `specs/006-search-performance/spec.md`

Goal:

- Improve search and login-helper performance only after measurements justify the work.

Main outcomes:

- Performance baseline.
- Target database sizes.
- Search latency targets.
- Possible in-memory embedding cache.
- Cache freshness visibility if implemented.

Confirmation points before implementation:

1. What face database sizes should be benchmarked?
2. What search/login latency is acceptable?
3. What record count should trigger memory-cache work?
4. Should Faiss remain explicitly deferred for Roadmap v1.0?

Definition of done:

- Search performance is measured before optimization.
- Any introduced cache remains consistent after registration and deletion.
- Operators can inspect cache readiness if cache exists.

## 6. Explicitly Deferred From Roadmap v1.0

The following are not part of Roadmap v1.0 implementation unless the user explicitly changes the roadmap:

- Liveness detection.
- Faiss vector index.
- Full web management dashboard.
- Multi-terminal synchronization.
- Full user account management.
- Token or session issuing.
- RBAC or business permission decisions.
- Centralized multi-tenant platform.

## 7. Version Control Guidance

When implementing this roadmap:

- Keep one phase per implementation branch or commit series.
- Do not mix phases in a single implementation goal.
- Keep spec, plan, tasks, code, tests, and docs aligned per phase.
- Commit roadmap/spec updates separately from business code when possible.
- Preserve unrelated user changes in the working tree.

## 8. Current Starting Point

Current baseline artifacts:

- Product PRD: `docs/02_product/01_prd.md`
- Product baseline spec: `specs/001-face-api-product/spec.md`
- Roadmap index: `specs/README.md`
- This roadmap version: `specs/ROADMAP-v1.0.md`

The next recommended `/goal` is:

```text
Implement Roadmap v1.0 Phase 002 - Production Hardening
```

