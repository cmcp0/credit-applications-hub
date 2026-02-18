# Design Document: Workflow Administration Services (Admin + Webhooks + Async Execution)

## Metadata
- **Related PRD**: `docs/prd-credit-applications-hub.md` (Phase 3: Async + integration + realtime, Phase 4: Hardening)
- **Related Architecture**: `docs/architecture-specification.md`
- **Related Auth Design**: `docs/design-auth-context.md`
- **Related Applications Design**: `docs/design-applications-services.md`
- **Messaging Rules**: `docs/messaging-rule.md`
- **Status**: draft
- **Last Updated**: 2026-02-17
- **Author**: Engineering
- **Scope**: Admin-managed workflow services, operation-user administration, webhook administration, and async workflow execution specifications

## Overview
This design defines the backend services and domain models required for `admin` workflow governance. It formalizes:
- Admin services under `/api/users/operations/*` and `/api/workflows/*`.
- Workflow authoring and publication rules (statuses, transitions, operations, sub-operations, triggers).
- Webhook endpoint/event/delivery models tied to workflows.
- Async execution models and processing rules for workflow runtime.

The document is implementation-tracking by design and extends currently stubbed endpoints into implementation-ready contracts.

## Context
- **Problem**:
  - Current admin endpoints (`GET /api/users/operations`, `GET /api/workflows`) are stubs and do not provide management behavior.
  - Workflow models currently cover only `workflows`, `statuses`, and `status_transitions`; operation graph, webhook, and execution models are not yet specified in implementation detail.
  - Webhook ingress/egress and runtime async execution behavior are documented at architecture level, but no service-level contracts exist.
- **Goals**:
  - Define explicit admin API contracts for operation-user and workflow administration.
  - Specify persistent models and invariants for workflow graph, webhooks, and async execution.
  - Preserve DDD + Hexagonal boundaries across `src/auth`, `src/applications`, and app entrypoints.
  - Enforce idempotent, auditable, and retry-safe async behavior.
  - Keep admin scope explicit and permission-driven.
- **Out of scope (this slice)**:
  - Customer/operation `/api/applications` behaviors (already covered in `docs/design-applications-services.md`).
  - Frontend UX details beyond API contracts.
  - Provider-specific webhook payload schemas (kept as normalized JSON contracts).

## Functional Specifications

### Feature 1: Operation User Administration (`/api/users/operations/*`)
**User Story**: As an `admin`, I can list and manage operation users who execute customer-facing application workflows.  
**Acceptance Criteria**:
- Admin can list operation users with active/inactive filtering.
- Admin can assign the `operation` role to an existing active auth user.
- Admin can remove operation access without deleting the user account.
- Responses return safe identity summaries only.

**Functional Requirements**:
- FR-1: The system SHALL require `users:manage_operations` for all `/api/users/operations/*` routes.
- FR-2: The system SHALL support `GET /api/users/operations?active=true|false`.
- FR-3: The system SHALL support `POST /api/users/operations` to assign `operation` role to an existing user.
- FR-4: The system SHALL support `PATCH /api/users/operations/{user_id}` for operation-access enable/disable.
- FR-5: The system SHALL return deterministic conflict errors when role assignment already exists.
- FR-6: The system SHALL write audit events for role assignment/revocation with actor metadata.
- FR-7: The system SHALL never expose `password_hash` or secret fields in operation-user responses.
- FR-8: The system SHALL return `404 USER_NOT_FOUND` when target user does not exist.

### Feature 2: Workflow Catalog Administration (`/api/workflows/*`)
**User Story**: As an `admin`, I can manage country workflows and publish safe transition policies used by application lifecycle services.  
**Acceptance Criteria**:
- Admin can list workflows by country and active status.
- Admin can create draft workflow definitions for a country.
- Admin can update statuses and transitions only in draft versions.
- Admin can publish one active workflow version per country.

**Functional Requirements**:
- FR-9: The system SHALL require `workflows:manage` for all `/api/workflows/*` routes.
- FR-10: The system SHALL support `GET /api/workflows` with filters `country`, `active`, and `version_status`.
- FR-11: The system SHALL support `POST /api/workflows` to create draft workflows with country ownership.
- FR-12: The system SHALL enforce exactly one `is_initial=true` status per workflow version.
- FR-13: The system SHALL reject transitions referencing statuses outside the same workflow version.
- FR-14: The system SHALL reject terminal statuses with outgoing transitions.
- FR-15: The system SHALL keep published workflow versions immutable.
- FR-16: The system SHALL activate at most one published workflow per country at a time.
- FR-17: The system SHALL provide `POST /api/workflows/{workflow_id}/publish` with optimistic concurrency guard.
- FR-18: The system SHALL persist publication audit metadata (`published_by`, `published_at`, `version`).

### Feature 3: Workflow Operation Graph Administration
**User Story**: As an `admin`, I can define ordered operations/sub-operations and trigger rules that drive async execution for each workflow.  
**Acceptance Criteria**:
- Admin can create, update, and reorder operations per workflow.
- Admin can define sub-operations with execution type and target reference.
- Admin can define trigger rules for event, command, and webhook egress actions.
- Invalid graph references are rejected before publication.

**Functional Requirements**:
- FR-19: The system SHALL support `POST/PUT/DELETE` for workflow `operations`.
- FR-20: The system SHALL support `POST/PUT/DELETE` for `sub_operations` under each operation.
- FR-21: The system SHALL support `POST/PUT/DELETE` for `sub_operation_triggers`.
- FR-22: The system SHALL enforce contiguous `sort_order` values within each operation/sub-operation list.
- FR-23: The system SHALL validate `execution_type` against an explicit enum (`QUERY_USE_CASE`, `COMMAND_USE_CASE`, `THIRD_PARTY_HTTP_REQUEST`).
- FR-24: The system SHALL validate `trigger_type` against an explicit enum (`TRIGGER_EVENT`, `TRIGGER_COMMAND`, `TRIGGER_WEBHOOK_EGRESS`).
- FR-25: The system SHALL validate referenced status codes and event names at save time.
- FR-26: The system SHALL reject operation-graph edits when workflow version status is `PUBLISHED`.
- FR-27: The system SHALL snapshot the operation graph revision into runtime job records at enqueue time.
- FR-28: The system SHALL emit `WorkflowDefinitionPublished` integration event after publish commit.

### Feature 4: Webhook Administration for Workflows
**User Story**: As an `admin`, I can configure webhook endpoints per workflow and monitor delivery behavior.  
**Acceptance Criteria**:
- Admin can create ingress/egress webhook endpoints with country and provider mapping.
- Admin can rotate endpoint secrets without exposing secret material in responses.
- Admin can inspect webhook events and delivery attempts by workflow.
- Admin can replay failed egress deliveries.

**Functional Requirements**:
- FR-29: The system SHALL require `workflows:manage` for workflow webhook management routes.
- FR-30: The system SHALL support `POST /api/workflows/{workflow_id}/webhooks/endpoints`.
- FR-31: The system SHALL support `PATCH /api/workflows/{workflow_id}/webhooks/endpoints/{endpoint_id}` for activation and metadata updates.
- FR-32: The system SHALL support secret rotation via `POST /api/workflows/{workflow_id}/webhooks/endpoints/{endpoint_id}/rotate-secret`.
- FR-33: The system SHALL persist only secret references (`secret_ref`), never plaintext secrets.
- FR-34: The system SHALL support `GET /api/workflows/{workflow_id}/webhooks/events` with filters (`direction`, `event_type`, `delivery_status`).
- FR-35: The system SHALL support `POST /api/workflows/{workflow_id}/webhooks/events/{webhook_event_id}/replay` for failed egress events.
- FR-36: The system SHALL enforce idempotent replay requests using replay command id.
- FR-37: The system SHALL capture ingress signature verification result on each webhook event.
- FR-38: The system SHALL retain webhook payload hash and correlation metadata for audit.

### Feature 5: Async Workflow and Webhook Execution Runtime
**User Story**: As a platform owner, workflow and webhook async handlers run safely in parallel and remain auditable under retries/failures.  
**Acceptance Criteria**:
- Worker jobs are idempotent and correlation-linked to application/workflow artifacts.
- Duplicate broker deliveries do not cause duplicate side effects.
- Retry and DLQ behavior is deterministic per queue.
- Admin can inspect execution outcomes from API projections.
- `THIRD_PARTY_HTTP_REQUEST` executions follow a consistent contract for request rendering, auth, timeout, retries, and response mapping.

**Functional Requirements**:
- FR-39: The system SHALL persist one `WorkerJob` per scheduled execution unit with stable `idempotency_key`.
- FR-40: The system SHALL enforce unique idempotency for (`consumer_name`, `queue_name`, `message_id`) in event consumption tracking.
- FR-41: The system SHALL transition worker job states through explicit lifecycle (`PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `DEAD_LETTERED`).
- FR-42: The system SHALL record attempt count, error code/message, and next retry time for failed executions.
- FR-43: The system SHALL allow async handlers to emit commands/events, but only backend application services may write `Application` state.
- FR-44: The system SHALL include `correlation_id` and `workflow_revision` in runtime job payloads.
- FR-45: The system SHALL expose `GET /api/workflows/{workflow_id}/executions` for admin observability.
- FR-46: The system SHALL redact sensitive payload fields in execution logs and admin responses.
- FR-47: The system SHALL process webhook egress delivery attempts with bounded retries and DLQ fallback.
- FR-48: The system SHALL map retry exhaustion to persistent terminal states (`FAILED` or `DEAD_LETTERED`).
- FR-49: The system SHALL emit runtime events for state changes (`WorkflowExecutionQueued`, `WorkflowExecutionCompleted`, `WorkflowExecutionFailed`).
- FR-57: The system SHALL resolve `THIRD_PARTY_HTTP_REQUEST` `target_ref` to an active endpoint in the same workflow/country scope before execution.
- FR-58: The system SHALL render outbound request payloads from `input_template` and execution context (application snapshot + prior sub-operation outputs).
- FR-59: The system SHALL include `X-Correlation-Id` and `X-Idempotency-Key` headers in outbound HTTP requests.
- FR-60: The system SHALL enforce timeout from endpoint config (`timeout_ms`, default `5000`) with bounded allowed range.
- FR-61: The system SHALL retry only retryable failures (network/timeout, HTTP `408`, `425`, `429`, and `5xx`) using bounded exponential backoff.
- FR-62: The system SHALL persist one delivery-attempt record per HTTP attempt with response/error metadata and retry schedule.
- FR-63: The system SHALL enforce egress safety controls (HTTPS by default, endpoint/domain allowlist, and private-network blocking in non-test environments).
- FR-64: The system SHALL map final HTTP outcomes to execution/webhook statuses and emit corresponding success/failure events exactly once.

### Feature 6: Admin Scope, Authorization, and Audit Enforcement
**User Story**: As a security stakeholder, admin workflow services are explicit, least-privilege, and fully auditable.  
**Acceptance Criteria**:
- Admin-only services are guarded by explicit permissions.
- Admin actions are audit-tracked with actor and request metadata.
- Admin does not inherit operation/customer application actions by default.

**Functional Requirements**:
- FR-50: The system SHALL enforce explicit permission checks on every admin workflow service route.
- FR-51: The system SHALL write audit events for create/update/delete/publish/replay operations.
- FR-52: The system SHALL include `request_id` and `correlation_id` in admin mutations.
- FR-53: The system SHALL require optimistic concurrency (`version` or `etag`) on mutable workflow resources.
- FR-54: The system SHALL deny unsafe destructive actions on published workflows unless a replacement is activated.
- FR-55: The system SHALL deny `admin` access to `/api/applications/*` in MVP unless an explicit future design supersedes this behavior.
- FR-56: The system SHALL include security test coverage for permission boundaries and replay abuse scenarios.

## Technical Design

### Architecture and Boundaries
- `src/auth/` owns operation-user role assignment/revocation rules and permission resolution.
- `src/applications/workflow/` owns workflow definition entities, status policy, and operation graph metadata.
- `src/applications/webhook/` owns webhook endpoint/event/delivery domain and adapters.
- `src/applications/execution/` owns runtime job state and idempotent event-consumption tracking.
- `apps/backend/` owns admin HTTP routes, schema validation, dependency wiring, and principal extraction.
- `apps/webhooks/` owns webhook ingress/egress transport and signature verification concerns.
- `apps/workers/` owns async consumers and command/event runners.

### Proposed Source Layout
```text
src/auth/
└── operations_admin/
    ├── domain/
    │   ├── entities.py
    │   └── ports/
    │       └── operation_user_repository.py
    ├── application/
    │   ├── commands/
    │   │   ├── assign_operation_role.py
    │   │   └── revoke_operation_role.py
    │   └── services/
    │       └── manage_operation_users_service.py
    └── infrastructure/
        └── adapters/
            └── operation_user_repository.py

src/applications/
├── workflow/
│   ├── domain/
│   │   ├── entities.py
│   │   ├── events.py
│   │   └── ports/
│   │       └── workflow_admin_repository.py
│   ├── application/
│   │   ├── commands/
│   │   │   ├── create_workflow.py
│   │   │   ├── publish_workflow.py
│   │   │   └── upsert_workflow_graph.py
│   │   └── services/
│   │       ├── workflow_catalog_service.py
│   │       └── workflow_graph_service.py
│   └── infrastructure/
│       └── adapters/
│           ├── operation_orm_model.py
│           ├── sub_operation_orm_model.py
│           └── sub_operation_trigger_orm_model.py
├── webhook/
│   ├── domain/
│   │   ├── entities.py
│   │   ├── events.py
│   │   └── ports/
│   │       └── webhook_repository.py
│   ├── application/
│   │   ├── commands/
│   │   │   ├── configure_webhook_endpoint.py
│   │   │   └── replay_webhook_delivery.py
│   │   └── services/
│   │       ├── webhook_endpoint_service.py
│   │       └── webhook_event_service.py
│   └── infrastructure/
│       └── adapters/
│           ├── webhook_endpoint_orm_model.py
│           ├── webhook_event_orm_model.py
│           └── webhook_delivery_attempt_orm_model.py
└── execution/
    ├── domain/
    │   ├── entities.py
    │   └── ports/
    │       └── execution_repository.py
    ├── application/
    │   └── services/
    │       └── workflow_execution_service.py
    └── infrastructure/
        └── adapters/
            ├── worker_job_orm_model.py
            └── event_consumption_orm_model.py

apps/backend/
└── api/
    ├── users_operations/
    │   ├── router.py
    │   ├── schemas.py
    │   └── dependencies.py
    └── workflows/
        ├── router.py
        ├── schemas.py
        └── dependencies.py
```

### Data Models (PostgreSQL)

#### Workflow definition models
`workflows` table (existing, extended):
- `id UUID PRIMARY KEY`
- `country TEXT NOT NULL`
- `active BOOLEAN NOT NULL`
- `version INT NOT NULL`
- `version_status TEXT NOT NULL` (`DRAFT`, `PUBLISHED`, `RETIRED`)
- `published_by UUID NULL REFERENCES auth_users(id)`
- `published_at TIMESTAMPTZ NULL`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

`statuses` and `status_transitions` remain the policy graph for application lifecycle; publication invariants apply per workflow version.

`operations` table:
- `id UUID PRIMARY KEY`
- `workflow_id UUID NOT NULL REFERENCES workflows(id)`
- `name TEXT NOT NULL`
- `sort_order INT NOT NULL`
- `active BOOLEAN NOT NULL DEFAULT TRUE`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

`sub_operations` table:
- `id UUID PRIMARY KEY`
- `operation_id UUID NOT NULL REFERENCES operations(id)`
- `sort_order INT NOT NULL`
- `execution_type TEXT NOT NULL`
- `target_ref TEXT NOT NULL`
- `input_template JSONB NOT NULL DEFAULT '{}'::jsonb`
- `output_alias TEXT NULL`
- `active BOOLEAN NOT NULL DEFAULT TRUE`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

`sub_operation_triggers` table:
- `id UUID PRIMARY KEY`
- `sub_operation_id UUID NOT NULL REFERENCES sub_operations(id)`
- `trigger_type TEXT NOT NULL`
- `trigger_name TEXT NOT NULL`
- `payload_template JSONB NOT NULL DEFAULT '{}'::jsonb`
- `condition_expr TEXT NULL`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

#### Webhook models
`webhook_endpoints` table:
- `id UUID PRIMARY KEY`
- `workflow_id UUID NOT NULL REFERENCES workflows(id)`
- `country TEXT NOT NULL`
- `provider_code TEXT NOT NULL`
- `direction TEXT NOT NULL` (`INGRESS`, `EGRESS`)
- `event_type TEXT NOT NULL`
- `method TEXT NOT NULL`
- `url TEXT NOT NULL`
- `secret_ref TEXT NOT NULL`
- `timeout_ms INT NOT NULL DEFAULT 5000`
- `active BOOLEAN NOT NULL DEFAULT TRUE`
- `created_by UUID NOT NULL REFERENCES auth_users(id)`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

`webhook_events` table:
- `id UUID PRIMARY KEY`
- `endpoint_id UUID NOT NULL REFERENCES webhook_endpoints(id)`
- `workflow_id UUID NOT NULL REFERENCES workflows(id)`
- `application_id UUID NULL REFERENCES applications(id)`
- `direction TEXT NOT NULL`
- `event_type TEXT NOT NULL`
- `payload JSONB NOT NULL`
- `payload_hash TEXT NOT NULL`
- `signature_valid BOOLEAN NULL`
- `external_event_id TEXT NULL`
- `correlation_id UUID NOT NULL`
- `delivery_status TEXT NOT NULL` (`RECEIVED`, `QUEUED`, `DELIVERED`, `FAILED`, `DEAD_LETTERED`)
- `occurred_at TIMESTAMPTZ NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL`

`webhook_delivery_attempts` table:
- `id UUID PRIMARY KEY`
- `webhook_event_id UUID NOT NULL REFERENCES webhook_events(id)`
- `attempt_no INT NOT NULL`
- `delivery_status TEXT NOT NULL`
- `response_code INT NULL`
- `response_body TEXT NULL`
- `latency_ms INT NULL`
- `error_code TEXT NULL`
- `error_message TEXT NULL`
- `next_retry_at TIMESTAMPTZ NULL`
- `created_at TIMESTAMPTZ NOT NULL`

#### Async execution models
`worker_jobs` table:
- `id UUID PRIMARY KEY`
- `workflow_id UUID NOT NULL REFERENCES workflows(id)`
- `workflow_revision INT NOT NULL`
- `application_id UUID NULL REFERENCES applications(id)`
- `operation_id UUID NULL REFERENCES operations(id)`
- `sub_operation_id UUID NULL REFERENCES sub_operations(id)`
- `idempotency_key TEXT NOT NULL`
- `status TEXT NOT NULL` (`PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `DEAD_LETTERED`)
- `attempts INT NOT NULL DEFAULT 0`
- `max_attempts INT NOT NULL DEFAULT 5`
- `available_at TIMESTAMPTZ NOT NULL`
- `locked_at TIMESTAMPTZ NULL`
- `completed_at TIMESTAMPTZ NULL`
- `last_error_code TEXT NULL`
- `last_error_message TEXT NULL`
- `correlation_id UUID NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

`event_consumptions` table:
- `id UUID PRIMARY KEY`
- `consumer_name TEXT NOT NULL`
- `queue_name TEXT NOT NULL`
- `message_id TEXT NOT NULL`
- `correlation_id UUID NULL`
- `processed_at TIMESTAMPTZ NOT NULL`

#### Constraints and indexes
- Unique: `workflows(country, version)`.
- Unique partial: one active published workflow per country (`active=true AND version_status='PUBLISHED'`).
- Unique: one initial status per workflow (`statuses(workflow_id)` where `is_initial=true`).
- Unique: `status_transitions(from_status_id, to_status_id)`.
- Unique: `operations(workflow_id, sort_order)`.
- Unique: `sub_operations(operation_id, sort_order)`.
- Unique: `webhook_delivery_attempts(webhook_event_id, attempt_no)`.
- Unique: `worker_jobs(idempotency_key)`.
- Unique: `event_consumptions(consumer_name, queue_name, message_id)`.
- Index: `webhook_events(workflow_id, created_at DESC)`.
- Index: `worker_jobs(workflow_id, status, available_at)`.

### Invariants and write-path rules
- Published workflow versions are immutable.
- Only one active published workflow can exist per country.
- Backend application services remain single-writer for `applications` state.
- Webhook and worker processes can emit commands/events but never mutate `applications` table directly.
- Async side effects must be idempotent under at-least-once delivery.
- Admin mutation endpoints require optimistic concurrency (`version`/`etag` semantics).

### Domain Specification Catalog (Documentation Only)
The following catalog is normative for implementation and intentionally lives in this document (not in runtime code) until each model is implemented.

Value catalogs:
- `WorkflowVersionStatus`: `DRAFT`, `PUBLISHED`, `RETIRED`
- `SubOperationExecutionType`: `QUERY_USE_CASE`, `COMMAND_USE_CASE`, `THIRD_PARTY_HTTP_REQUEST`
- `SubOperationTriggerType`: `TRIGGER_EVENT`, `TRIGGER_COMMAND`, `TRIGGER_WEBHOOK_EGRESS`
- `WebhookDirection`: `INGRESS`, `EGRESS`
- `WebhookDeliveryStatus`: `RECEIVED`, `QUEUED`, `DELIVERED`, `FAILED`, `DEAD_LETTERED`
- `WorkflowExecutionStatus`: `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `DEAD_LETTERED`

Conceptual entity contracts:
- `Workflow`:
  - Fields: `id`, `country`, `active`, `version`, `version_status`, `published_by`, `published_at`
  - Owns: `statuses`, transitions, and operation graph root.
- `WorkflowOperation`:
  - Fields: `id`, `workflow_id`, `name`, `sort_order`, `active`
  - Owns ordered `sub_operations`.
- `WorkflowSubOperation`:
  - Fields: `id`, `operation_id`, `sort_order`, `execution_type`, `target_ref`, `input_template`, `output_alias`, `active`
  - Owns ordered `triggers`.
- `WorkflowSubOperationTrigger`:
  - Fields: `id`, `sub_operation_id`, `trigger_type`, `trigger_name`, `payload_template`, `condition_expr`
  - Emits internal event/command/webhook egress intent.
- `WorkflowWebhookEndpoint`:
  - Fields: `id`, `workflow_id`, `country`, `provider_code`, `direction`, `event_type`, `method`, `url`, `secret_ref`, `timeout_ms`, `active`
  - Invariant: secret material is referenced, never stored plaintext.
- `WorkflowWebhookEvent`:
  - Fields: `id`, `endpoint_id`, `workflow_id`, `application_id`, `direction`, `event_type`, `payload_hash`, `signature_valid`, `correlation_id`, `delivery_status`, `occurred_at`
  - Captures normalized ingress/egress event record.
- `WorkflowWebhookDeliveryAttempt`:
  - Fields: `id`, `webhook_event_id`, `attempt_no`, `delivery_status`, `response_code`, `error_code`, `error_message`, `next_retry_at`, `created_at`
  - Captures each network attempt and retry metadata.
- `WorkflowExecutionJob`:
  - Fields: `id`, `workflow_id`, `workflow_revision`, `application_id`, `operation_id`, `sub_operation_id`, `idempotency_key`, `status`, `attempts`, `max_attempts`, `available_at`, `locked_at`, `completed_at`, `correlation_id`, `last_error_code`, `last_error_message`
  - Invariant: idempotent under retries and parallel worker execution.
- `WorkflowEventConsumption`:
  - Fields: `id`, `consumer_name`, `queue_name`, `message_id`, `correlation_id`, `processed_at`
  - Invariant: unique (`consumer_name`, `queue_name`, `message_id`) checkpoint.

### API Contracts

#### `GET /api/users/operations`
- Permission: `users:manage_operations`
- Query params: `active` (optional), `page`, `page_size`
- Success (`200`):
```json
{
  "items": [
    {
      "user_id": "uuid",
      "email": "operation@example.com",
      "is_active": true,
      "has_operation_role": true,
      "updated_at": "2026-02-17T10:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

#### `POST /api/users/operations`
- Permission: `users:manage_operations`
- Request:
```json
{
  "user_id": "uuid"
}
```
- Success (`201`):
```json
{
  "user_id": "uuid",
  "assigned_role": "operation",
  "assigned_at": "2026-02-17T10:02:00Z"
}
```
- Errors: `404 USER_NOT_FOUND`, `409 ROLE_ALREADY_ASSIGNED`

#### `PATCH /api/users/operations/{user_id}`
- Permission: `users:manage_operations`
- Request:
```json
{
  "enabled": false
}
```
- Success (`200`): `{ "user_id": "uuid", "enabled": false, "updated_at": "..." }`

#### `GET /api/workflows`
- Permission: `workflows:manage`
- Query params: `country`, `active`, `version_status`
- Success (`200`):
```json
{
  "items": [
    {
      "id": "uuid",
      "country": "MX",
      "version": 3,
      "version_status": "PUBLISHED",
      "active": true,
      "published_at": "2026-02-17T10:05:00Z"
    }
  ]
}
```

#### `POST /api/workflows`
- Permission: `workflows:manage`
- Request:
```json
{
  "country": "MX",
  "version": 4,
  "statuses": [
    { "code": "PENDING_REVIEW", "label": "Pending review", "is_initial": true, "is_terminal": false, "sort_order": 1 },
    { "code": "APPROVED", "label": "Approved", "is_initial": false, "is_terminal": true, "sort_order": 2 },
    { "code": "REJECTED", "label": "Rejected", "is_initial": false, "is_terminal": true, "sort_order": 3 }
  ],
  "transitions": [
    { "from": "PENDING_REVIEW", "to": "APPROVED" },
    { "from": "PENDING_REVIEW", "to": "REJECTED" }
  ]
}
```
- Success (`201`): `{ "id": "uuid", "country": "MX", "version": 4, "version_status": "DRAFT" }`

#### `PUT /api/workflows/{workflow_id}/graph`
- Permission: `workflows:manage`
- Purpose: upsert operations, sub-operations, and triggers for a draft workflow version
- Concurrency:
  - Require one optimistic guard: `If-Match` header (preferred) or `expected_version` body field.
  - If both are present, they must match.
  - Missing guard returns `428 PRECONDITION_REQUIRED`.
- Request:
```json
{
  "expected_version": 4,
  "operations": [
    {
      "id": "uuid-or-null-for-create",
      "name": "provider_enrichment",
      "sort_order": 1,
      "active": true,
      "sub_operations": [
        {
          "id": "uuid-or-null-for-create",
          "sort_order": 1,
          "execution_type": "THIRD_PARTY_HTTP_REQUEST",
          "target_ref": "webhook_endpoint:8baf2f63-657f-4f8f-8eef-bb258c62297f",
          "input_template": {
            "application_id": "{{ application.id }}",
            "country": "{{ application.country }}"
          },
          "output_alias": "provider_response",
          "active": true,
          "triggers": [
            {
              "id": "uuid-or-null-for-create",
              "trigger_type": "TRIGGER_EVENT",
              "trigger_name": "credit.workflow.execution.completed",
              "payload_template": {
                "application_id": "{{ application.id }}",
                "result_alias": "provider_response"
              },
              "condition_expr": "provider_response.approved == true"
            }
          ]
        }
      ]
    }
  ],
  "deleted_operation_ids": [],
  "deleted_sub_operation_ids": [],
  "deleted_trigger_ids": []
}
```
- Success (`200`):
```json
{
  "workflow_id": "uuid",
  "version": 4,
  "graph_revision": 12,
  "etag": "W/\"workflow:uuid:v4:r12\"",
  "counts": {
    "operations": 3,
    "sub_operations": 7,
    "triggers": 9
  },
  "updated_at": "2026-02-17T10:08:00Z"
}
```
- Validation semantics:
  - `sort_order` must be contiguous and unique per sibling scope.
  - `target_ref` is required for `THIRD_PARTY_HTTP_REQUEST` and validated before commit.
  - `trigger_name` and `trigger_type` must map to known routing/event contracts.
- Errors:
  - `404 WORKFLOW_NOT_FOUND`
  - `409 WORKFLOW_NOT_DRAFT`
  - `409 VERSION_CONFLICT`
  - `412 ETAG_MISMATCH`
  - `422 GRAPH_VALIDATION_ERROR`

#### `POST /api/workflows/{workflow_id}/publish`
- Permission: `workflows:manage`
- Request:
```json
{
  "expected_version": 4
}
```
- Success (`200`):
```json
{
  "workflow_id": "uuid",
  "country": "MX",
  "version": 4,
  "version_status": "PUBLISHED",
  "active": true,
  "published_at": "2026-02-17T10:10:00Z"
}
```
- Errors: `409 VERSION_CONFLICT`, `409 WORKFLOW_VALIDATION_FAILED`

#### `POST /api/workflows/{workflow_id}/webhooks/endpoints`
- Permission: `workflows:manage`
- Request:
```json
{
  "direction": "EGRESS",
  "provider_code": "provider_x",
  "event_type": "ApplicationStatusUpdated",
  "method": "POST",
  "url": "https://provider.example/webhooks/status",
  "secret_ref": "secrets://webhooks/provider_x/status",
  "timeout_ms": 5000,
  "active": true
}
```
- Success (`201`): `{ "endpoint_id": "uuid", "direction": "EGRESS", "active": true }`

#### `PATCH /api/workflows/{workflow_id}/webhooks/endpoints/{endpoint_id}`
- Permission: `workflows:manage`
- Request:
```json
{
  "active": false,
  "url": "https://provider.example/webhooks/status-v2",
  "timeout_ms": 7000
}
```
- Success (`200`):
```json
{
  "endpoint_id": "uuid",
  "workflow_id": "uuid",
  "active": false,
  "updated_at": "2026-02-17T10:12:00Z"
}
```
- Errors: `404 WORKFLOW_NOT_FOUND`, `404 ENDPOINT_NOT_FOUND`, `409 ENDPOINT_WORKFLOW_MISMATCH`, `422 WEBHOOK_ENDPOINT_VALIDATION_ERROR`

#### `POST /api/workflows/{workflow_id}/webhooks/endpoints/{endpoint_id}/rotate-secret`
- Permission: `workflows:manage`
- Request:
```json
{
  "reason": "scheduled_rotation_q1"
}
```
- Success (`200`):
```json
{
  "endpoint_id": "uuid",
  "secret_ref": "secrets://webhooks/provider_x/status/v2",
  "rotated_at": "2026-02-17T10:13:00Z"
}
```
- Errors: `404 WORKFLOW_NOT_FOUND`, `404 ENDPOINT_NOT_FOUND`, `409 ENDPOINT_WORKFLOW_MISMATCH`

#### `GET /api/workflows/{workflow_id}/webhooks/events`
- Permission: `workflows:manage`
- Query params:
  - Filters: `direction`, `event_type`, `delivery_status`, `application_id`, `correlation_id`
  - Pagination: `page` (default `1`), `page_size` (default `50`, max `100`)
  - Sorting: `sort_by` (`occurred_at` or `created_at`, default `occurred_at`), `sort_dir` (`asc` or `desc`, default `desc`)
- Success (`200`):
```json
{
  "items": [
    {
      "id": "uuid",
      "endpoint_id": "uuid",
      "provider_code": "provider_x",
      "direction": "EGRESS",
      "event_type": "ApplicationStatusUpdated",
      "application_id": "uuid",
      "payload_hash": "sha256:3e2d...",
      "signature_valid": null,
      "delivery_status": "FAILED",
      "correlation_id": "uuid",
      "occurred_at": "2026-02-17T10:15:00Z",
      "created_at": "2026-02-17T10:15:01Z",
      "last_attempt": {
        "attempt_no": 3,
        "delivery_status": "FAILED",
        "response_code": 504,
        "error_code": "HTTP_TIMEOUT",
        "error_message": "provider request timeout",
        "next_retry_at": null,
        "created_at": "2026-02-17T10:20:00Z"
      }
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 1,
  "sort_by": "occurred_at",
  "sort_dir": "desc"
}
```
- Errors: `404 WORKFLOW_NOT_FOUND`, `422 INVALID_QUERY_PARAMS`

#### `POST /api/workflows/{workflow_id}/webhooks/events/{webhook_event_id}/replay`
- Permission: `workflows:manage`
- Request:
```json
{
  "command_id": "uuid",
  "reason": "manual_replay_after_provider_fix"
}
```
- Success (`202`): `{ "queued": true, "command_id": "uuid" }`
- Errors: `404 WORKFLOW_NOT_FOUND`, `404 WEBHOOK_EVENT_NOT_FOUND`, `409 REPLAY_COMMAND_DUPLICATE`, `409 REPLAY_COOLDOWN_ACTIVE`, `429 REPLAY_RATE_LIMIT_EXCEEDED`

#### `GET /api/workflows/{workflow_id}/executions`
- Permission: `workflows:manage`
- Query params:
  - Filters: `status`, `application_id`, `operation_id`, `sub_operation_id`, `from`, `to`, `correlation_id`
  - Pagination: `page` (default `1`), `page_size` (default `50`, max `100`)
  - Sorting: `sort_by` (`updated_at`, `available_at`, `created_at`, default `updated_at`), `sort_dir` (`asc` or `desc`, default `desc`)
- Success (`200`):
```json
{
  "items": [
    {
      "job_id": "uuid",
      "workflow_id": "uuid",
      "workflow_revision": 4,
      "application_id": "uuid",
      "operation": {
        "id": "uuid",
        "name": "provider_enrichment",
        "sort_order": 1
      },
      "sub_operation": {
        "id": "uuid",
        "execution_type": "THIRD_PARTY_HTTP_REQUEST",
        "target_ref": "webhook_endpoint:8baf2f63-657f-4f8f-8eef-bb258c62297f"
      },
      "status": "FAILED",
      "attempts": 3,
      "max_attempts": 5,
      "available_at": "2026-02-17T10:18:00Z",
      "locked_at": "2026-02-17T10:18:01Z",
      "completed_at": null,
      "last_error_code": "HTTP_TIMEOUT",
      "last_error_message": "provider request timeout",
      "correlation_id": "uuid",
      "payload_summary": {
        "input_fields": ["application.id", "application.country"],
        "output_aliases": ["provider_response"],
        "redacted": true
      },
      "updated_at": "2026-02-17T10:20:00Z",
      "created_at": "2026-02-17T10:17:55Z"
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 1,
  "sort_by": "updated_at",
  "sort_dir": "desc"
}
```
- Errors: `404 WORKFLOW_NOT_FOUND`, `422 INVALID_QUERY_PARAMS`

### Messaging Topology
- **Workflow events exchange**: `workflows.events`
- **Workflow commands exchange**: `workflows.commands`
- **Webhook events exchange**: `webhooks.events`
- **Webhook commands exchange**: `webhooks.commands`

Routing keys:
- `credit.workflow.definition.published`
- `credit.workflow.execution.queued`
- `credit.workflow.execution.completed`
- `credit.workflow.execution.failed`
- `credit.webhook.ingress.received`
- `credit.webhook.egress.deliver`
- `credit.webhook.egress.delivered`
- `credit.webhook.egress.failed`
- `credit.webhook.egress.replay`

Suggested queue bindings:
- `workers.workflow.execute.q` <- `credit.workflow.execution.queued`
- `workers.webhook.ingress.normalize.q` <- `credit.webhook.ingress.received`
- `workers.webhook.egress.deliver.q` <- `credit.webhook.egress.deliver`
- `workers.webhook.egress.replay.q` <- `credit.webhook.egress.replay`
- `backend.workflow.execution.projection.q` <- `credit.workflow.execution.*`

Per-queue policy expectations:
- Queue-specific retry TTL, DLQ, and prefetch.
- Bounded retries with deterministic dead-letter behavior.
- Consumer idempotency based on `event_consumptions` unique key.

Canonical message envelope:
```json
{
  "message_id": "uuid",
  "routing_key": "credit.workflow.execution.queued",
  "event_name": "WorkflowExecutionQueued",
  "schema_version": "1.0",
  "occurred_at": "2026-02-17T10:18:00Z",
  "correlation_id": "uuid",
  "causation_id": "uuid-or-null",
  "producer": "apps.backend",
  "payload": {}
}
```

Routing-key payload contracts:
- `credit.workflow.definition.published`:
```json
{
  "workflow_id": "uuid",
  "country": "MX",
  "version": 4,
  "graph_revision": 12,
  "published_by": "uuid",
  "published_at": "2026-02-17T10:10:00Z"
}
```
- `credit.workflow.execution.queued`:
```json
{
  "job_id": "uuid",
  "workflow_id": "uuid",
  "workflow_revision": 4,
  "application_id": "uuid",
  "operation_id": "uuid",
  "sub_operation_id": "uuid",
  "idempotency_key": "workflow:uuid:app:uuid:op:1:sub:1",
  "available_at": "2026-02-17T10:18:00Z"
}
```
- `credit.workflow.execution.completed`:
```json
{
  "job_id": "uuid",
  "workflow_id": "uuid",
  "workflow_revision": 4,
  "application_id": "uuid",
  "status": "SUCCEEDED",
  "attempts": 1,
  "completed_at": "2026-02-17T10:18:05Z",
  "outputs_summary": {
    "aliases": ["provider_response"],
    "redacted": true
  }
}
```
- `credit.workflow.execution.failed`:
```json
{
  "job_id": "uuid",
  "workflow_id": "uuid",
  "workflow_revision": 4,
  "application_id": "uuid",
  "status": "FAILED",
  "attempts": 3,
  "max_attempts": 5,
  "last_error_code": "HTTP_TIMEOUT",
  "last_error_message": "provider request timeout",
  "next_retry_at": null,
  "terminal": true
}
```
- `credit.webhook.ingress.received`:
```json
{
  "webhook_event_id": "uuid",
  "endpoint_id": "uuid",
  "workflow_id": "uuid",
  "application_id": "uuid-or-null",
  "provider_code": "provider_x",
  "event_type": "ProviderDecisionReceived",
  "signature_valid": true,
  "payload_hash": "sha256:3e2d..."
}
```
- `credit.webhook.egress.deliver`:
```json
{
  "webhook_event_id": "uuid",
  "endpoint_id": "uuid",
  "workflow_id": "uuid",
  "application_id": "uuid-or-null",
  "event_type": "ApplicationStatusUpdated",
  "attempt_no": 1,
  "timeout_ms": 5000
}
```
- `credit.webhook.egress.delivered`:
```json
{
  "webhook_event_id": "uuid",
  "endpoint_id": "uuid",
  "delivery_status": "DELIVERED",
  "attempt_no": 1,
  "response_code": 200,
  "latency_ms": 184
}
```
- `credit.webhook.egress.failed`:
```json
{
  "webhook_event_id": "uuid",
  "endpoint_id": "uuid",
  "delivery_status": "FAILED",
  "attempt_no": 3,
  "error_code": "HTTP_TIMEOUT",
  "error_message": "provider request timeout",
  "terminal": true
}
```
- `credit.webhook.egress.replay`:
```json
{
  "command_id": "uuid",
  "webhook_event_id": "uuid",
  "workflow_id": "uuid",
  "requested_by": "uuid",
  "reason": "manual_replay_after_provider_fix",
  "requested_at": "2026-02-17T10:30:00Z"
}
```

### Async Execution Flows

#### Ingress webhook flow
1. Provider calls webhook ingress endpoint.
2. Webhooks app verifies signature and persists `webhook_events` (`direction=INGRESS`).
3. Webhooks app publishes normalized command/event.
4. Worker/backend consumer records `event_consumptions` idempotency checkpoint.
5. Backend applies allowed state changes through application services only.

#### Egress webhook flow
1. Backend/workers publish egress command for a workflow event.
2. Delivery worker resolves active `webhook_endpoint` and executes HTTP request.
3. Worker persists `webhook_delivery_attempts` and updates `webhook_events.delivery_status`.
4. Retry scheduling uses per-queue policy until success or retry exhaustion.
5. Failure terminal state emits `credit.webhook.egress.failed` and remains replayable by admin.

### External HTTP Request Execution Specification
Applies to sub-operations where `execution_type=THIRD_PARTY_HTTP_REQUEST`.

Target resolution:
- Preferred `target_ref` format: `webhook_endpoint:{endpoint_id}`.
- Allowed compatibility format: `provider:{provider_code}:{event_type}`.
- Resolver must return exactly one active endpoint for the workflow/country scope; otherwise fail validation before enqueue.

Request construction:
- Method and URL are resolved from `webhook_endpoints` (`method`, `url`).
- Request body is rendered from `input_template` using:
  - application execution context
  - previous sub-operation outputs referenced by `output_alias`
- Standard outbound headers:
  - `Content-Type: application/json`
  - `Accept: application/json`
  - `X-Request-Id`
  - `X-Correlation-Id`
  - `X-Idempotency-Key`
- Authentication/signing:
  - Secret material is resolved via `secret_ref` at runtime.
  - Secrets are never persisted in execution tables/logs.
  - Signature-based providers use deterministic canonical payload hashing before signing.

Timeout and retry policy:
- Timeout source: `webhook_endpoints.timeout_ms` (default `5000`, recommended bounds `1000..30000`).
- Retryable failures:
  - transport failures (DNS/connect/reset/timeout)
  - HTTP `408`, `425`, `429`
  - HTTP `5xx`
- Non-retryable failures:
  - HTTP `4xx` except `408`, `425`, `429`
  - schema/rendering/validation errors
- Retry schedule: exponential backoff with jitter, bounded by `worker_jobs.max_attempts`.
- Retry exhaustion transitions to terminal failure state and DLQ path where configured.

Outcome mapping and persistence:
- Every attempt appends one `webhook_delivery_attempts` record with:
  - `attempt_no`
  - `delivery_status`
  - `response_code`
  - `error_code` / `error_message`
  - `next_retry_at` (when retryable)
- Success path:
  - `webhook_events.delivery_status=DELIVERED`
  - `worker_jobs.status=SUCCEEDED`
  - emit `credit.webhook.egress.delivered`
- Retryable failure path:
  - `webhook_events.delivery_status=QUEUED`
  - `worker_jobs.status=RUNNING` or `FAILED` with next attempt scheduled
  - emit retry telemetry only (no terminal failure event)
- Terminal failure path:
  - `webhook_events.delivery_status=FAILED` or `DEAD_LETTERED`
  - `worker_jobs.status=FAILED` or `DEAD_LETTERED`
  - emit `credit.webhook.egress.failed`

Security and compliance controls:
- Enforce endpoint allowlist for production egress.
- Block loopback/private CIDR destinations in non-test environments.
- Redact sensitive headers and payload fields in logs/metrics/traces.
- Bound response body capture to prevent sensitive or large payload persistence.

### Realtime Push Contract (Backend -> Frontend)
This section closes `DX3` interface ambiguity by defining an implementation-ready backend contract aligned with frontend subscriber expectations.

Transport and authorization:
- Endpoint: `GET /api/realtime/applications/ws`.
- Protocol: WebSocket (`wss` in non-local environments).
- AuthN:
  - Preferred: same-origin secure session cookie during WebSocket handshake.
  - Token mode: `?access_token=<jwt>` query parameter when cookie mode is not available.
- AuthZ at connect time:
  - `customer`: allowed, stream only customer-owned application updates.
  - `operation`: allowed, stream all application updates.
  - `admin`: denied (`403`) for MVP scope.

Frame contract:
- Event frame MAY be sent as either direct payload or wrapped payload to support current frontend parser:
```json
{
  "version": 12,
  "application": {
    "id": "uuid",
    "country": "MX",
    "status_code": "APPROVED",
    "requested_amount": 1500.0,
    "created_at": "2026-02-17T10:00:00Z",
    "updated_at": "2026-02-17T10:20:00Z"
  },
  "meta": {
    "event_type": "ApplicationStatusUpdated",
    "schema_version": "1.0",
    "correlation_id": "uuid",
    "emitted_at": "2026-02-17T10:20:00Z"
  }
}
```
or
```json
{
  "event": {
    "version": 12,
    "application": {
      "id": "uuid",
      "country": "MX",
      "status_code": "APPROVED",
      "requested_amount": 1500.0,
      "created_at": "2026-02-17T10:00:00Z",
      "updated_at": "2026-02-17T10:20:00Z"
    }
  },
  "meta": {
    "event_type": "ApplicationStatusUpdated",
    "schema_version": "1.0",
    "correlation_id": "uuid",
    "emitted_at": "2026-02-17T10:20:00Z"
  }
}
```

Delivery and resiliency rules:
- Server sends update frames for `ApplicationCreated` and `ApplicationStatusUpdated` projections.
- Server may emit non-event control frames (for example heartbeat); clients must ignore unknown shapes.
- Heartbeat interval target: every `25s` while connected.
- Reconnect strategy expectation for clients: exponential backoff with jitter, capped at `30s`.
- Ordering model: at-least-once and potentially out-of-order; client reconciliation MUST use `(application.id, version)` and ignore stale versions.

## Security Controls
- Admin endpoints require explicit permission dependencies (`users:manage_operations`, `workflows:manage`).
- All admin writes must record actor, request id, and correlation id.
- Webhook secrets are stored as references only; plaintext values are never returned.
- Webhook payloads and execution logs apply PII redaction and payload-size limits.
- Replay endpoints are protected against abuse via idempotent command ids and audit logs.
- Admin application-access policy must remain explicit:
  - For MVP parity with auth design intent, `admin` should not gain `/api/applications/*` capabilities by default.
  - Current seeded permission mapping includes `applications:list_all` for `admin`; this is a tracked implementation gap.

## Phased Implementation Plan
1. **Phase 1: Versioned Workflow Catalog**
   - Objective: introduce draft/published workflow versions and immutable publication behavior.
   - Deliverables: `workflows.version`, `workflows.version_status`, publish workflow command/service, single active published workflow per country invariant.
2. **Phase 2: Operation Graph Model**
   - Objective: implement operations, sub-operations, and triggers with deterministic ordering.
   - Deliverables: `operations`, `sub_operations`, `sub_operation_triggers` persistence + graph validation for enums/references.
3. **Phase 3: Webhook Domain Integration**
   - Objective: add workflow-owned webhook endpoint/event/delivery models and admin control surface.
   - Deliverables: `webhook_endpoints`, `webhook_events`, `webhook_delivery_attempts`, replay command contract with idempotency key.
4. **Phase 4: Async Runtime and Idempotency**
   - Objective: add explicit job lifecycle and duplicate-consumption safety for parallel workers.
   - Deliverables: `worker_jobs`, `event_consumptions`, retry/DLQ terminal-state semantics, execution observability query contracts.
5. **Phase 5: Admin Policy Alignment**
   - Objective: align role-permission behavior with admin scope and complete security test coverage.
   - Deliverables: workflow admin route guards, operation-user administration service, admin scope enforcement tests, audit/correlation metadata checks.

## PRD + Architecture Coverage Audit (Repository Snapshot: 2026-02-17)
This audit cross-checks:
- `docs/prd-credit-applications-hub.md`
- `docs/architecture-specification.md`
against the current repository state on 2026-02-17.

### Missing Implementation Matrix
| Source Requirement | Expected Capability | Current Repository State | Missing Part | Tracking |
|---|---|---|---|---|
| PRD goal: provider/banking data by country | Provider adapters + banking snapshot/reference persistence | No `BankingData`/provider model, table, or adapter artifacts found in `src/` or migrations | Country provider integration and banking-data persistence layer | Add cross-slice task `DX1` |
| PRD acceptance: webhook flow integrated | At least one ingress or egress webhook flow that updates app/audit state | `apps/webhooks/ingress/` and `apps/webhooks/egress/` exist as empty scaffolds | Webhook app transport handlers and end-to-end integration flow | `WA6`, `WA8`, `WA9`, plus `DX2` |
| PRD scope: basic caching for one read path | Read cache for list/detail path with invalidation strategy | `src/applications/application/infrastructure/adapters/application_list_cache.py` + `cached_application_read_repository.py` provide Redis/in-memory cache for applications list reads | List cache invalidation strategy can be tightened after provider/runtime slices settle | `DX4` (DONE baseline) |
| PRD scope: deployment artifacts | Kubernetes manifests for backend/frontend/workers (+db if included) | Helm chart and Docker build assets now exist under `deploy/helm/credit-applications-hub` and `deploy/docker` for local Docker Desktop deployment | Production-grade hardening (ingress, certs, HPA, secrets manager integration) remains | `DX5` (DONE baseline for local) |
| PRD acceptance: frontend near-real-time updates | Backend push channel + frontend subscriber wiring | Backend websocket endpoint `/api/realtime/applications/ws` and projector/hub are implemented under `apps/backend/realtime/**`; frontend subscriber resolves and authenticates websocket URL | Expand from applications realtime to admin workflow observability channel if/when required | `DX3` (DONE for applications scope) |
| Architecture responsibility: webhooks app owns ingress/egress runtime | FastAPI webhook ingress + egress delivery service with signature verification | No webhook runtime modules implemented under `apps/webhooks/**` | Webhook runtime service implementation | `WA8`, `WA9`, `DX2` |
| Architecture data model: Operation/SubOperation/SubOperationTrigger | Persisted workflow operation graph | `operations`, `sub_operations`, `sub_operation_triggers` ORM models + migration + graph upsert API are implemented | Deep trigger-name contract validation against runtime registry | `WA4` |
| Architecture data model: WebhookEndpoint/Event/DeliveryAttempt | Persisted webhook endpoint/event/audit models | `webhook_endpoints`, `webhook_events`, `webhook_delivery_attempts`, and replay-command persistence are implemented | Dedicated `src/applications/webhook/**` bounded-context split and runtime adapters | `WA6`, `WA8` |
| Architecture data model: WorkerJob/EventConsumption | Runtime job/idempotency persistence | `worker_jobs` + `event_consumptions` ORM models and migration are implemented; admin execution query now uses these projections | Worker consumers still need to write lifecycle transitions/checkpoints | `WA7`, `WA9` |
| Architecture topology: workflow/webhook queues/exchanges | RabbitMQ exchanges/queues for workflow+webhooks | `apps/workers/rabbitmq_topology.py` now declares `workflows.*` and `webhooks.*` exchanges and queue bindings | Queue consumers/producers for new bindings remain pending | `WA9`, `DX2` |

### Cross-Slice Dependency Backlog (Tracked Here)
| ID | Dependency | Owner Slice | Status | Notes |
|---|---|---|---|---|
| DX1 | Provider/banking-data domain + provider adapters by country | applications/provider slice | TODO | Needed to satisfy PRD provider-data goals and acceptance criteria |
| DX2 | Webhook app runtime (`apps/webhooks`) ingress/egress handlers and signature verification | webhooks slice | TODO | Required for architecture webhook responsibilities and PRD webhook acceptance |
| DX3 | Backend realtime push channel (WebSocket/SSE) + event fan-out | backend + frontend realtime slice | DONE | `/api/realtime/applications/ws` + projector/hub + frontend websocket URL/token wiring implemented |
| DX4 | Application read caching strategy and implementation | backend applications slice | DONE | Applications list read-path cache implemented with Redis + in-memory fallback |
| DX5 | Kubernetes deployment manifests for backend/frontend/workers | platform/deployment slice | DONE | Local Docker Desktop-ready Helm deployment added under `deploy/helm/credit-applications-hub` |

## Implementation Tracking

### Requirement Traceability
| Requirement | Owner Layer | Concrete Artifact(s) | Test Coverage |
|---|---|---|---|
| FR-1..FR-8 operation-user admin services | `src/auth` + backend API | `src/auth/operations_admin/**`, `apps/backend/api/users_operations/**` | unit + integration |
| FR-9..FR-18 workflow catalog and publish | `src/applications/workflow` + backend API | `src/applications/workflow/**`, `apps/backend/api/workflows/**` | unit + integration |
| FR-19..FR-28 operation graph management | `src/applications/workflow` | workflow graph commands/services/adapters | unit + integration |
| FR-29..FR-38 webhook admin and replay | `src/applications/webhook` + webhooks app + backend API | `src/applications/webhook/**`, `apps/webhooks/**`, `apps/backend/api/workflows/**` | integration + contract |
| FR-39..FR-49 async runtime/idempotency | `src/applications/execution` + workers | `src/applications/execution/**`, `apps/workers/**` | integration + resilience |
| FR-57..FR-64 external HTTP request execution contract | workflow/execution/webhook runtime | `src/applications/workflow/**`, `src/applications/execution/**`, `apps/workers/**`, `apps/webhooks/**` | integration + resilience + security |
| FR-50..FR-56 authorization/audit/security controls | auth dependencies + backend security | `apps/backend/auth/dependencies.py`, audit logger/redaction adapters | security + integration |

### Task Checklist (living tracker)
| ID | Task | Path(s) | Status | Notes |
|---|---|---|---|---|
| WA1 | Replace stub admin routers with dedicated route modules | `apps/backend/api/router.py`, `apps/backend/api/users_operations/**`, `apps/backend/api/workflows/**` | DONE | Dedicated route modules are wired with explicit permission dependencies |
| WA2 | Implement operation-user admin module | `src/auth/operations_admin/**` | DONE | Domain/application/infrastructure module implemented and wired to API |
| WA3 | Extend workflow persistence for versioned publish model | `src/applications/workflow/infrastructure/adapters/**`, migrations | DONE | Workflow versioning/publication columns and migration implemented |
| WA4 | Add operation/sub-operation/trigger ORM models and repositories | `src/applications/workflow/infrastructure/adapters/**` | IN_PROGRESS | ORM models + graph upsert repository/service + validation implemented; deeper reference validation/event-name contracts pending |
| WA5 | Implement workflow publish service and definition event | `src/applications/workflow/application/services/**`, `src/applications/workflow/domain/events.py` | DONE | Publish now emits `WorkflowDefinitionPublished` to outbox (`workflows.events`, `credit.workflow.definition.published`) |
| WA6 | Add webhook bounded module with endpoint/event/delivery models | `src/applications/webhook/**`, migrations | IN_PROGRESS | Webhook endpoint/event/attempt/replay persistence + admin mutations implemented in workflow slice; dedicated `src/applications/webhook/**` context pending |
| WA7 | Add execution bounded module (`worker_jobs`, `event_consumptions`) | `src/applications/execution/**`, migrations | IN_PROGRESS | Execution context scaffold + ORM models + migration implemented; worker lifecycle consumers still pending |
| WA8 | Implement webhook ingress/egress transport adapters | `apps/webhooks/ingress/**`, `apps/webhooks/egress/**` | TODO | Signature verify + normalized event publication |
| WA9 | Implement workers for execution and webhook delivery | `apps/workers/**` | TODO | Workflow/webhook queue bindings are declared; queue consumers with lifecycle persistence are still pending |
| WA10 | Add admin execution/read endpoints | `apps/backend/api/workflows/router.py` | DONE | `/executions` and `/webhooks/events` now support filter/sort/pagination validation and include sort metadata in response |
| WA11 | Add audit logging and redaction coverage for admin flows | backend logging and security adapters | TODO | Capture actor/correlation without secret leakage |
| WA12 | Align role-permission mapping with admin scope policy | `src/auth/authorization/infrastructure/adapters/role_permission_mapper.py`, migrations/seed data | DONE | Admin no longer inherits `applications:list_all`; RBAC integration checks enforce deny on `/api/applications/*` |
| WA13 | Add integration and security tests for admin services | `tests/auth/integration/**`, `tests/applications/integration/**` | IN_PROGRESS | Added publish-event contract, webhook/execution filter validation, and admin scope-boundary assertions |
| WA14 | Implement third-party HTTP request executor contract | `apps/workers/**`, `src/applications/execution/**`, `src/applications/webhook/**` | TODO | Enforce request rendering/auth/timeout/retry/outcome mapping rules |
| WA15 | Add contract + resilience tests for external HTTP execution | `tests/applications/integration/execution/**`, `tests/applications/integration/security/**` | TODO | Cover retry classification, idempotency headers, SSRF guardrails |
| DX1 | Implement provider/banking-data integration foundations | `src/applications/**`, migrations | TODO | Cross-slice dependency from PRD/architecture audit |
| DX2 | Implement webhook app runtime services | `apps/webhooks/**` | TODO | Cross-slice dependency from PRD/architecture audit |
| DX3 | Implement backend realtime push transport | `apps/backend/**` | DONE | `apps/backend/realtime/**` endpoint + projector lifecycle + websocket auth/role scope are wired in `apps/backend/main.py` |
| DX4 | Implement one cached read path for applications | `apps/backend/api/applications/**` | DONE | Dependencies now wrap read repository with cache adapter and configurable Redis URL/TTL |
| DX5 | Add baseline Kubernetes manifests | deployment manifests | DONE | Helm chart, jobs, and local infra manifests delivered in `deploy/` |

## Testing Strategy
- Unit:
  - Workflow publish invariants (single initial status, no terminal outgoing transitions, immutability).
  - Operation graph validators (sort order, enum validation, reference integrity).
  - Webhook replay idempotency and secret-reference validation.
  - Worker job lifecycle and event consumption deduplication.
  - External HTTP request policy classification (retryable vs non-retryable) and timeout bounds.
- Integration:
  - Admin can manage operation users and workflows with required permissions.
  - Unauthorized roles cannot access admin services.
  - Workflow publish event is emitted once and updates active country workflow.
  - Webhook ingress/egress persistence and replay endpoints operate correctly.
  - Execution list endpoints return consistent projection data.
  - `THIRD_PARTY_HTTP_REQUEST` execution propagates idempotency/correlation headers and persists attempt history.
- Contract:
  - Snapshot tests for admin API payloads and error codes.
  - Routing key and queue binding contract tests for new workflow/webhook exchanges.
  - Outbound HTTP request contract tests for template rendering and endpoint resolution.
- Security:
  - Admin attempts on `/api/applications/*` are rejected in MVP policy.
  - Secret material is never returned in webhook endpoint responses.
  - Replay endpoint rejects duplicate command ids and untrusted callers.
  - Egress protection tests block disallowed/private-network targets and redact sensitive outbound data.

## Implementation Gaps and Mitigations
| Gap/Risk | Impact | Mitigation |
|---|---|---|
| Admin mutation paths still need uniform audit hooks | Partial actor/correlation traceability on critical writes | Add centralized admin-audit instrumentation for create/update/publish/replay handlers (WA11) |
| Workflow graph reference contracts are partially validated | Runtime contract drift risk for trigger naming conventions | Extend WA4 validation with trigger/event registry checks and contract tests |
| Webhook transport app remains unimplemented | No ingress/egress runtime execution despite persisted admin config | Implement `apps/webhooks` ingress/egress adapters and worker bindings (WA8, WA9, DX2) |
| Worker lifecycle writers for `worker_jobs`/`event_consumptions` are not wired | Observability tables can remain stale under runtime load | Implement queue consumers that persist lifecycle transitions and consumption checkpoints (WA7, WA9) |
| Admin audit metadata coverage for workflow mutations is incomplete | Actor/correlation traceability gaps for compliance and incident review | Add structured audit hooks for create/update/publish/replay paths (WA11, WA13) |
| External HTTP execution contract not yet implemented | Inconsistent egress behavior and retry safety | Implement executor contract + contract/resilience/security tests (WA14, WA15) |
| Provider/banking-data integration missing | PRD end-to-end acceptance cannot be satisfied | Implement provider adapters and banking snapshot model (`DX1`) |
| Applications realtime currently uses polling projector over DB updates | Higher DB read frequency than direct event fan-out | Optimize projector to consume outbox/domain event stream once DX2/WA9 worker pipelines are fully wired |
| List cache invalidation is TTL-based only | Short-lived stale list responses after writes | Add explicit cache bust hooks on create/status-update mutations when write-side services are stabilized |
| Deployment currently targets local Docker Desktop baseline | Production rollout posture is not yet fully specified | Add production overlays (ingress TLS, managed secrets, autoscaling, observability, pod disruption budgets) on top of `deploy/` |

## Design Decisions

### Decision 1: Split admin responsibilities by bounded context ownership
- **Context**: Admin operations span auth role management and workflow governance.
- **Chosen Solution**: Keep operation-user management in `src/auth`; keep workflow/webhook/execution domains in `src/applications`.
- **Trade-off**: Cross-context composition is required in backend API wiring, but ownership boundaries stay coherent.

### Decision 2: Immutable published workflow versions
- **Context**: Runtime safety requires deterministic workflow behavior.
- **Chosen Solution**: Use draft/published versioning; published versions are immutable and replaced by newer published versions.
- **Trade-off**: Extra authoring workflow complexity, but safer rollback/audit behavior.

### Decision 3: Webhook events and delivery attempts as first-class persisted models
- **Context**: Retries, replay, and auditability require durable records.
- **Chosen Solution**: Persist endpoint configuration, normalized events, and per-attempt outcomes.
- **Trade-off**: More storage and indexing overhead, but deterministic observability and replay controls.

### Decision 4: Explicit async idempotency model per consumer/queue/message
- **Context**: At-least-once delivery semantics can create duplicate side effects.
- **Chosen Solution**: Persist `event_consumptions` with strict uniqueness and enforce idempotent handlers.
- **Trade-off**: Additional write path for every consumed message, but eliminates duplicate side-effect risk.

### Decision 5: Preserve explicit admin scope and no implicit inheritance
- **Context**: Existing auth design intent limits admin to operation-user and workflow governance.
- **Chosen Solution**: Keep admin permissions explicit and do not grant application operations unless a separate design approves it.
- **Trade-off**: Some admin support workflows may require impersonation or delegated operation accounts.

## MVP Default Decisions (Resolved)
- Permission split:
  - Use `workflows:manage` for workflow + webhook administration in MVP.
  - Do not introduce `webhooks:manage` until non-MVP policy split is explicitly approved.
- Replay abuse controls:
  - Enforce idempotent `command_id` (existing requirement).
  - Enforce per-actor/workflow replay rate limit: `10` requests/minute with burst `20`.
  - Enforce per-event cooldown: one replay command per `webhook_event_id` every `60s`.
- Execution response payload policy:
  - `GET /api/workflows/{workflow_id}/executions` returns redacted summaries only in MVP.
  - Raw request/response payload excerpts are excluded from admin API responses in MVP.

## Definition of Done
- Admin can list/create/update operation-user assignments through `/api/users/operations/*`.
- Admin can create draft workflows, manage status/transition graph, and publish active versions per country.
- Admin can configure webhook endpoints and replay failed webhook deliveries.
- `THIRD_PARTY_HTTP_REQUEST` operations execute using the documented request/timeout/retry/security contract.
- Async execution models persist job lifecycle and consumer idempotency checkpoints.
- Worker and webhook runtime flows are idempotent, retry-safe, and DLQ-aware.
- Admin policy boundaries are enforced and test-covered, including denial on `/api/applications/*` per MVP scope.
- Unit/integration/contract/security tests for admin workflow services are green.

## References
- `docs/prd-credit-applications-hub.md`
- `docs/architecture-specification.md`
- `docs/design-auth-context.md`
- `docs/design-applications-services.md`
- `docs/messaging-rule.md`
- `docs/bounded-context-structure.md`
- `AGENTS.md`
