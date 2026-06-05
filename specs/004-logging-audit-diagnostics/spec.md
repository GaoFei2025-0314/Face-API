# Feature Specification: Logging, Audit, and Diagnostics

**Feature Branch**: `004-logging-audit-diagnostics`

**Created**: 2026-06-05

**Status**: Draft

**Input**: User description: "Make service behavior observable so failures can be diagnosed by logs and audit records."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator Diagnoses API Failures (Priority: P1)

An operator needs logs that show what failed, where it failed, and which request context was involved.

**Why this priority**: Without logs, failed recognition, login, or startup events can only be guessed.

**Independent Test**: A failed request produces an operator-readable log record with route, duration, error code, and relevant context.

**Acceptance Scenarios**:

1. **Given** a request fails due to no face, **When** the operator reads logs, **Then** the route, error code, and duration are visible.
2. **Given** a login-assistance failure, **When** the operator reads logs or audit records, **Then** the failure reason and threshold context are available.

---

### User Story 2 - Business Reviews Login Attempts (Priority: P1)

A business operator needs audit records for recent face-login helper attempts.

**Why this priority**: Login-like flows need traceability for support and risk review.

**Independent Test**: Successful and failed login-assistance attempts appear in recent audit and summary views.

**Acceptance Scenarios**:

1. **Given** a successful login-assistance attempt, **When** audit records are queried, **Then** matched identity, similarity, threshold, and duration are available.
2. **Given** a failed login-assistance attempt, **When** audit records are queried, **Then** failure reason and request tracking fields are available.

---

### User Story 3 - Maintainer Finds Slow Paths (Priority: P2)

A maintainer needs timing information to understand slow recognition, search, or login flows.

**Why this priority**: Performance work should be based on measured bottlenecks.

**Independent Test**: Compute-heavy operations expose duration data in responses and logs.

**Acceptance Scenarios**:

1. **Given** a search request, **When** the operation completes, **Then** duration is available for later performance review.

### Edge Cases

- Logging must not expose face embeddings.
- Logging must not expose API keys.
- Audit records may grow over time.
- A request may fail before face analysis begins.
- A request may fail after matching but before final response.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service MUST define a structured log format for startup, request, error, and key business events.
- **FR-002**: Request logs MUST include route, status outcome, duration, and error code when applicable.
- **FR-003**: Login-assistance audit records MUST include success state, matched identity when available, similarity, threshold, failure reason, tracking fields, duration, and timestamp.
- **FR-004**: Logs and audit outputs MUST NOT expose embeddings or API keys.
- **FR-005**: Audit query capabilities MUST support recent-record and summary-review use cases.
- **FR-006**: Diagnostics documentation MUST explain how to interpret common log and audit fields.
- **FR-007**: Slow operation analysis MUST rely on recorded durations rather than guesses.

### Key Entities *(include if feature involves data)*

- **Log Event**: A structured service event used for diagnostics.
- **Request Context**: Route, status, timing, error, and optional tracking information for one API request.
- **Audit Record**: A durable record of a login-assistance attempt.
- **Diagnostic Field**: A documented field used by operators to understand service behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operators can identify the error code and route for a failed request from logs in under 2 minutes.
- **SC-002**: 100% of login-assistance outcomes write an audit record.
- **SC-003**: Logs and audits contain no face embeddings or API keys.
- **SC-004**: Compute-heavy flows expose duration information for performance review.

## Assumptions

- Login audit remains stored locally with the service database unless a future phase introduces centralization.
- File-based logs are sufficient for workstation operation.
- Log retention policy may be added after real deployment needs are known.
