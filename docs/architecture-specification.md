# Architecture Specification and Technology Stack

## Metadata
- Product: `credit-applications-hub`
- Status: Draft
- Last Updated: 2026-02-14
- Author: Engineering

## Overview
This document defines the MVP architecture and technology stack for the credit applications hub. The system is split into app-level entrypoints (`apps/`) and domain-oriented business logic (`src/`) using DDD + Hexagonal boundaries.

## Architecture Principles
- Keep transport and framework code in `apps/`.
- Keep business capabilities in bounded contexts under `src/`.
- Use domain events and async commands for cross-module/process communication.
- Prefer exchange-per-domain/context and queue-per-consumer/use-case.
- Keep consumers idempotent and safe for parallel processing.

## Application Specifications

### 1) Backend (`apps/backend`) - FastAPI
Responsibilities:
- Expose REST APIs for creating, reading, listing, and updating applications.
- Expose `POST /auth/login`, validate bearer JWT tokens on `/api/*`, and enforce RBAC/ownership checks.
- Execute synchronous validations and orchestration for immediate request flows.
- Persist source-of-truth application data in PostgreSQL.
- Publish integration events to RabbitMQ after relevant domain changes.
- Expose near-real-time update channel to frontend via WebSocket/Socket.IO-style push.

### 2) Frontend (`apps/frontend`) - Vue.js
Responsibilities:
- Provide create/list/detail/update status experiences.
- Filter lists by country and status.
- Subscribe to near-real-time updates (WebSocket/Socket.IO-style push) and refresh state within seconds.
- Show processing state transitions driven by backend events/projections.
- Use `shadcn-vue` as the main UI component library for all new frontend screens/components.
- Keep design tokens and component conventions aligned with `shadcn-vue`.
- Reference installation baseline: official `shadcn-vue` installation documentation.

### 3) Webhooks (`apps/webhooks`) - FastAPI
Responsibilities:
- Handle inbound webhooks from external providers.
- Validate signatures/authentication for inbound calls.
- Normalize payloads and publish internal events/commands.
- Subscribe to egress events when outbound webhook delivery is needed.
- Track webhook delivery attempts, retries, and dead-letter outcomes.
- Persist webhook endpoint configuration and event/audit records.

### 4) Workers (`apps/workers`) - Event Subscribers / Command Runners
Responsibilities:
- Subscribe to RabbitMQ queues per use case.
- Execute background workflows (provider sync, risk checks, notifications, status recalculation).
- Run handlers in parallel with idempotency protections.
- Emit follow-up events for downstream consumers and UI projections.
- Persist job state transitions and consumer idempotency checkpoints.

## Technology Stack
- API Framework: FastAPI (backend + webhooks)
- Frontend Framework: Vue.js
- Message Broker: RabbitMQ
- Primary Database: PostgreSQL
- Cache/Rate Control: Redis
- Auth Strategy: JWT access tokens + PostgreSQL-backed RBAC (roles and permissions)

## Data Model (Starting Point)
The diagram below uses your base classes (`Application`, `BankingData`, `Status`, `Workflow`, `Operation`, `Countries`) and adds webhook/worker plus authentication/RBAC models required for complete async and protected API flows.

```mermaid
classDiagram
  direction LR

  class Countries {
    <<enumeration>>
    BR
    MX
    CO
    CL
    PE
  }

  class Application {
    +UUID id
    +UUID user_id
    +Countries country
    +string full_name
    +string identity_document
    +decimal requested_amount
    +decimal monthly_income
    +date application_date
    +UUID current_status_id
    +datetime created_at
    +datetime updated_at
  }

  class BankingData {
    +UUID id
    +UUID application_id
    +string provider_code
    +json payload
    +datetime fetched_at
  }

  class Status {
    +UUID id
    +UUID workflow_id
    +string code
    +string label
    +bool is_terminal
    +bool is_initial
    +int sort_order
  }

  class Workflow {
    +UUID id
    +Countries country
    +bool active
    +datetime created_at
  }

  class Operation {
    +UUID id
    +UUID workflow_id
    +string name
    +int sort_order
    +bool active
  }

  class SubOperation {
    +UUID id
    +UUID operation_id
    +int sort_order
    +string execution_type
    +string target_ref
    +json input_template
    +string output_alias
  }

  class SubOperationTrigger {
    +UUID id
    +UUID sub_operation_id
    +string trigger_type
    +string trigger_name
    +json payload_template
    +string condition_expr
  }

  class OutboxEvent {
    +UUID id
    +string aggregate_type
    +UUID aggregate_id
    +string routing_key
    +json payload
    +string publish_status
    +datetime created_at
    +datetime published_at
  }

  class WorkerJob {
    +UUID id
    +UUID application_id
    +UUID operation_id
    +UUID sub_operation_id
    +string idempotency_key
    +string status
    +int attempts
    +datetime available_at
    +datetime locked_at
    +datetime completed_at
    +string error_message
  }

  class EventConsumption {
    +UUID id
    +string consumer_name
    +string queue_name
    +string message_id
    +datetime processed_at
  }

  class AuthUser {
    +UUID id
    +string email
    +string password_hash
    +bool is_active
    +datetime created_at
    +datetime updated_at
    +datetime last_login_at
  }

  class AuthRole {
    +UUID id
    +string code
    +string description
  }

  class AuthPermission {
    +UUID id
    +string code
    +string description
  }

  class AuthUserRole {
    +UUID user_id
    +UUID role_id
  }

  class AuthRolePermission {
    +UUID role_id
    +UUID permission_id
  }

  class WebhookEndpoint {
    +UUID id
    +string direction
    +string provider_code
    +string url
    +string secret_ref
    +bool active
  }

  class WebhookEvent {
    +UUID id
    +UUID endpoint_id
    +UUID application_id
    +string direction
    +string event_type
    +json payload
    +bool signature_valid
    +datetime occurred_at
  }

  class WebhookDeliveryAttempt {
    +UUID id
    +UUID webhook_event_id
    +int attempt_no
    +string delivery_status
    +int response_code
    +string response_body
    +datetime next_retry_at
    +datetime created_at
  }

  Application "1" *-- "0..*" BankingData : has
  Application "0..*" --> "1" AuthUser : owner
  Application "1" --> "1" Status : current
  Application "1" --> "1" Countries : country
  Countries "1" --> "0..1" Workflow : workflow (current invariant)
  Workflow "1" --> "1" Countries : country
  Workflow "1" *-- "1..*" Status : defines statuses
  Status "1" --> "0..*" Status : allowed_transitions
  Workflow "1" *-- "1..*" Operation : executes
  Operation "1" *-- "1..*" SubOperation : executes
  SubOperation "1" *-- "0..*" SubOperationTrigger : triggers
  OutboxEvent "0..*" --> "1" Application : for aggregate
  WorkerJob "0..*" --> "1" Application : for
  WorkerJob "0..*" --> "1" Operation : runs
  WorkerJob "0..*" --> "0..1" SubOperation : current step
  EventConsumption "0..*" --> "1" OutboxEvent : consumes
  AuthUser "1" --> "0..*" AuthUserRole : assignments
  AuthRole "1" --> "0..*" AuthUserRole : assigned_to_users
  AuthRole "1" --> "0..*" AuthRolePermission : grants
  AuthPermission "1" --> "0..*" AuthRolePermission : permission_entries
  WebhookEvent "0..*" --> "1" WebhookEndpoint : endpoint
  WebhookEvent "0..*" --> "0..1" Application : related application
  WebhookEvent "1" *-- "0..*" WebhookDeliveryAttempt : delivery attempts
  SubOperationTrigger "0..*" --> "0..*" OutboxEvent : emits event/command
  SubOperationTrigger "0..*" --> "0..*" WebhookEvent : emits egress webhook
```

### Current Invariants (MVP)
- Only one `Workflow` is allowed per country (`Countries`) value for now; no country can have more than one workflow.
- Exactly one `Status` row must have `is_initial=true` per `Workflow`.
- Multiple `Operation` rows can belong to the same `Workflow`.
- Each `Operation` can have multiple ordered `SubOperation` rows.
- `Application.country` must match the `Workflow.country` used for status resolution.
- `Application.current_status_id` is initialized from `Status(is_initial=true)` of the matched country workflow.
- Valid next statuses are defined by the `Status -> Status` `allowed_transitions` relation within the same workflow.
- Terminal statuses (`is_terminal=true`) must have zero outgoing `allowed_transitions` relations.
- `Application.user_id` is required and references `AuthUser.id` to enforce customer ownership rules.
- `AuthUser.email` is unique and case-insensitive (CITEXT).
- `AuthRole.code` and `AuthPermission.code` are unique.
- `AuthUserRole` is unique per `(user_id, role_id)`.
- `AuthRolePermission` is unique per `(role_id, permission_id)`.

### Model Clarifications
- `WebhookEndpoint.country` is required. Each endpoint is configured for exactly one country.
- `OutboxEvent` is the durable integration-event record created in the same DB transaction as domain changes; a publisher process reads pending outbox rows and sends them to RabbitMQ.
- `EventConsumption` is the consumer-side idempotency/audit record; it stores processed message IDs per consumer/queue to prevent duplicate side effects.
- `allowed_transitions` is modeled as a self-relation on `Status`; in persistence it can be represented by a join table (`status_transition`) with `from_status_id` and `to_status_id`.
- `AuthUser.password_hash` stores hashed credentials only (never plaintext); password comparison happens through dedicated auth services.
- JWT claims are minimized to identity and authorization attributes required for request authorization (`sub`, `roles`, `permissions`, `iat`, `exp`, `iss`, `aud`).
- `SubOperation.execution_type` supports the current operation types:
  - `QUERY_USE_CASE`
  - `COMMAND_USE_CASE`
  - `THIRD_PARTY_HTTP_REQUEST`
- `SubOperationTrigger` allows using prior sub-operation outputs (`output_alias`) to trigger:
  - new events (`TRIGGER_EVENT`)
  - new commands (`TRIGGER_COMMAND`)
  - webhook egress (`TRIGGER_WEBHOOK_EGRESS`)

### Ownership and Write Paths
- Backend writes: `Application`, `BankingData`, `Workflow`/`Status`/`Operation`/`SubOperation`/`SubOperationTrigger` metadata, `OutboxEvent`, and read projections.
- Auth infrastructure adapters in `src/auth` write: `AuthUser` and RBAC tables (`AuthRole`, `AuthPermission`, `AuthUserRole`, `AuthRolePermission`); `apps/backend` provides transport wiring and runtime composition.
- Workers write: `WorkerJob` and `EventConsumption`. If async logic requires status changes, workers emit commands/events and the backend application service applies the `Application` transition (single writer rule).
- Webhooks write: `WebhookEndpoint` config, `WebhookEvent`, and `WebhookDeliveryAttempt`. Webhooks do not write `Application` state directly; they publish normalized events/commands.
- Frontend reads backend projections/materialized views only (no direct table writes).

## Data and Messaging Specifications

### PostgreSQL
Use as system of record for:
- Applications
- Auth users, roles, permissions, and role assignments
- Status history / audit trail
- Provider snapshots/references
- Workflow and operation definitions
- Job correlation and idempotency metadata
- Outbox events
- Webhook endpoint/event/delivery records

Recommended patterns:
- Transaction boundaries around state changes.
- Outbox table for reliable event publication.
- Optimistic locking/version fields for race-safe status updates.
- Enforce one-workflow-per-country with a unique constraint/index on `workflow.country`.
- Enforce one-initial-status-per-workflow with a unique partial index on `status(workflow_id)` where `is_initial=true`.
- If using a join table for the self-relation, enforce unique transition edges with a unique index on `status_transition(from_status_id, to_status_id)`.
- Enforce unique user identity with a case-insensitive unique index on `auth_users.email` (CITEXT).
- Enforce unique RBAC catalogs with unique indexes on `auth_roles.code` and `auth_permissions.code`.
- Enforce unique membership/permission edges with composite primary keys:
  - `auth_user_roles(user_id, role_id)`
  - `auth_role_permissions(role_id, permission_id)`

### RabbitMQ
Use for:
- Integration events between apps and bounded contexts.
- Async commands consumed by workers.

Topology guideline:
- Exchange per domain/context (for example `applications.events`).
- Queue per consumer/use case (for example `workers.provider_sync.q`, `webhooks.egress.q`).
- Routing keys per event/command type.
- Per-queue retry, DLQ, TTL, and prefetch policies.

### Redis
Use for:
- Read-model caching for frequently queried lists/details.
- Request throttling and anti-abuse controls.
- Short-lived distributed locks/idempotency keys for workers.

## Authentication and Authorization Specifications (MVP)
### Endpoint Protection
- `POST /auth/login` accepts `email` + `password` and returns JWT access tokens for valid, active users.
- All `/api/*` endpoints require `Authorization: Bearer <token>`.
- Invalid, expired, or malformed tokens are rejected with `401`.

### JWT and Principal Model
- JWT required claims: `sub`, `roles`, `permissions`, `iat`, `exp`, `iss`, `aud`.
- Principal identity is derived from `sub` and used for ownership checks (`Application.user_id == principal.user_id`).
- Tokens must exclude unnecessary PII (for example email, identity document, income, provider payloads).

### RBAC Matrix (MVP)
Permission catalog:
- `applications:create`
- `applications:list_own`
- `applications:list_all`
- `applications:update_customer`
- `users:manage_operations`
- `workflows:manage`

Role mapping:
- `customer`: `applications:create`, `applications:list_own`
- `operation`: `applications:list_all`, `applications:update_customer`
- `admin`: `applications:list_all`, `users:manage_operations`, `workflows:manage`

Guard semantics:
- No implicit role inheritance; access is permission-driven.
- `customer` list/read operations are always owner-scoped.
- `operation` may list all applications and update customer applications through `applications:update_customer`.
- `admin` operations outside user/workflow management require explicit permission grants.

## End-to-End Flow (MVP)
1. Frontend submits application to backend.
2. Backend validates country rules, resolves initial status from `Status(is_initial=true)`, and persists application in PostgreSQL.
3. Backend persists an outbox integration event and the publisher dispatches it to RabbitMQ (event contract names/versioning are defined separately).
4. Workers consume events/commands, run async business commands, and publish follow-up events/commands.
5. Backend is the single writer for `Application` state and read projections; webhooks/workers send events/commands that backend handlers apply.
6. Frontend receives near-real-time updates and refreshes application status.

## Webhook Flows (Target MVP Design)
### Ingress (Provider -> Platform)
1. Provider sends webhook to `apps/webhooks`.
2. Webhooks app verifies signature and stores `WebhookEvent` (`direction=INGRESS`).
3. Webhooks app publishes normalized event/command to RabbitMQ.
4. Workers/backend consumers process the event; only backend application handlers update `Application`, while workers update `WorkerJob`/side-effect state.
5. Backend emits status update to frontend channel.

### Egress (Platform -> Provider)
1. Backend/workers create domain event and persist `OutboxEvent`.
2. Publisher pushes event to RabbitMQ with routing key.
3. Webhooks egress subscriber consumes event, resolves `WebhookEndpoint`, and sends request.
4. Webhooks app stores `WebhookDeliveryAttempt`; retries and DLQ are applied per queue policy.
5. Final delivery status is persisted to `WebhookEvent`/audit records.

## Cross-Cutting Requirements
- Security: `POST /auth/login`, bearer authN on `/api/*`, explicit RBAC + ownership checks, signed webhook verification, and sensitive-data minimization in tokens/logs.
- Reliability: at-least-once delivery assumptions, idempotent handlers, DLQ monitoring.
- Observability: correlation IDs, structured logs, queue/consumer metrics, tracing.
- Scalability: horizontal scale for backend/webhooks/workers; independent queue scaling.

## Suggested Initial Queue Map
- `workers.application_created.q`
- `workers.status_changed.q`
- `workers.provider_sync.q`
- `webhooks.egress_delivery.q`
- `backend.projections_refresh.q` (optional, if projection worker is separated)

## Open Decisions
- Outbox implementation details and polling/publish mechanism.
- Exact country/provider strategy contract and versioning policy.
- Redis deployment mode (single node vs highly available).
- WebSocket/Socket.IO channel fan-out strategy for multi-instance backend deployments.
- JWT key management and rotation approach beyond MVP `HS256`.
- Refresh token/revocation strategy (post-MVP).
