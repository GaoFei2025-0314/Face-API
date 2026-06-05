# Feature Specification: face_api Product Baseline

**Feature Branch**: `001-face-api-product`

**Created**: 2026-06-05

**Status**: Draft

**Input**: User description: "Use GitHub Spec Kit to make the overall PRD clear enough to guide development for the local Windows workstation face recognition REST API."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Business System Uses Face Recognition Evidence (Priority: P1)

A business system needs a reusable local recognition service that can identify whether an image contains one usable face, extract recognition evidence, compare identities, search registered people, and return a stable helper result for login-like flows.

**Why this priority**: This is the core product value. Without stable recognition evidence, downstream systems cannot safely integrate face registration, search, or login assistance.

**Independent Test**: A business integrator can call the service with representative valid and invalid face images and receive predictable success or structured failure results without reading internal code.

**Acceptance Scenarios**:

1. **Given** a valid single-face image and a protected integration context, **When** the caller requests single-face recognition evidence, **Then** the service returns one face result with the evidence required by the caller.
2. **Given** an image with no usable face, **When** the caller requests recognition, registration, search, or login assistance, **Then** the service returns a stable no-face failure with a machine-readable code and Chinese explanation.
3. **Given** an image with multiple faces where single-face behavior is required, **When** the caller requests registration or login assistance, **Then** the service rejects the request with a stable multiple-faces failure.

---

### User Story 2 - Operator Runs and Diagnoses the Workstation Service (Priority: P1)

An operator needs to start the service on a local Windows workstation, confirm whether it is healthy, inspect the active runtime configuration, and understand whether CPU or GPU inference is being used.

**Why this priority**: The service is intended for local workstation delivery. Operators must be able to run and diagnose it before any business integration is reliable.

**Independent Test**: An operator can start the service, inspect health and effective configuration, and determine runtime device selection without changing source code.

**Acceptance Scenarios**:

1. **Given** a workstation with the service installed, **When** the operator starts it without GPU-specific configuration, **Then** the service uses CPU inference by default.
2. **Given** a workstation where GPU inference is intentionally enabled, **When** the operator starts the service with the documented GPU switch, **Then** the runtime status clearly reports whether GPU inference is selected or CPU fallback is active.
3. **Given** a startup failure, **When** the operator reads the failure message, **Then** it includes enough model and runtime context to distinguish configuration, provider, and model-loading problems.

---

### User Story 3 - Frontend Developer Integrates Predictable API Contracts (Priority: P2)

A frontend developer needs stable request and response contracts, Chinese error messages, and clear guidance for handling common recognition failures.

**Why this priority**: Frontend integration quality depends on stable error semantics and predictable payloads, especially for user-facing capture and retry flows.

**Independent Test**: A frontend developer can use the documentation and API schema to implement success, retry, and error display paths without reverse-engineering backend internals.

**Acceptance Scenarios**:

1. **Given** a failed request, **When** the frontend receives an error response, **Then** it can branch on a stable error code and display a short Chinese message or detailed Chinese reason.
2. **Given** a detection-style response, **When** the frontend receives face attributes, **Then** it does not receive sensitive embeddings unless using a trusted evidence-extraction capability.
3. **Given** a changed runtime configuration, **When** the frontend or integrator checks effective configuration, **Then** it can see relevant limits and device-selection flags.

---

### User Story 4 - Delivery Engineer Protects Local Face Data (Priority: P2)

A delivery engineer needs to understand which data is critical, how to back it up, and how to recover enough state after workstation or database problems.

**Why this priority**: Registered face data is a core business asset. Losing it can require re-enrollment and interrupt business operations.

**Independent Test**: A delivery engineer can identify the required database artifacts, follow backup guidance, and validate restored data through documented service behavior.

**Acceptance Scenarios**:

1. **Given** a running deployment, **When** the engineer prepares a backup, **Then** the documentation identifies the required database files and when the service should be stopped.
2. **Given** a restored database, **When** the service starts and health/status are checked, **Then** the registered face count and face list reflect the restored data.

---

### User Story 5 - Maintainer Evolves the Service Safely (Priority: P3)

A maintainer needs clear product boundaries, phased priorities, and acceptance criteria so future changes do not turn the service into an overly broad business platform.

**Why this priority**: The project will continue evolving, but it must remain a reusable capability module rather than absorbing unrelated business responsibilities.

**Independent Test**: A maintainer can compare proposed work against the product specification and decide whether it is in scope, deferred, or out of scope.

**Acceptance Scenarios**:

1. **Given** a proposed feature, **When** it overlaps with user accounts, permissions, token issuing, liveness detection, or large-scale vector infrastructure, **Then** the specification makes clear whether it is out of scope or requires a separate phase decision.
2. **Given** a proposed performance improvement, **When** the maintainer evaluates it, **Then** the specification guides them to measure need and prefer the simplest scalable step first.

### Edge Cases

- Images may be invalid, corrupted, too large, too high resolution, empty, no-face, or multi-face.
- Runtime provider availability may differ from selected runtime device; visible GPU providers do not guarantee GPU inference is selected.
- GPU may be explicitly requested but unavailable; the service must make selected runtime behavior inspectable.
- Sensitive recognition evidence must not appear in ordinary user-facing responses.
- The local database may be empty, missing, locked, corrupted, or restored from backup.
- API authentication may be intentionally disabled for development but must be explicit and inspectable for protected use.
- A caller may submit thresholds that are weaker than the minimum allowed for login-like authentication.
- Registration may be attempted for the same business user more than once; the current product direction treats the exact duplicate policy as a future decision rather than hidden behavior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service MUST provide reusable face recognition capabilities for local business integrations, including detection, single-face evidence extraction, comparison, search, registration, and login assistance.
- **FR-002**: The service MUST remain a recognition capability module and MUST NOT issue business tokens, sessions, user permissions, or final access decisions.
- **FR-003**: The service MUST allow operators to verify health without authentication.
- **FR-004**: The service MUST allow protected callers to inspect runtime status and effective configuration, including model identity, detection size, device selection, authentication state, database location, and image limits.
- **FR-005**: The service MUST use CPU inference by default for workstation stability.
- **FR-006**: The service MUST allow GPU inference only when explicitly enabled by configuration.
- **FR-007**: The service MUST allow an explicit force-CPU setting to override GPU enablement.
- **FR-008**: The service MUST expose enough runtime diagnostics to distinguish CPU/GPU selection, provider availability, and model initialization failures.
- **FR-009**: The service MUST accept image input through documented file-upload and Base64 flows where those flows are part of the public contract.
- **FR-010**: The service MUST reject invalid, oversized, or excessive-resolution images with stable structured errors.
- **FR-011**: The service MUST return detection results without exposing embeddings in ordinary detection, list, search, or login responses.
- **FR-012**: The service MUST provide a trusted single-face evidence capability that returns an embedding only to protected integrations.
- **FR-013**: The service MUST require exactly one face for registration and login assistance.
- **FR-014**: The service MUST provide stable no-face and multiple-faces failures for single-face flows.
- **FR-015**: The service MUST store registered face records with business-facing identity fields, metadata, embeddings, and created-time information.
- **FR-016**: The service MUST allow registered face records to be listed and deleted without exposing embeddings.
- **FR-017**: The service MUST compare two face images and return similarity, threshold, same-person decision, and processing duration.
- **FR-018**: The service MUST search registered faces and return ranked matches with similarity and business identity fields.
- **FR-019**: The service MUST provide login assistance that validates a single face, performs top-match search, applies a minimum authentication threshold, and returns matched business identity when successful.
- **FR-020**: The login assistance capability MUST NOT issue tokens or sessions.
- **FR-021**: The service MUST write audit records for successful and failed login-assistance attempts.
- **FR-022**: The service MUST allow protected callers to view recent login audit records and summary counts.
- **FR-023**: Business-facing errors MUST include a stable code, a short Chinese message, and a longer Chinese reason/remediation.
- **FR-024**: Documentation MUST define setup, integration, architecture, operational boundaries, and backup/recovery expectations.
- **FR-025**: Future work MUST be evaluated against the phased roadmap before implementation.

### Key Entities *(include if feature involves data)*

- **Face Image**: A caller-provided image used for detection, comparison, registration, search, or login assistance. Key attributes include input form, decoded size, pixel count, and recognition suitability.
- **Face Result**: A detected face and its visible attributes, such as bounding box, confidence, landmarks, age, and gender. Embedding is sensitive and only returned through trusted evidence extraction.
- **Face Embedding**: A sensitive numerical representation used for similarity comparison and search. It is stored and processed internally and only exposed through trusted protected flows.
- **Registered Face Record**: A locally stored face entry associated with an internal face ID, optional business user ID, username, metadata, embedding, and creation time.
- **Match Result**: A ranked search or authentication candidate containing business identity fields, metadata, and similarity.
- **Login Audit Record**: A record of a login-assistance attempt containing success state, matched identity when available, similarity, threshold, failure reason, terminal/request tracking fields, duration, and creation time.
- **Runtime Configuration**: The currently active operational settings such as authentication state, model selection, detection size, database path, CPU/GPU flags, and image limits.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new integrator can identify the service purpose, in-scope capabilities, and out-of-scope responsibilities from product documentation in under 15 minutes.
- **SC-002**: Operators can determine whether the service is healthy and whether CPU or GPU inference is selected using documented status/configuration outputs within 2 minutes of startup.
- **SC-003**: 100% of documented business-facing failure scenarios include a stable code, Chinese message, and Chinese reason/remediation.
- **SC-004**: Ordinary detection, list, search, and login responses do not expose face embeddings.
- **SC-005**: Default startup uses CPU inference unless GPU is explicitly enabled.
- **SC-006**: Protected recognition, configuration, and audit capabilities require the documented API-key behavior.
- **SC-007**: Core contract tests cover health/status, effective configuration, image validation, structured errors, CPU/GPU selection, single-face constraints, search, registration, and login audit behavior.
- **SC-008**: The service can complete a representative local business flow of register, search, and login assistance without requiring a separate account or permission platform.
- **SC-009**: Operators can identify the files required for face database backup and the minimum recovery validation steps from documentation.
- **SC-010**: Future development proposals can be categorized as current scope, next-phase scope, optional advanced capability, or out of scope using the roadmap and boundaries in this specification.

## Assumptions

- The primary deployment target is a single local Windows workstation.
- CPU inference is preferred by default for stability and predictable workstation operation.
- GPU inference is an explicit optimization path rather than the default baseline.
- Existing business systems own user accounts, roles, permissions, tokens, sessions, and final access decisions.
- The local face database is the source of truth for registered face embeddings until a measured scale problem justifies a different design.
- Liveness detection is not part of the baseline product and requires separate business approval.
- Large-scale vector search infrastructure is not part of the baseline product and should follow measured need.
- Documentation is part of the product contract, not a secondary deliverable.
- Registration duplicate policy and multi-face-per-user policy remain future decisions until the target business scenario requires them.
