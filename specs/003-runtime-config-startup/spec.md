# Feature Specification: Runtime Configuration and Startup Validation

**Feature Branch**: `003-runtime-config-startup`

**Created**: 2026-06-05

**Status**: Draft

**Input**: User description: "Make runtime configuration clear, validated, and easier for beginners to understand."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator Understands Effective Configuration (Priority: P1)

An operator needs to see exactly which configuration values are active at runtime.

**Why this priority**: Hidden or mistaken configuration causes confusing behavior such as wrong database, missing auth, or unexpected CPU/GPU mode.

**Independent Test**: The operator can inspect effective configuration and compare it with intended deployment settings.

**Acceptance Scenarios**:

1. **Given** the service is running, **When** the operator requests effective configuration, **Then** the service returns the active operational settings.
2. **Given** CPU/GPU settings are changed, **When** the operator checks effective configuration, **Then** the selected flags reflect the changed behavior.

---

### User Story 2 - Invalid Configuration Fails Early (Priority: P1)

An operator needs invalid or dangerous configuration to be detected at startup rather than during user requests.

**Why this priority**: Late failures are harder to diagnose and may break real business flows.

**Independent Test**: Invalid configuration values produce clear startup validation failures.

**Acceptance Scenarios**:

1. **Given** an invalid numeric image limit, **When** the service starts, **Then** startup validation reports the invalid setting.
2. **Given** a database path that cannot be written, **When** the service starts, **Then** startup validation reports the database path problem.

---

### User Story 3 - Beginner Can Choose CPU or GPU (Priority: P2)

A beginner operator needs simple instructions for default CPU mode, GPU opt-in, and force-CPU override.

**Why this priority**: Device selection is easy to misunderstand on Windows machines.

**Independent Test**: The operator can choose default CPU, explicit GPU, or forced CPU by following documented environment settings.

**Acceptance Scenarios**:

1. **Given** no device override is configured, **When** the service starts, **Then** CPU inference is selected.
2. **Given** GPU opt-in is configured, **When** the service starts on a compatible workstation, **Then** the runtime status shows whether GPU inference is selected.

### Edge Cases

- Numeric configuration values are empty, non-numeric, negative, or too large.
- Both GPU opt-in and force-CPU are set.
- API key is empty in a production-like mode.
- Database directory exists but is not writable.
- Configuration values differ between startup script and terminal session.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service MUST define all operator-facing environment variables in one authoritative documentation section.
- **FR-002**: The service MUST expose effective runtime configuration through a protected status/configuration capability.
- **FR-003**: Startup validation MUST reject invalid numeric configuration values.
- **FR-004**: Startup validation MUST detect database path writability before business requests are handled.
- **FR-005**: Device-selection rules MUST be documented and testable: default CPU, GPU opt-in, force-CPU override.
- **FR-006**: Production-like configuration guidance MUST state whether missing API key is allowed, warned, or rejected.
- **FR-007**: Validation failures MUST include the variable name and a Chinese operator-readable explanation.

### Key Entities *(include if feature involves data)*

- **Runtime Setting**: A configurable value that affects service behavior.
- **Effective Configuration**: The resolved value after defaults and environment variables are applied.
- **Validation Failure**: A startup problem that blocks or warns about unsafe runtime behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can identify all supported environment variables and defaults from documentation in under 5 minutes.
- **SC-002**: Invalid numeric settings are detected before the service accepts business requests.
- **SC-003**: Effective configuration output includes all settings needed to diagnose auth, device, database, model, and image-limit behavior.
- **SC-004**: CPU/GPU selection behavior is covered by tests and documentation.

## Assumptions

- The service remains environment-variable driven.
- Some production strictness decisions, such as whether empty API key blocks startup, may require explicit business confirmation.
- Configuration validation should stay simple and local to the service.
