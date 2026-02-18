# Design Document: Frontend Admin Workflow Services (Vue.js)

## Metadata
- **Related PRD**: `docs/prd-credit-applications-hub.md` (Phase 3: Async + integration + realtime, Phase 4: Hardening)
- **Related Architecture**: `docs/architecture-specification.md`
- **Related Backend Design**: `docs/design-admin-workflow-services.md`
- **Related Auth Design**: `docs/design-auth-context.md`
- **Related Frontend Auth Design**: `docs/design-frontend-auth-routing.md`
- **Status**: draft
- **Last Updated**: 2026-02-17
- **Author**: Engineering
- **Scope**: Frontend admin service layer and UI flows for operation-user administration, workflow governance, webhook administration, and async execution observability

## Overview
This design defines client-side behavior for admin workflow governance features in `apps/frontend`. It mirrors backend admin goals and contracts under:
- `/api/users/operations/*`
- `/api/workflows/*`

The frontend responsibilities in this slice are:
- expose admin-only workflow and operation-user tools;
- enforce permission-driven UX gates before actions are attempted;
- send typed requests aligned with backend contracts;
- surface optimistic concurrency and domain validation conflicts predictably;
- provide execution and webhook observability views for admin operations.

## Context
- **Problem**:
  - Admin frontend currently has only a placeholder dashboard page.
  - No typed client-side module exists for operation-user management, workflow graph editing, webhook inspection/replay, or execution observability.
  - Backend contracts were recently expanded; frontend specs for those contracts are missing.
- **Goals**:
  - Define implementation-ready frontend contracts for all admin workflow APIs.
  - Keep admin behavior permission-driven and aligned with backend RBAC.
  - Define client-side state and UX rules for concurrency, retries, and replay operations.
  - Keep sensitive payload handling redacted and minimal in browser state/logging.
  - Provide a concrete implementation plan and test strategy for the frontend slice.
- **Out of scope (this slice)**:
  - Backend service implementation details for admin routes and workers.
  - Customer/operation applications flows (`/api/applications/*`).
  - Provider-specific payload semantics beyond normalized workflow/webhook contracts.

## Functional Specifications

### Feature 1: Operation User Administration
**User Story**: As an `admin`, I can manage users who should have operation capabilities.  
**Acceptance Criteria**:
- Admin can list operation users with active filter and pagination.
- Admin can assign operation role to an existing user.
- Admin can enable/disable operation access for a user.
- UI surfaces deterministic conflict/not-found errors.

**Functional Requirements**:
- FR-1: The frontend SHALL expose `listOperationUsers`, `assignOperationRole`, and `setOperationAccess` service methods.
- FR-2: The frontend SHALL call `GET /api/users/operations` with filters (`active`, `page`, `page_size`) and render pagination metadata.
- FR-3: The frontend SHALL call `POST /api/users/operations` with `{ user_id }` for role assignment.
- FR-4: The frontend SHALL call `PATCH /api/users/operations/{user_id}` with `{ enabled }`.
- FR-5: The frontend SHALL map `404 USER_NOT_FOUND` and `409 ROLE_ALREADY_ASSIGNED` to actionable UI messages.
- FR-6: The frontend SHALL not display or persist sensitive auth fields outside safe response models.

### Feature 2: Workflow Catalog Administration
**User Story**: As an `admin`, I can create, filter, and publish versioned workflow definitions.  
**Acceptance Criteria**:
- Admin can list workflows by country, active, and version status.
- Admin can create draft workflow versions.
- Admin can publish a draft with concurrency guard.
- Publish conflicts are visible and recoverable in UI.

**Functional Requirements**:
- FR-7: The frontend SHALL expose `listWorkflows`, `createWorkflow`, and `publishWorkflow` service methods.
- FR-8: The frontend SHALL call `GET /api/workflows` with (`country`, `active`, `version_status`) filters.
- FR-9: The frontend SHALL call `POST /api/workflows` with statuses/transitions payload for draft creation.
- FR-10: The frontend SHALL call `POST /api/workflows/{workflow_id}/publish` with `expected_version`.
- FR-11: The frontend SHALL disable publish action when client-known workflow version status is not `DRAFT`.
- FR-12: The frontend SHALL surface `409 VERSION_CONFLICT` and `409 WORKFLOW_VALIDATION_FAILED` with retry guidance.
- FR-13: The frontend SHALL refresh workflow catalog state after successful publish.
- FR-14: The frontend SHALL preserve filter state (country/status/pagination) across navigation and refresh.

### Feature 3: Workflow Graph Authoring
**User Story**: As an `admin`, I can edit operation graphs that define runtime behavior.  
**Acceptance Criteria**:
- Admin can upsert operations, sub-operations, and triggers in one save action.
- Admin can reorder graph nodes and maintain contiguous sort order.
- Admin can author `THIRD_PARTY_HTTP_REQUEST` sub-operations with valid target references.
- UI blocks save when graph shape is invalid.

**Functional Requirements**:
- FR-15: The frontend SHALL expose a typed `upsertWorkflowGraph` method for `PUT /api/workflows/{workflow_id}/graph`.
- FR-16: The frontend SHALL send one concurrency guard on graph save (`If-Match` preferred or `expected_version`).
- FR-17: The frontend SHALL validate contiguous `sort_order` per list scope before request submit.
- FR-18: The frontend SHALL enforce `execution_type` enum values:
  - `QUERY_USE_CASE`
  - `COMMAND_USE_CASE`
  - `THIRD_PARTY_HTTP_REQUEST`
- FR-19: The frontend SHALL enforce `trigger_type` enum values:
  - `TRIGGER_EVENT`
  - `TRIGGER_COMMAND`
  - `TRIGGER_WEBHOOK_EGRESS`
- FR-20: The frontend SHALL require `target_ref` when `execution_type=THIRD_PARTY_HTTP_REQUEST`.
- FR-21: The frontend SHALL support `target_ref` formats:
  - `webhook_endpoint:{endpoint_id}`
  - `provider:{provider_code}:{event_type}` (compatibility mode)
- FR-22: The frontend SHALL map `428 PRECONDITION_REQUIRED`, `412 ETAG_MISMATCH`, and `409 VERSION_CONFLICT` to explicit stale-editor UX.
- FR-23: The frontend SHALL map `422 GRAPH_VALIDATION_ERROR` to field-level or node-level inline errors.
- FR-24: The frontend SHALL prevent graph edits in UI when workflow version status is `PUBLISHED`.

### Feature 4: Webhook Endpoint and Event Administration
**User Story**: As an `admin`, I can manage webhook endpoints and monitor delivery outcomes.  
**Acceptance Criteria**:
- Admin can create and update webhook endpoints.
- Admin can inspect webhook events with filters/pagination.
- Admin can replay failed egress events with command id.
- UI highlights terminal failures and latest attempt details.

**Functional Requirements**:
- FR-25: The frontend SHALL expose `createWebhookEndpoint`, `updateWebhookEndpoint`, `listWebhookEvents`, and `replayWebhookEvent` methods.
- FR-26: The frontend SHALL call `POST /api/workflows/{workflow_id}/webhooks/endpoints` with typed endpoint config.
- FR-27: The frontend SHALL call `GET /api/workflows/{workflow_id}/webhooks/events` with filters, pagination, and sorting.
- FR-28: The frontend SHALL call replay endpoint with `{ command_id, reason }`.
- FR-29: The frontend SHALL generate a unique `command_id` for replay requests client-side if user does not provide one.
- FR-30: The frontend SHALL render `last_attempt` summary (`attempt_no`, `response_code`, `error_code`, `next_retry_at`) when present.
- FR-31: The frontend SHALL avoid rendering secret values and only display `secret_ref` where necessary for admin context.
- FR-32: The frontend SHALL map `422 INVALID_QUERY_PARAMS` and backend filter errors to query-form feedback.
- FR-33: The frontend SHALL support replay cooldown UX for the same event (disable repeated replay action for 60 seconds after submit) and map backend throttle errors (`409 REPLAY_COOLDOWN_ACTIVE`, `429 REPLAY_RATE_LIMIT_EXCEEDED`) to actionable feedback.

### Feature 5: Execution Observability
**User Story**: As an `admin`, I can inspect async workflow execution outcomes and diagnose failures.  
**Acceptance Criteria**:
- Admin can list executions by status and correlated dimensions.
- UI shows attempt counters, last error, and relevant operation/sub-operation metadata.
- UI respects redacted payload policy.
- Filter/sort/pagination are stable and bookmarkable.

**Functional Requirements**:
- FR-34: The frontend SHALL expose `listWorkflowExecutions` method for `GET /api/workflows/{workflow_id}/executions`.
- FR-35: The frontend SHALL support filters (`status`, `application_id`, `operation_id`, `sub_operation_id`, `from`, `to`, `correlation_id`).
- FR-36: The frontend SHALL support sorting options (`updated_at`, `available_at`, `created_at`) with direction.
- FR-37: The frontend SHALL render execution status and lifecycle metadata (`attempts`, `max_attempts`, `available_at`, `locked_at`, `completed_at`).
- FR-38: The frontend SHALL render only `payload_summary` and SHALL NOT expect raw request/response payloads in MVP.
- FR-39: The frontend SHALL map `404 WORKFLOW_NOT_FOUND` and `422 INVALID_QUERY_PARAMS` to deterministic page-level states.
- FR-40: The frontend SHALL preserve selected filters/sort in URL query params for shareable diagnostics.
- FR-41: The frontend SHALL provide single-action refresh and automatic polling fallback while execution screen is active.

### Feature 6: Admin Realtime and Refresh Strategy
**User Story**: As an `admin`, I can see webhook/execution states evolve without manual hard reload loops.  
**Acceptance Criteria**:
- Admin pages refresh data automatically in bounded intervals.
- Refresh behavior avoids duplicate request storms.
- Out-of-order API responses do not regress visible state.

**Functional Requirements**:
- FR-42: The frontend SHALL poll webhook events and execution lists when their pages are focused and visible.
- FR-43: The frontend SHALL use a default polling interval of 10 seconds and pause polling on hidden tabs.
- FR-44: The frontend SHALL reconcile list data by stable row identity (`id` or `job_id`) and newest timestamp/version.
- FR-45: The frontend SHALL keep manual refresh available even when polling is enabled.
- FR-46: The frontend SHALL debounce rapid filter changes before issuing list requests.
- FR-47: The frontend SHALL be transport-agnostic so polling can be replaced by an admin realtime channel in a future iteration.

### Feature 7: Authorization, Error Handling, and Safety
**User Story**: As a security stakeholder, admin frontend surfaces are least-privilege and predictable under failures.  
**Acceptance Criteria**:
- Only authorized principals can reach admin workflow routes.
- `401` and `403` errors follow shared auth UX behavior.
- Client logs avoid sensitive payload details.

**Functional Requirements**:
- FR-48: The frontend SHALL require authenticated principal for all admin workflow routes.
- FR-49: The frontend SHALL require `users:manage_operations` for operation-user pages/actions.
- FR-50: The frontend SHALL require `workflows:manage` for workflow/webhook/execution pages/actions.
- FR-51: The frontend SHALL route unauthorized admin action attempts to `/forbidden`.
- FR-52: The frontend SHALL apply auth-aware fetch behavior and redirect to `/login` on `401 TOKEN_INVALID|TOKEN_EXPIRED`.
- FR-53: The frontend SHALL keep session and route to `/forbidden` on protected API `403` responses.
- FR-54: The frontend SHALL avoid storing full webhook payload bodies in browser persistent storage.
- FR-55: The frontend SHALL avoid emitting raw server error payloads into console logs in production mode.

## Technical Design

### Architecture and Boundaries
- Frontend admin workflow code lives in `apps/frontend/src/features/admin_workflows/`.
- Router-level auth checks remain in `apps/frontend/src/app/router/`.
- Auth/session behavior reuses `auth_store` and bootstrap logic from existing auth modules.
- Backend remains authoritative for permission and validation enforcement; frontend guards are UX pre-checks.
- New screens/components use existing frontend stack and conventions defined in current frontend design docs.

### Proposed Source Layout
```text
apps/frontend/
|-- src/
|   |-- features/
|   |   |-- admin_workflows/
|   |   |   |-- api/
|   |   |   |   |-- operation_users_api.ts
|   |   |   |   `-- workflows_admin_api.ts
|   |   |   |-- model/
|   |   |   |   `-- admin_workflow_types.ts
|   |   |   |-- services/
|   |   |   |   |-- operation_users_admin_service.ts
|   |   |   |   |-- workflow_catalog_admin_service.ts
|   |   |   |   |-- workflow_graph_admin_service.ts
|   |   |   |   |-- webhook_admin_service.ts
|   |   |   |   |-- execution_admin_service.ts
|   |   |   |   `-- admin_workflow_permission_policy.ts
|   |   |   |-- store/
|   |   |   |   `-- admin_workflows_store.ts
|   |   |   |-- views/
|   |   |   |   |-- admin_workflow_home_page.vue
|   |   |   |   |-- admin_operation_users_page.vue
|   |   |   |   |-- admin_workflows_page.vue
|   |   |   |   |-- admin_workflow_editor_page.vue
|   |   |   |   |-- admin_workflow_webhooks_page.vue
|   |   |   |   `-- admin_workflow_executions_page.vue
|   |   |   `-- components/
|   |   |       |-- operation_user_table.vue
|   |   |       |-- workflow_catalog_table.vue
|   |   |       |-- workflow_graph_editor.vue
|   |   |       |-- webhook_events_table.vue
|   |   |       `-- executions_table.vue
```

### Route Plan
- `/dashboard/admin`: admin home.
- `/dashboard/admin/operation-users`: operation-user administration.
- `/dashboard/admin/workflows`: workflow catalog list/create/publish.
- `/dashboard/admin/workflows/:workflowId/editor`: graph authoring.
- `/dashboard/admin/workflows/:workflowId/webhooks`: webhook endpoint/events/replay.
- `/dashboard/admin/workflows/:workflowId/executions`: execution observability.

Route meta rules:
- All routes require `requiresAuth=true`.
- `/dashboard/admin` route requires at least one admin-management permission (`users:manage_operations` OR `workflows:manage`).
- `operation-users` route requires permission `users:manage_operations`.
- Workflow routes require permission `workflows:manage`.

### Role Capability Matrix
| Role | Required Permission(s) | Admin Workflow Frontend Access |
|---|---|---|
| `admin` | At least one of `users:manage_operations` or `workflows:manage` for admin entry; feature pages require their specific permission | Allowed |
| `operation` | n/a | Denied (`/forbidden`) |
| `customer` | n/a | Denied (`/forbidden`) |

### Frontend Data Models
```ts
export type WorkflowVersionStatus = "DRAFT" | "PUBLISHED" | "RETIRED";
export type SubOperationExecutionType =
  | "QUERY_USE_CASE"
  | "COMMAND_USE_CASE"
  | "THIRD_PARTY_HTTP_REQUEST";
export type SubOperationTriggerType =
  | "TRIGGER_EVENT"
  | "TRIGGER_COMMAND"
  | "TRIGGER_WEBHOOK_EGRESS";
export type WebhookDirection = "INGRESS" | "EGRESS";
export type WebhookDeliveryStatus =
  | "RECEIVED"
  | "QUEUED"
  | "DELIVERED"
  | "FAILED"
  | "DEAD_LETTERED";
export type WorkflowExecutionStatus =
  | "PENDING"
  | "RUNNING"
  | "SUCCEEDED"
  | "FAILED"
  | "DEAD_LETTERED";

export interface OperationUserSummary {
  user_id: string;
  email: string;
  is_active: boolean;
  has_operation_role: boolean;
  updated_at: string;
}

export interface WorkflowSummary {
  id: string;
  country: string;
  version: number;
  version_status: WorkflowVersionStatus;
  active: boolean;
  published_at?: string | null;
}

export interface WorkflowGraphTrigger {
  id?: string;
  trigger_type: SubOperationTriggerType;
  trigger_name: string;
  payload_template: Record<string, unknown>;
  condition_expr?: string | null;
}

export interface WorkflowGraphSubOperation {
  id?: string;
  sort_order: number;
  execution_type: SubOperationExecutionType;
  target_ref: string;
  input_template: Record<string, unknown>;
  output_alias?: string | null;
  active: boolean;
  triggers: WorkflowGraphTrigger[];
}

export interface WorkflowGraphOperation {
  id?: string;
  name: string;
  sort_order: number;
  active: boolean;
  sub_operations: WorkflowGraphSubOperation[];
}

export interface UpsertWorkflowGraphRequest {
  expected_version?: number;
  operations: WorkflowGraphOperation[];
  deleted_operation_ids: string[];
  deleted_sub_operation_ids: string[];
  deleted_trigger_ids: string[];
}

export interface WebhookEventSummary {
  id: string;
  endpoint_id: string;
  provider_code: string;
  direction: WebhookDirection;
  event_type: string;
  application_id?: string | null;
  payload_hash: string;
  signature_valid?: boolean | null;
  delivery_status: WebhookDeliveryStatus;
  correlation_id: string;
  occurred_at: string;
  created_at: string;
  last_attempt?: {
    attempt_no: number;
    delivery_status: WebhookDeliveryStatus;
    response_code?: number | null;
    error_code?: string | null;
    error_message?: string | null;
    next_retry_at?: string | null;
    created_at: string;
  } | null;
}

export interface WorkflowExecutionSummary {
  job_id: string;
  workflow_id: string;
  workflow_revision: number;
  application_id?: string | null;
  status: WorkflowExecutionStatus;
  attempts: number;
  max_attempts: number;
  last_error_code?: string | null;
  last_error_message?: string | null;
  correlation_id: string;
  updated_at: string;
  created_at: string;
}
```

### Service Interfaces
```ts
export interface OperationUsersAdminService {
  listOperationUsers(params: {
    active?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<{ items: OperationUserSummary[]; page: number; page_size: number; total: number }>;
  assignOperationRole(input: { user_id: string }): Promise<{ user_id: string; assigned_role: "operation"; assigned_at: string }>;
  setOperationAccess(userId: string, input: { enabled: boolean }): Promise<{ user_id: string; enabled: boolean; updated_at: string }>;
}

export interface WorkflowCatalogAdminService {
  listWorkflows(params: {
    country?: string;
    active?: boolean;
    version_status?: WorkflowVersionStatus;
  }): Promise<{ items: WorkflowSummary[] }>;
  createWorkflow(input: Record<string, unknown>): Promise<WorkflowSummary>;
  publishWorkflow(workflowId: string, input: { expected_version: number }): Promise<WorkflowSummary>;
}

export interface WorkflowGraphAdminService {
  upsertWorkflowGraph(
    workflowId: string,
    input: UpsertWorkflowGraphRequest,
    etag?: string,
  ): Promise<{ workflow_id: string; version: number; graph_revision: number; etag: string; updated_at: string }>;
}

export interface WebhookAdminService {
  createEndpoint(workflowId: string, input: Record<string, unknown>): Promise<{ endpoint_id: string; direction: WebhookDirection; active: boolean }>;
  updateEndpoint(
    workflowId: string,
    endpointId: string,
    input: Record<string, unknown>,
  ): Promise<{ endpoint_id: string; active: boolean; updated_at: string }>;
  rotateEndpointSecret(
    workflowId: string,
    endpointId: string,
    input: { reason: string },
  ): Promise<{ endpoint_id: string; rotated_at: string }>;
  listEvents(workflowId: string, params: Record<string, string | number | boolean | undefined>): Promise<{
    items: WebhookEventSummary[];
    page: number;
    page_size: number;
    total: number;
  }>;
  replayEvent(workflowId: string, webhookEventId: string, input: { command_id: string; reason: string }): Promise<{ queued: boolean; command_id: string }>;
}

export interface ExecutionAdminService {
  listExecutions(workflowId: string, params: Record<string, string | number | undefined>): Promise<{
    items: WorkflowExecutionSummary[];
    page: number;
    page_size: number;
    total: number;
  }>;
}
```

### API Contracts Used by Frontend
- `GET /api/users/operations`
  - Query: `active`, `page`, `page_size`
  - Success (`200`): paginated operation-user summaries
- `POST /api/users/operations`
  - Request: `{ user_id }`
  - Success (`201`): assignment summary
  - Errors: `404 USER_NOT_FOUND`, `409 ROLE_ALREADY_ASSIGNED`
- `PATCH /api/users/operations/{user_id}`
  - Request: `{ enabled }`
  - Success (`200`): updated operation-access state

- `GET /api/workflows`
  - Query: `country`, `active`, `version_status`
  - Success (`200`): workflow summary list
- `POST /api/workflows`
  - Request: workflow draft payload with `statuses` and `transitions`
  - Success (`201`): created draft summary
- `PUT /api/workflows/{workflow_id}/graph`
  - Request: graph upsert payload with optimistic concurrency guard
  - Success (`200`): `{ workflow_id, version, graph_revision, etag, updated_at }`
  - Errors: `428 PRECONDITION_REQUIRED`, `412 ETAG_MISMATCH`, `409 VERSION_CONFLICT`, `422 GRAPH_VALIDATION_ERROR`
- `POST /api/workflows/{workflow_id}/publish`
  - Request: `{ expected_version }`
  - Success (`200`): published workflow summary
  - Errors: `409 VERSION_CONFLICT`, `409 WORKFLOW_VALIDATION_FAILED`

- `POST /api/workflows/{workflow_id}/webhooks/endpoints`
  - Request: endpoint configuration payload
  - Success (`201`): endpoint summary
- `PATCH /api/workflows/{workflow_id}/webhooks/endpoints/{endpoint_id}`
  - Request: endpoint activation/metadata update payload
  - Success (`200`): endpoint update summary
- `POST /api/workflows/{workflow_id}/webhooks/endpoints/{endpoint_id}/rotate-secret`
  - Request: `{ reason }`
  - Success (`200`): secret-rotation summary
- `GET /api/workflows/{workflow_id}/webhooks/events`
  - Query: filter + pagination + sorting
  - Success (`200`): paginated webhook event summaries
  - Errors: `404 WORKFLOW_NOT_FOUND`, `422 INVALID_QUERY_PARAMS`
- `POST /api/workflows/{workflow_id}/webhooks/events/{webhook_event_id}/replay`
  - Request: `{ command_id, reason }`
  - Success (`202`): `{ queued, command_id }`
  - Errors: `404 WORKFLOW_NOT_FOUND`, `404 WEBHOOK_EVENT_NOT_FOUND`, `409 REPLAY_COMMAND_DUPLICATE`, `409 REPLAY_COOLDOWN_ACTIVE`, `429 REPLAY_RATE_LIMIT_EXCEEDED`

- `GET /api/workflows/{workflow_id}/executions`
  - Query: filter + pagination + sorting
  - Success (`200`): paginated execution summaries
  - Errors: `404 WORKFLOW_NOT_FOUND`, `422 INVALID_QUERY_PARAMS`

### Client-Side Error Mapping
- `401 TOKEN_INVALID|TOKEN_EXPIRED`: clear session and route to `/login`.
- `403 PERMISSION_DENIED`: keep session and route to `/forbidden`.
- `409 VERSION_CONFLICT|WORKFLOW_VALIDATION_FAILED`: show conflict banner with reload/retry actions.
- `412 ETAG_MISMATCH` and `428 PRECONDITION_REQUIRED`: show stale editor warning and force server-state reload.
- `422 GRAPH_VALIDATION_ERROR|INVALID_QUERY_PARAMS`: map to inline field/query validation states.
- `409 REPLAY_COOLDOWN_ACTIVE`: keep replay action disabled and show cooldown timer feedback.
- `429 REPLAY_RATE_LIMIT_EXCEEDED`: show rate-limit feedback with retry guidance for replay actions.

## PRD + Architecture + Frontend Coverage Audit (Repository Snapshot: 2026-02-17)
This audit cross-checks:
- `docs/prd-credit-applications-hub.md`
- `docs/architecture-specification.md`
- `docs/design-auth-context.md`
- `docs/design-frontend-auth-routing.md`
- `docs/design-frontend-applications-services.md`
- `docs/design-admin-workflow-services.md`
against current frontend and backend repository implementation state on 2026-02-17.

### Missing Frontend Implementation Matrix
| Source Requirement | Expected Frontend Capability | Current Repository State | Missing Part | Tracking |
|---|---|---|---|---|
| Backend admin contracts: `/api/users/operations` list/assign/enable-disable | Operation-user admin page + typed API/service actions | Typed API/service + live page actions are implemented (`list`, `assign`, `enable/disable`) | Expand edge-case UX and add e2e coverage | `FAW2`, `FTW2`, `FTW3` |
| Backend admin contracts: `/api/workflows` list/create/publish + `/graph` upsert | Workflow catalog page + graph editor with concurrency handling | Catalog and JSON-based graph editor flows are implemented with conflict mapping (`409/412/428/422`) | Replace JSON textarea with dedicated graph component UX | `FAW3`, `FAW4`, `FTW2`, `FTW3` |
| Backend admin contracts: webhook endpoint/event/replay management including endpoint updates and secret rotation | Webhook admin views with endpoint CRUD-ish flows, replay action, and attempt diagnostics | Webhook admin service + page now support create/update/rotate/list/replay with cooldown UX | Add richer endpoint discovery/list UX and deeper replay diagnostics | `FAW5`, `FTW2`, `FTW3`, `FDX2` |
| Backend admin contracts: `/api/workflows/{workflow_id}/executions` observability query | Execution diagnostics page with filters/sorting/pagination and redacted rendering | Execution diagnostics page and service are implemented with filters/sort/pagination | Add deeper correlation drill-down and e2e diagnostics journey | `FAW6`, `FTW2`, `FTW3` |
| Frontend auth routing requirements: permission-aware protected routes for admin surfaces | Admin sub-routes with `requiredPermissions` metadata and guard enforcement | Admin sub-routes and permission metadata are wired | Expand route-level integration coverage beyond guard-only tests | `FTW2` |
| Frontend applications design requirement: admin should use dedicated workflow/user-management surfaces | Discoverable navigation from admin dashboard to management screens | Admin dashboard now exposes permission-aware navigation cards | Complete end-to-end journey tests from dashboard to feature actions | `FTW3` |
| Architecture + frontend auth design: new frontend screens should use `shadcn-vue` conventions | Admin workflow screens/components aligned to existing UI patterns | Implemented pages use existing UI primitives and shared shell; component extraction is still pending | Extract reusable admin workflow table/editor components | `FAW1`, `FAW4`, `FAW5`, `FAW6` |
| PRD/architecture async+integration observability objective | Admin frontend should provide near-real-time or bounded-latency observability for webhook/execution changes | Polling + visibility pause + manual refresh are implemented for webhook/execution pages | Replace polling with backend push channel when available | `FAW7`, `FDX3` |
| Frontend testing expectations for new admin capability | Unit/integration/e2e suites for admin workflow flows | Policy unit tests + guard integration tests exist | Add admin service, flow integration, and full journey e2e coverage | `FTW1`, `FTW2`, `FTW3` |
| Cross-slice integration readiness with backend admin API | Frontend can execute real integration tests against implemented admin endpoints | Frontend now wires operation-user, workflow, graph, webhook, and execution APIs with integration tests | Continue expanding e2e coverage and advanced UX behavior under failure modes | `FDX1`, `FDX2`, `FTW3` |

## Implementation Tracking

### Requirement Traceability
| Requirement | Owner Layer | Concrete Artifact(s) | Test Coverage |
|---|---|---|---|
| FR-1..FR-6 operation-user admin behavior | admin_workflows api/services/views | `apps/frontend/src/features/admin_workflows/api/operation_users_api.ts`, `apps/frontend/src/features/admin_workflows/services/operation_users_admin_service.ts`, `apps/frontend/src/features/admin_workflows/views/admin_operation_users_page.vue` | unit + integration |
| FR-7..FR-14 workflow catalog behavior | admin_workflows api/services/views | `apps/frontend/src/features/admin_workflows/api/workflows_admin_api.ts`, `apps/frontend/src/features/admin_workflows/services/workflow_catalog_admin_service.ts`, `apps/frontend/src/features/admin_workflows/views/admin_workflows_page.vue` | unit + integration |
| FR-15..FR-24 workflow graph authoring | editor view + graph service | `apps/frontend/src/features/admin_workflows/views/admin_workflow_editor_page.vue`, `apps/frontend/src/features/admin_workflows/services/workflow_graph_admin_service.ts` | unit + integration |
| FR-25..FR-33 webhook admin and replay | webhook service + views | `apps/frontend/src/features/admin_workflows/services/webhook_admin_service.ts`, `apps/frontend/src/features/admin_workflows/views/admin_workflow_webhooks_page.vue` | unit + integration |
| FR-34..FR-41 execution observability | execution service + views/store | `apps/frontend/src/features/admin_workflows/services/execution_admin_service.ts`, `apps/frontend/src/features/admin_workflows/views/admin_workflow_executions_page.vue`, `apps/frontend/src/features/admin_workflows/store/admin_workflows_store.ts` | unit + integration |
| FR-42..FR-47 refresh strategy and reconciliation | admin store + list views | `apps/frontend/src/features/admin_workflows/store/admin_workflows_store.ts`, admin list pages | integration + e2e |
| FR-48..FR-55 authz/error/safety controls | router guards + auth bootstrap + admin api layer | `apps/frontend/src/app/router/auth_guards.ts`, `apps/frontend/src/features/admin_workflows/services/admin_workflow_permission_policy.ts`, admin API adapters | integration + security-focused tests |

### Task Checklist (living tracker)
| ID | Task | Path(s) | Status | Notes |
|---|---|---|---|---|
| FAW1 | Scaffold admin workflows frontend module | `apps/frontend/src/features/admin_workflows/**` | IN_PROGRESS | Feature module is fully wired; extracting reusable sub-components remains |
| FAW2 | Add operation-user admin API + service layer | `apps/frontend/src/features/admin_workflows/api/operation_users_api.ts`, `apps/frontend/src/features/admin_workflows/services/operation_users_admin_service.ts` | DONE | Typed API/service are wired into operation-user page actions |
| FAW3 | Add workflow catalog API + service layer | `apps/frontend/src/features/admin_workflows/api/workflows_admin_api.ts`, `apps/frontend/src/features/admin_workflows/services/workflow_catalog_admin_service.ts` | DONE | Catalog list/create/publish APIs are wired with conflict-aware UX |
| FAW4 | Implement workflow graph editor models and service | `apps/frontend/src/features/admin_workflows/model/admin_workflow_types.ts`, `apps/frontend/src/features/admin_workflows/services/workflow_graph_admin_service.ts`, `apps/frontend/src/features/admin_workflows/views/admin_workflow_editor_page.vue` | IN_PROGRESS | JSON editor implements enum/order/concurrency prechecks; visual graph component still pending |
| FAW5 | Implement webhook endpoint/events/replay services and UI | `apps/frontend/src/features/admin_workflows/services/webhook_admin_service.ts`, `apps/frontend/src/features/admin_workflows/views/admin_workflow_webhooks_page.vue` | IN_PROGRESS | Endpoint create/update/rotate + event list/replay + cooldown UX implemented; richer endpoint UX pending |
| FAW6 | Implement execution observability service and page | `apps/frontend/src/features/admin_workflows/services/execution_admin_service.ts`, `apps/frontend/src/features/admin_workflows/views/admin_workflow_executions_page.vue` | DONE | Execution diagnostics filters/sort/pagination/polling are implemented |
| FAW7 | Add admin workflows shared store with polling and reconcile | `apps/frontend/src/features/admin_workflows/store/admin_workflows_store.ts` | DONE | Store now controls polling interval, selected workflow, and replay cooldown state |
| FAW8 | Wire admin routes and permission metadata | `apps/frontend/src/app/router/index.ts`, `apps/frontend/src/app/router/auth_guards.ts` | DONE | `/dashboard/admin/*` route tree is wired with role/permission metadata |
| FAW9 | Expand admin dashboard entry links/navigation | `apps/frontend/src/features/dashboards/admin_dashboard_page.vue` | DONE | Admin dashboard now includes permission-aware navigation cards |
| FTW1 | Add unit tests for admin services and error mapping | `apps/frontend/tests/unit/admin_workflows/**` | IN_PROGRESS | Added API contract/error mapping unit tests (`workflows_admin_api.spec.ts`) plus permission policy coverage |
| FTW2 | Add integration tests for route guards and admin flows | `apps/frontend/tests/integration/admin_workflows/**` | IN_PROGRESS | Added admin workflow flow integration coverage (`admin_workflows_flows.spec.ts`) in addition to guard tests |
| FTW3 | Add e2e tests for admin workflow management journeys | `apps/frontend/tests/e2e/admin_workflows/**` | TODO | Cover operation-user admin, workflow publish, replay, and execution diagnostics |

### Cross-Slice Dependencies
| ID | Dependency | Owner Slice | Status | Notes |
|---|---|---|---|---|
| FDX1 | Backend implementation of `/api/users/operations/*` | backend auth/admin | DONE | Backend list/assign/enable-disable endpoints are implemented |
| FDX2 | Backend implementation of `/api/workflows/*` admin contracts | backend workflow/admin | IN_PROGRESS | Backend list/create/publish/graph + webhook endpoint mutation/replay + filtered inspection endpoints are implemented; webhook/execution runtime transport workers remain pending |
| FDX3 | Backend realtime channel for admin observability (optional) | backend realtime | TODO | Frontend uses polling baseline until channel exists |

## Testing Strategy
- Unit:
  - Request/response adapters and error mapping for admin APIs.
  - Workflow graph client validators (sort order, enum values, target_ref format).
  - Replay cooldown logic and query-state serialization.
- Integration:
  - Admin route permission enforcement and redirects.
  - Operation-user management flow: list -> assign -> disable/enable.
  - Workflow flow: create draft -> graph save -> publish conflict handling.
  - Webhook flow: list events -> replay action state transitions.
  - Execution diagnostics flow: filters + pagination + sorting + refresh.
- E2E:
  - Admin opens dashboard and navigates to each admin workflow section.
  - Full workflow governance journey using mocked or test backend responses.
  - Permission denial behavior for non-admin or admin without required permission.

## Implementation Gaps and Mitigations
| Gap/Risk | Impact | Mitigation |
|---|---|---|
| Visual graph editor is still JSON-based | Lower usability and higher authoring error rate for non-technical admins | Replace JSON textarea with structured graph components and targeted field-level validation UX |
| Graph editor complexity can cause high regression risk | Save failures and invalid workflow definitions | Keep strict client validators, granular component tests, and server-error mapping coverage |
| Polling on admin observability pages can increase API load | Increased backend pressure in active sessions | Pause polling on hidden tabs, support manual refresh, and apply debounced query changes |
| Permission drift between frontend route metadata and backend RBAC | Inconsistent UX and unexpected 403s | Keep permission constants centralized and cover guard behavior with integration tests |
| Sensitive webhook/execution data exposure in logs/state | Security and compliance risk | Enforce response allowlists, redaction-safe models, and production log suppression for payload bodies |

## Design Decisions

### Decision 1: One admin module with service separation by capability
- **Context**: Admin workflows span users, graph governance, webhooks, and executions.
- **Chosen Solution**: Keep one `admin_workflows` feature with separate typed services and pages per capability.
- **Trade-off**: More files and setup, but clear ownership boundaries and safer incremental rollout.

### Decision 2: Permission-driven sub-route gating inside admin area
- **Context**: Admin dashboard access can be granted by either of two permissions.
- **Chosen Solution**: Enforce feature-level route checks (`users:manage_operations` vs `workflows:manage`) instead of only role checks.
- **Trade-off**: Slightly more guard complexity, but aligns exactly with backend RBAC semantics.

### Decision 3: Polling-first observability for MVP
- **Context**: Admin realtime transport contract is not implemented yet.
- **Chosen Solution**: Use bounded polling for webhook/events and execution views with explicit refresh controls.
- **Trade-off**: Not instant push updates, but predictable behavior without waiting for realtime backend work.

### Decision 4: Strict optimistic concurrency UX for graph updates
- **Context**: Workflow graph edits are high-risk and can conflict between admins.
- **Chosen Solution**: Make stale-state errors first-class in UI (`428`, `412`, `409`) and require reload/rebase actions.
- **Trade-off**: More explicit conflict UX, but prevents silent overwrite and drift.

## Open Questions
- Should admin workflow pages be grouped under `/dashboard/admin/*` or a separate `/admin/*` route tree?
- Should replay `reason` be mandatory in UI for all environments, or optional outside production?
- What polling interval should be the default in production for executions and webhook events (`10s` vs `15s`)?

## Definition of Done
- Frontend has a dedicated admin workflow feature module with typed clients for all admin endpoints defined in backend design.
- Admin can manage operation users, workflow catalog, workflow graph, webhook operations, and execution observability from UI.
- Admin sub-routes enforce permission-specific access and integrate with existing auth guard behaviors.
- Concurrency and validation conflicts for workflow graph/publish are surfaced with deterministic UX.
- Webhook replay and execution diagnostics screens are implemented with safe redacted models.
- Polling-based observability works and is covered by integration/e2e tests.
- Unit, integration, and e2e tests for admin workflow frontend flows are green.

## References
- `docs/prd-credit-applications-hub.md`
- `docs/architecture-specification.md`
- `docs/design-admin-workflow-services.md`
- `docs/design-auth-context.md`
- `docs/design-frontend-auth-routing.md`
- `docs/design-frontend-applications-services.md`
- `AGENTS.md`
