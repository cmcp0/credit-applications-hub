# Design Document: Applications Services (Customer + Operation)

## Metadata
- **Related PRD**: `docs/prd-credit-applications-hub.md` (Phase 1: Foundation, Phase 2: Multi-country, Phase 3: Async + integration + realtime)
- **Related Architecture**: `docs/architecture-specification.md`
- **Related Auth Design**: `docs/design-auth-context.md`
- **Related Frontend Design**: `docs/design-frontend-auth-routing.md`
- **Messaging Rules**: `docs/messaging-rule.md`
- **Status**: draft
- **Last Updated**: 2026-02-16
- **Author**: Engineering
- **Scope**: `/api/applications` services for `customer` and `operation` roles, status-transition command design, and event publication rules

## Overview
This design defines the backend services under `/api/applications` for MVP role behaviors:
- `customer`: create applications and read their own applications.
- `operation`: list applications and transition customer application status.

The design keeps business logic under `src/applications/` and transport wiring under `apps/backend/`, aligned with DDD + Hexagonal boundaries in current repository docs.

It also standardizes:
- `UpdateApplicationStatus` as the canonical command for status transitions.
- `ApplicationCreated` and `ApplicationStatusUpdated` as integration events emitted through outbox-backed publication.
- PII minimization and sensitive-data non-exposure defaults across API responses, logs, and event payloads.
- Aggregate ownership inside the bounded context:
  - `application` module for the `Application` aggregate root and lifecycle commands/queries.
  - `workflow` module for the `Workflow` aggregate that models status-policy metadata and transition rules.

## Context
- **Problem**:
  - `/api/applications` behavior is currently scaffold-level and does not define stable role contracts, transition rules, or event contracts.
  - Auth design already defines permission semantics, but applications context behavior is deferred.
- **Goals**:
  - Provide implementation-ready contracts for `customer` and `operation` role services.
  - Define lifecycle-safe status transition flow via `UpdateApplicationStatus`.
  - Ensure application create/status-change flows emit consistent integration events.
  - Enforce secure handling of PII and avoid sensitive data leakage.
  - Keep async/event flows idempotent and compatible with parallel worker processing.
- **Out of scope (this slice)**:
  - Admin-only workflow/operation management services.
  - Non-status patch of application business fields by `operation`.
  - Refresh token/session management (covered in auth design).
  - Full provider adapter implementation details per country (covered by separate provider/routing implementation slices).

## Functional Specifications

### Feature 1: Customer Creates Application (`POST /api/applications`)
**User Story**: As a `customer`, I can submit a credit application and receive a trackable application id and initial status.  
**Acceptance Criteria**:
- Authenticated `customer` with `applications:create` can create an application.
- Initial status resolves from active workflow for the selected country.
- On success, API returns safe summary data (no raw sensitive fields).
- Create transaction writes application state and one outbox event atomically.
- `ApplicationCreated` is published from outbox after commit.

**Functional Requirements**:
- FR-1: The system SHALL require `applications:create` for `POST /api/applications`.
- FR-2: The system SHALL enforce country-specific validation rules before persistence.
- FR-3: The system SHALL resolve initial status from country workflow (`Status.is_initial=true`).
- FR-4: The system SHALL persist `Application` and `OutboxEvent(ApplicationCreated)` in the same transaction.
- FR-5: The system SHALL return response data using explicit allowlist fields only.
- FR-6: The system SHALL attach correlation metadata for traceability (`request_id`, `correlation_id`).

### Feature 2: Role-Scoped Read Services (`GET /api/applications`, `GET /api/applications/{application_id}`)
**User Story**: As a `customer`, I can view only my own applications; as an `operation` user, I can view applications for operational processing.  
**Acceptance Criteria**:
- `customer` reads are owner-scoped (`application.user_id == principal.user_id`).
- `operation` reads are global when `applications:list_all` is present.
- List supports at minimum country and status filtering.
- Responses avoid raw PII exposure by default.

**Functional Requirements**:
- FR-7: The system SHALL require `applications:list_own` or `applications:list_all` for list/read services.
- FR-8: The system SHALL enforce owner scope for `customer` on both list and detail routes.
- FR-9: The system SHALL allow global list/detail for `operation` with `applications:list_all`.
- FR-10: The system SHALL support filters for `country` and `status` at minimum.
- FR-11: The system SHALL use stable pagination semantics for list responses.
- FR-12: The system SHALL exclude raw identity documents and other sensitive fields from standard list responses.

### Feature 3: Operation Status Transition (`PATCH /api/applications/{application_id}/status`)
**User Story**: As an `operation` user, I can transition an application status through valid workflow transitions.  
**Acceptance Criteria**:
- Endpoint requires `applications:update_customer`.
- Route delegates to `UpdateApplicationStatus` command handler.
- Invalid transitions are rejected with explicit error code.
- On valid transition, application state changes once and emits one status-updated event.
- Replayed command messages are idempotent and do not apply duplicate transitions.

**Functional Requirements**:
- FR-13: The system SHALL require `applications:update_customer` for status transition endpoint.
- FR-14: The system SHALL represent all status changes through `UpdateApplicationStatus`.
- FR-15: The system SHALL validate transition against country workflow allowed edges.
- FR-16: The system SHALL reject invalid transitions with `409 INVALID_STATUS_TRANSITION`.
- FR-17: The system SHALL persist status change, append one `ApplicationStatusHistory` record, and write `OutboxEvent(ApplicationStatusUpdated)` in the same transaction.
- FR-18: The system SHALL enforce optimistic concurrency/version checks for transition writes.
- FR-19: The system SHALL process duplicate command deliveries idempotently using command id/message id.
- FR-20: The system SHALL validate command caller trust/authorization before transition execution (API path via principal permission checks; async path via trusted producer policy and server-side actor resolution or permission re-check), and record actor metadata (`actor_user_id`, `actor_role`) for auditability.

### Feature 4: Event Publication Contracts
**User Story**: As a downstream consumer (worker/webhook/frontend projection), I receive consistent event contracts when applications are created or status changes.  
**Acceptance Criteria**:
- `ApplicationCreated` and `ApplicationStatusUpdated` contracts are versioned.
- Event payloads contain correlation metadata and no unnecessary PII.
- Events are published to `applications.events` exchange via outbox publisher.

**Functional Requirements**:
- FR-21: The system SHALL publish `ApplicationCreated` after successful create commit.
- FR-22: The system SHALL publish `ApplicationStatusUpdated` after successful status-transition commit.
- FR-23: The system SHALL include `event_id`, `occurred_at`, `correlation_id`, and `schema_version` in event envelopes.
- FR-24: The system SHALL keep event payloads minimal and PII-safe by default.

### Feature 5: Security and Sensitive Data Protection
**User Story**: As a security stakeholder, application services protect PII and avoid accidental data exposure.  
**Acceptance Criteria**:
- API schemas, event payloads, and logs exclude raw sensitive fields by default.
- Sensitive fields are redacted in structured logs.
- Security controls are test-covered and enforced in CI.

**Functional Requirements**:
- FR-25: The system SHALL redact sensitive fields (`identity_document`, `monthly_income`, tokens, authorization headers) in logs.
- FR-26: The system SHALL avoid including raw PII in event payloads unless explicitly required by a consumer contract.
- FR-27: The system SHALL encrypt transport (TLS) and rely on encrypted-at-rest database/storage in runtime environments.
- FR-28: The system SHALL use explicit response schema allowlists and never serialize ORM entities directly to API responses.
- FR-29: The system SHALL avoid raw PII in queue keys, idempotency keys, and observability labels.

## Technical Design

### Architecture and Boundaries
- `src/applications/application/` owns the `Application` aggregate root, create/read/list/status-update use cases, and application-domain events.
- `src/applications/workflow/` owns the `Workflow` aggregate and status-policy metamodel (`Status`, allowed transitions, initial status resolution).
- `apps/backend/` owns FastAPI routes, request/response schemas, dependency wiring, and principal extraction.
- `src/applications/.../infrastructure` owns repositories/adapters for aggregate persistence and outbox integration.
- Ports are defined under each module `domain/ports/` (no separate `application/ports/` folders).
- Workers/webhooks never write `Application` directly; they publish commands/events that backend handlers apply.

### Proposed Source Layout
```text
src/applications/
├── application/
│   ├── domain/
│   │   ├── entities.py
│   │   ├── events.py
│   │   ├── value_objects.py
│   │   └── ports/
│   │       ├── application_repository.py
│   │       ├── application_read_repository.py
│   │       └── outbox_event_writer.py
│   ├── application/
│   │   ├── commands/
│   │   │   ├── create_application.py
│   │   │   └── update_application_status.py
│   │   ├── queries/
│   │   │   ├── get_application.py
│   │   │   └── list_applications.py
│   │   └── services/
│   │       ├── create_application_service.py
│   │       └── update_application_status_service.py
│   └── infrastructure/
│       └── adapters/
│           ├── application_orm_model.py
│           ├── application_status_history_orm_model.py
│           ├── application_repository.py
│           ├── application_read_repository.py
│           └── status_history_repository.py
├── workflow/
│   ├── domain/
│   │   ├── entities.py
│   │   ├── events.py
│   │   ├── value_objects.py
│   │   └── ports/
│   │       └── workflow_repository.py
│   ├── application/
│   │   └── services/
│   │       ├── resolve_initial_status_service.py
│   │       └── validate_status_transition_service.py
│   └── infrastructure/
│       └── adapters/
│           ├── workflow_repository.py
│           └── status_transition_repository.py
└── shared/
    ├── domain/
    │   ├── value_objects.py
    │   └── errors.py
    └── infrastructure/
        └── adapters/
            └── outbox_event_repository.py

apps/backend/
├── api/
│   ├── router.py
│   └── applications/
│       ├── router.py
│       └── schemas.py
└── security/
    └── pii_redaction.py
```

### Status Lifecycle Rules
- Status transitions are country-workflow driven (`workflow.country == application.country`).
- `Workflow` aggregate is the policy source of truth for:
  - initial status resolution
  - valid transition graph
  - terminal-state constraints
- Transition validity comes from `Status -> allowed_transitions` edges.
- Terminal statuses have zero outgoing transitions.
- Transition command (`UpdateApplicationStatus`) mutates only the `Application` aggregate after workflow-policy validation.
- Transition write path is single-writer through backend application services.
- Each transition increments aggregate version for race-safe updates.

### Status History Model
Append-only persistence model for transition audit and traceability:

`application_status_history` table:
- `id UUID PRIMARY KEY`
- `application_id UUID NOT NULL REFERENCES application(id)`
- `from_status_code TEXT NOT NULL`
- `to_status_code TEXT NOT NULL`
- `application_version INT NOT NULL`
- `reason_code TEXT NULL`
- `actor_user_id UUID NULL` (nullable for trusted system-triggered transitions)
- `actor_role TEXT NULL`
- `command_id UUID NULL`
- `correlation_id UUID NOT NULL`
- `changed_at TIMESTAMPTZ NOT NULL`

Constraints/indexes:
- Unique index on (`application_id`, `application_version`)
- Optional unique index on `command_id` when non-null (idempotency safety)
- Index on (`application_id`, `changed_at DESC`) for history reads

### Command Contract: `UpdateApplicationStatus`
Command object (application-layer canonical command):
```json
{
  "command_id": "uuid",
  "application_id": "uuid",
  "target_status_code": "APPROVED",
  "actor_user_id": "uuid",
  "actor_role": "operation",
  "reason_code": "MANUAL_REVIEW_COMPLETED",
  "expected_version": 7,
  "correlation_id": "uuid",
  "requested_at": "2026-02-16T12:00:00Z"
}
```

Rules:
- API handler maps HTTP payload to `UpdateApplicationStatus`.
- Async consumers (workers/webhooks) map normalized messages to the same command.
- `command_id` (or broker `message_id`) is used for idempotency guard.
- Transition handler re-validates caller trust/authorization before applying state changes.
- If status already equals `target_status_code`, handler returns idempotent success without duplicate event.

### Event Contracts

#### `ApplicationCreated` (integration event, `v1`)
```json
{
  "event_name": "ApplicationCreated",
  "schema_version": "v1",
  "event_id": "uuid",
  "occurred_at": "2026-02-16T12:00:00Z",
  "correlation_id": "uuid",
  "payload": {
    "application_id": "uuid",
    "owner_id": "uuid",
    "country": "MX",
    "status_code": "PENDING_REVIEW",
    "application_date": "2026-02-16",
    "version": 1
  }
}
```

#### `ApplicationStatusUpdated` (integration event, `v1`)
```json
{
  "event_name": "ApplicationStatusUpdated",
  "schema_version": "v1",
  "event_id": "uuid",
  "occurred_at": "2026-02-16T12:05:00Z",
  "correlation_id": "uuid",
  "payload": {
    "application_id": "uuid",
    "country": "MX",
    "previous_status_code": "PENDING_REVIEW",
    "current_status_code": "APPROVED",
    "actor_user_id": "uuid",
    "actor_role": "operation",
    "version": 2
  }
}
```

PII policy for events:
- Do not include `identity_document`, `monthly_income`, provider payload snapshots, or raw names in these integration events.
- Include only minimum fields required for orchestration and projections.

### API Contracts

#### `POST /api/applications`
Request:
```json
{
  "country": "MX",
  "full_name": "Jane Doe",
  "identity_document": "ABC123456",
  "requested_amount": 5000,
  "monthly_income": 2500
}
```

Success response (`201`):
```json
{
  "id": "uuid",
  "country": "MX",
  "status_code": "PENDING_REVIEW",
  "created_at": "2026-02-16T12:00:00Z"
}
```

Errors:
- `400 VALIDATION_ERROR` (includes structured field errors)
- `401 TOKEN_INVALID|TOKEN_EXPIRED|AUTH_HEADER_MISSING`
- `403 PERMISSION_DENIED`

Validation error response shape (`400`):
```json
{
  "code": "VALIDATION_ERROR",
  "message": "Validation failed",
  "errors": [
    {
      "field": "identity_document",
      "code": "INVALID_FORMAT",
      "message": "Identity document format is invalid for selected country"
    }
  ]
}
```

#### `GET /api/applications`
Query params:
- `country` (optional)
- `status` (optional)
- `page` / `page_size` (optional)

Success response (`200`):
```json
{
  "items": [
    {
      "id": "uuid",
      "country": "MX",
      "status_code": "PENDING_REVIEW",
      "requested_amount": 5000,
      "created_at": "2026-02-16T12:00:00Z",
      "updated_at": "2026-02-16T12:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

#### `GET /api/applications/{application_id}`
Success response (`200`): same safe-summary fields as list plus workflow-related status metadata.  
Ownership/permission enforcement:
- `customer`: must own the application.
- `operation`: requires `applications:list_all`.
- `operation` response remains summary-only in MVP (no additional sensitive applicant fields).

#### `PATCH /api/applications/{application_id}/status`
Request:
```json
{
  "status": "APPROVED",
  "reason_code": "MANUAL_REVIEW_COMPLETED",
  "expected_version": 7
}
```

Success response (`200`):
```json
{
  "id": "uuid",
  "previous_status_code": "PENDING_REVIEW",
  "status_code": "APPROVED",
  "updated_at": "2026-02-16T12:05:00Z",
  "version": 8
}
```

Errors:
- `403 PERMISSION_DENIED`
- `404 APPLICATION_NOT_FOUND`
- `409 INVALID_STATUS_TRANSITION`
- `409 VERSION_CONFLICT`

### Messaging Topology
- **Event exchange**: `applications.events`
- **Command exchange**: `applications.commands`
- **Routing keys**:
  - `credit.application.created` -> `ApplicationCreated`
  - `credit.application.status.updated` -> `ApplicationStatusUpdated`
  - `credit.application.status.update` -> `UpdateApplicationStatus`

Suggested queue bindings aligned with current architecture doc:
- `workers.application_created.q` binds `credit.application.created`
- `workers.status_changed.q` binds `credit.application.status.updated`
- `backend.applications.update_status.q` binds `credit.application.status.update`

Command/event consumption policy:
- `credit.application.status.update` is consumed by backend application handlers only (single-writer rule for `Application` state).
- Workflow workers may subscribe to application events (`ApplicationCreated`, `ApplicationStatusUpdated`, and future event types) for async side effects.

Per-queue policy expectations:
- retry + DLQ configured per queue
- consumer idempotency via message/command id tracking
- queue-specific prefetch and concurrency settings

### Security Controls (PII and Sensitive Data)
Data minimization:
- Persist required identity/financial fields, but do not expose raw values in standard summary responses.
- Event payloads are PII-minimal by contract.

Output and serialization:
- Use explicit response schemas.
- Never serialize ORM objects directly to HTTP responses.
- Never return secrets, token internals, or authorization headers.

Logging and observability:
- Reuse centralized redaction filter (`apps/backend/security/pii_redaction.py`).
- Redact or hash sensitive values before logs/metrics/traces.
- Keep correlation IDs and non-sensitive identifiers for traceability.

Storage and transport:
- TLS for all service-to-service and client-to-service transport.
- Encryption at rest for PostgreSQL and broker persistence where supported.
- Secrets sourced from environment/secret manager only.

## Implementation Tracking

### Requirement Traceability
| Requirement | Owner Layer | Concrete Artifact(s) | Test Coverage |
|---|---|---|---|
| FR-1..FR-6 create behavior + created event | `src/applications/application` + `src/applications/workflow` + backend transport | `src/applications/application/application/services/create_application_service.py`, `src/applications/workflow/application/services/resolve_initial_status_service.py`, `apps/backend/api/applications/router.py` | unit + integration |
| FR-7..FR-12 role-scoped list/detail | `src/applications/application` + auth dependencies | `src/applications/application/application/queries/list_applications.py`, `src/applications/application/application/queries/get_application.py`, `apps/backend/auth/dependencies.py` | unit + integration |
| FR-13..FR-20 status command + transition policy | `src/applications/application` + `src/applications/workflow` + backend API | `src/applications/application/application/commands/update_application_status.py`, `src/applications/application/application/services/update_application_status_service.py`, `src/applications/workflow/application/services/validate_status_transition_service.py`, `apps/backend/api/applications/router.py` | unit + integration |
| FR-21..FR-24 event contracts/outbox publish | applications shared infra + publisher | `src/applications/shared/infrastructure/adapters/outbox_event_repository.py`, publisher worker/process | integration + contract |
| FR-25..FR-29 PII/sensitive-data protection | backend security + schemas + messaging adapters | `apps/backend/security/pii_redaction.py`, API schemas, event mappers | security + integration |

### Task Checklist (living tracker)
| ID | Task | Path(s) | Status | Notes |
|---|---|---|---|---|
| AP1 | Create applications bounded-context module structure | `src/applications/**` | TODO | Keep strict domain/application/infrastructure boundaries |
| AP2 | Implement `Application` aggregate module (commands/queries/services) | `src/applications/application/**` | TODO | Aggregate owns create/read/list/status-change invariants |
| AP3 | Implement `Workflow` aggregate module as policy meta-model | `src/applications/workflow/**` | TODO | Own initial-status and transition-policy resolution |
| AP4 | Implement `UpdateApplicationStatus` command and handler | `src/applications/application/application/**` | TODO | Command is canonical status transition path |
| AP5 | Implement workflow transition validation service | `src/applications/workflow/application/services/validate_status_transition_service.py` | TODO | Return explicit transition errors |
| AP6 | Add outbox event writes for create/status update | `src/applications/shared/infrastructure/adapters/outbox_event_repository.py` | TODO | Must be in same DB transaction |
| AP7 | Implement event publisher bindings and message envelopes | publisher process + infra adapters | TODO | Use schema_version + correlation metadata |
| AP8 | Add FastAPI application routes and schemas | `apps/backend/api/applications/**` | TODO | Keep transport logic out of `src/applications` |
| AP9 | Enforce response allowlists and redaction for PII | `apps/backend/api/applications/schemas.py`, `apps/backend/security/pii_redaction.py` | TODO | Ensure no raw sensitive fields in standard responses |
| AP10 | Add role-based integration tests (`customer`, `operation`) | `tests/applications/integration/**` | TODO | Include ownership and permission matrix checks |
| AP11 | Add event contract + outbox tests | `tests/applications/integration/events/**` | TODO | Verify exactly-once publish semantics via outbox/idempotency |
| AP12 | Add status-transition concurrency/idempotency tests | `tests/applications/integration/workflow/**` | TODO | Cover duplicate command and version conflicts |
| AP13 | Add async command trust/authorization tests | `tests/applications/integration/security/**` | TODO | Reject untrusted producers or unauthorized actor mappings |
| AP14 | Add status-history model + repository + migration | `src/applications/application/infrastructure/adapters/application_status_history_orm_model.py`, migrations | TODO | Append-only history written in same transaction as status updates |

## Testing Strategy
- Unit:
  - Create service validations and initial status resolution.
  - Transition policy validity (`allowed_transitions`, terminal behavior).
  - `UpdateApplicationStatus` command handler idempotency and version checks.
- Integration:
  - `customer` can create and read only owned applications.
  - `operation` can list global applications and execute status transitions.
  - `customer` cannot call status transition endpoint.
  - Outbox row creation for both `ApplicationCreated` and `ApplicationStatusUpdated`.
  - Status transition writes append one history row with actor/correlation metadata.
  - Async `UpdateApplicationStatus` messages from untrusted producers are rejected (or routed to DLQ) and do not mutate state.
- Contract:
  - Event schema snapshots for `ApplicationCreated` and `ApplicationStatusUpdated` (`v1`).
  - Routing key/exchange binding tests for consumer expectations.
- Security:
  - Response payloads exclude raw `identity_document` and other sensitive fields.
  - Log redaction covers request payloads, headers, and error logs.
  - Event payload assertions verify PII minimization.

## Implementation Gaps and Mitigations
**Status (2026-02-17): all tracked implementation gaps in this section are closed.**

| Gap/Risk | Status | Mitigation |
|---|---|---|
| Async command caller trust/authorization parity with API path | CLOSED | Trusted producer check + server-side actor authorization/role resolution before applying status updates |
| Queue retry policy for transient failures | CLOSED | Added bounded retry flow (`x-retry-count`) with retry queue + TTL + DLQ fallback |
| Log redaction coverage for handlers added after app boot | CLOSED | Added logger handler hook in redaction installer so newly attached handlers receive PII redaction filter |
| Missing messaging-topology contract tests and async actor auth tests | CLOSED | Added tests for RabbitMQ bindings/retry policy and async unauthorized actor rejection |

## Design Decisions

### Decision 1: `UpdateApplicationStatus` is the single status-write path
- **Context**: Status changes can be triggered by API and async flows.
- **Chosen Solution**: Route all status transitions through one command contract and handler.
- **Trade-off**: More explicit command plumbing, but consistent validation/audit/idempotency.

### Decision 2: Outbox-backed event publication for create/status changes
- **Context**: Events must be reliable and aligned with committed state.
- **Chosen Solution**: Persist outbox records in same transaction as aggregate changes.
- **Trade-off**: Requires publisher process and operational monitoring, but prevents lost events.

### Decision 3: Role scopes are permission-driven with owner filtering for customers
- **Context**: Auth design establishes permission model and ownership constraints.
- **Chosen Solution**: Enforce `applications:list_own` owner scope and `applications:list_all` global scope.
- **Trade-off**: Additional query-layer branching, but clear least-privilege behavior.

### Decision 4: PII-minimal read and event contracts by default
- **Context**: Sensitive data handling is a hard requirement.
- **Chosen Solution**: Keep default responses/events to safe summary fields and masked/redacted outputs.
- **Trade-off**: Some operational use cases may need separate privileged endpoints later.

### Decision 5: Keep transport/framework concerns outside `src/applications`
- **Context**: Repository architecture mandates DDD + Hexagonal boundaries.
- **Chosen Solution**: Domain/application/infrastructure in `src/applications`, FastAPI schemas/routes in `apps/backend`.
- **Trade-off**: More files and composition wiring, but cleaner modularity and testability.

## Open Questions
- Resolved: `GET /api/applications/{application_id}` stays summary-only for `operation` in MVP.
- Resolved: add `ApplicationStatusHistory` persistence model now; keep history internal/audit-oriented in MVP (no explicit public history endpoint yet).
- Resolved: `credit.application.status.update` is consumed by backend only; workflow workers subscribe to events for side effects.

## Definition of Done
- `customer` can create applications and read only owned applications.
- `operation` can list applications and transition customer status through `UpdateApplicationStatus`.
- Invalid status transitions are rejected with explicit `409` errors.
- Create/status writes each emit exactly one outbox-backed integration event.
- `ApplicationCreated` and `ApplicationStatusUpdated` contracts are versioned and documented.
- Standard responses/events/logs do not expose raw sensitive fields.
- Unit/integration/security tests for role scope, transitions, events, and PII controls are green.
- Implementation aligns with:
  - `docs/architecture-specification.md`
  - `docs/design-auth-context.md`
  - `docs/design-frontend-auth-routing.md`
  - `docs/messaging-rule.md`

## References
- `docs/prd-credit-applications-hub.md`
- `docs/architecture-specification.md`
- `docs/design-auth-context.md`
- `docs/design-frontend-auth-routing.md`
- `docs/bounded-context-structure.md`
- `docs/messaging-rule.md`
- `AGENTS.md`
