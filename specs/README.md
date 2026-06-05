# Spec Kit Roadmap Index

This directory contains Spec Kit feature specifications derived from the product PRD.

## Current Product Baseline

- `001-face-api-product` - Overall face_api product baseline and scope boundaries
- `ROADMAP-v1.0.md` - Versioned execution order for future `/goal` runs

## Planned Development Phases

Roadmap v1.0 execution order:

1. `002-production-hardening` - Stable production-like workstation operation
2. `003-runtime-config-startup` - Runtime configuration visibility and startup validation
3. `004-logging-audit-diagnostics` - Logs, audit records, and diagnostics
4. `007-security-hardening` - CORS, protected endpoints, sensitive data, and abuse controls
5. `008-delivery-deployment` - Handoff, deployment, backup, recovery, and troubleshooting
6. `005-face-database-governance` - Face database quality and registration governance
7. `006-search-performance` - Measured search and login-assistance performance improvements

## Recommended Flow

For any phase, use:

```text
spec -> clarify -> plan -> tasks -> implement
```

Do not implement directly from this index. Choose one phase, clarify open decisions, then create its implementation plan.
