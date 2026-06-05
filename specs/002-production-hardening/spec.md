# Feature Specification: Production Hardening

**Feature Branch**: `002-production-hardening`

**Created**: 2026-06-05

**Status**: Draft

**Input**: User description: "Make the local Windows face recognition service suitable for production-like workstation operation."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator Starts a Stable Production Service (Priority: P1)

An operator needs a production startup path that runs the service predictably without development reload behavior.

**Why this priority**: A service that depends on manual development startup is fragile in real workstation use.

**Independent Test**: The operator can follow documented production startup instructions and confirm the service is healthy without using a development reload mode.

**Acceptance Scenarios**:

1. **Given** the workstation is configured, **When** the operator starts the production command, **Then** the service starts on the configured host and port without development reload behavior.
2. **Given** the service starts successfully, **When** the operator checks health and effective configuration, **Then** both confirm a usable runtime state.

---

### User Story 2 - Operator Sees Startup Context (Priority: P1)

An operator needs startup output that explains the effective runtime configuration and device selection.

**Why this priority**: Startup problems are common in model services; operators need clear runtime facts before debugging.

**Independent Test**: Startup output or logs expose enough context to identify model, database path, CPU/GPU selection, authentication mode, and image limits.

**Acceptance Scenarios**:

1. **Given** the service is started, **When** startup completes, **Then** effective runtime configuration is visible in logs or status output.
2. **Given** a startup failure, **When** the operator reads the error, **Then** the failure explains the configuration area most likely involved.

---

### User Story 3 - Delivery Engineer Has a Safe Runbook (Priority: P2)

A delivery engineer needs a runbook that explains start, stop, restart, and basic verification steps.

**Why this priority**: The service may be handed to non-author operators who need repeatable instructions.

**Independent Test**: A delivery engineer can start, stop, restart, and validate the service using only documented steps.

**Acceptance Scenarios**:

1. **Given** a fresh workstation handoff, **When** the engineer follows the runbook, **Then** they can bring the service to a verified healthy state.

### Edge Cases

- Port is already occupied.
- API key is missing in a production-like environment.
- Database path is missing or not writable.
- GPU is requested but unavailable.
- Model initialization fails.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service MUST provide a documented production startup path that does not use development reload behavior.
- **FR-002**: The service MUST expose startup or status information for runtime device, model, detection size, authentication state, database path, and image limits.
- **FR-003**: The production startup path MUST preserve the CPU-first default and explicit GPU opt-in behavior.
- **FR-004**: Production run documentation MUST include start, stop, restart, and health verification steps.
- **FR-005**: Startup failures MUST provide actionable messages for common configuration and model initialization problems.
- **FR-006**: The production runbook MUST identify what not to do in production-like operation, including long-term use of development reload mode.

### Key Entities *(include if feature involves data)*

- **Production Startup Mode**: The documented way to run the service for stable workstation use.
- **Startup Context**: The visible runtime facts needed to diagnose whether the service is configured correctly.
- **Runbook**: The operator-facing instructions for normal service lifecycle actions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A delivery engineer can start and verify the service using documented production steps in under 10 minutes.
- **SC-002**: The production startup path avoids development reload behavior.
- **SC-003**: Startup context includes the runtime facts needed to identify CPU/GPU mode, auth mode, model, database, and image-limit configuration.
- **SC-004**: Common startup failure causes are mapped to clear operator actions.

## Assumptions

- The primary deployment target remains a single Windows workstation.
- A full Windows service wrapper may be documented before it is automated.
- Production-like operation still runs the same FastAPI application and local SQLite database.
