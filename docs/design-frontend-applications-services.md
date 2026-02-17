# Design Document: Frontend Applications Services by Role (Vue.js)

## Metadata
- **Related PRD**: `docs/prd-credit-applications-hub.md` (Phase 1: Foundation, Phase 2: Multi-country, Phase 3: Async + integration + realtime, Phase 4: Hardening)
- **Related Architecture**: `docs/architecture-specification.md`
- **Related Backend Design**: `docs/design-applications-services.md`
- **Related Auth Design**: `docs/design-auth-context.md`
- **Related Frontend Auth Design**: `docs/design-frontend-auth-routing.md`
- **Related Frontend Admin Workflow Design**: `docs/design-frontend-admin-workflow-services.md`
- **Status**: draft
- **Last Updated**: 2026-02-17
- **Author**: Engineering
- **Scope**: Frontend `/api/applications` service layer design for `customer` and `operation` roles, plus explicit no-access policy for `admin` on applications services

## Overview
This design defines frontend service behavior for applications endpoints under `/api/applications` with explicit role handling:
- `customer`: create application, list owned applications, read owned application detail.
- `operation`: list all applications, read detail, transition customer application status.
- `admin`: no `/api/applications` responsibilities; admin scope remains `users:manage_operations` and `workflows:manage`.

The design aligns with backend contracts in `docs/design-applications-services.md` and auth/permission semantics in `docs/design-auth-context.md`. Frontend guards remain UX constraints while backend authorization is authoritative.

## Context
- **Problem**: Frontend auth/routing behavior is defined, but applications service behavior per role is not yet specified.
- **Goals**:
  - Define a role-aware frontend applications service layer that maps to `/api/applications` contracts.
  - Keep all role behavior permission-driven and aligned with JWT claims.
  - Enforce explicit no-access behavior for `admin` in applications flows.
  - Standardize handling for list/detail/create/status-transition flows by role.
  - Define consistent handling for validation errors, permission denials, and concurrency conflicts.
  - Support near-real-time application/status updates in frontend state.
- **Out of scope (this slice)**:
  - Visual design of complete application pages beyond service needs.
  - Admin workflow/user-management services (covered by `docs/design-frontend-admin-workflow-services.md` and backend `/api/workflows` + `/api/users/operations` slices).
  - Backend schema/transition policy implementation details.
  - Full offline-first caching strategy.

## Functional Specifications

### Feature 1: Customer Applications Services
**User Story**: As a `customer`, I can submit and track my own applications from the frontend.  
**Acceptance Criteria**:
- Customer service can create an application via `POST /api/applications`.
- Customer service can list and read only customer-scoped applications.
- Customer service does not expose status-transition mutation actions.
- Validation errors are surfaced as field-level form errors.

**Functional Requirements**:
- FR-1: The frontend SHALL expose `createApplication`, `listApplications`, and `getApplication` methods for customer flows.
- FR-2: The frontend SHALL call `POST /api/applications` with country and applicant payload fields defined by backend contract.
- FR-3: The frontend SHALL call `GET /api/applications` with optional filters (`country`, `status`, `page`, `page_size`) and pagination metadata support.
- FR-4: The frontend SHALL treat customer list/detail views as owner-scoped and SHALL NOT include global-scope affordances.
- FR-5: The frontend SHALL map `400 VALIDATION_ERROR` responses to field-level error structures for create/edit forms.
- FR-6: The frontend SHALL not expose status-transition UI controls in customer-facing applications views.

### Feature 2: Operation Applications Services
**User Story**: As an `operation` user, I can process applications and execute valid status transitions.  
**Acceptance Criteria**:
- Operation service can list/read applications globally.
- Operation service can call status transition endpoint.
- `409 INVALID_STATUS_TRANSITION` and `409 VERSION_CONFLICT` are surfaced with actionable UI states.
- Duplicate in-flight status updates are prevented in frontend interaction flow.

**Functional Requirements**:
- FR-7: The frontend SHALL expose `listApplications`, `getApplication`, and `updateApplicationStatus` methods for operation flows.
- FR-8: The frontend SHALL call `PATCH /api/applications/{application_id}/status` using payload `{ status, reason_code, expected_version }`.
- FR-9: The frontend SHALL present transition errors with stable handling for `INVALID_STATUS_TRANSITION` and `VERSION_CONFLICT`.
- FR-10: The frontend SHALL disable repeated submit for the same status mutation while request is in flight.
- FR-11: The frontend SHALL refresh or reconcile application state after successful status transition.
- FR-12: The frontend SHALL keep operation actions scoped to status transitions only for MVP.

### Feature 3: Admin Exclusion from Applications Services
**User Story**: As an `admin`, I manage workflows and operation users, not customer applications.  
**Acceptance Criteria**:
- Admin-facing navigation does not expose applications list/detail/status-transition actions.
- If an admin directly reaches applications routes, frontend blocks access with forbidden UX.
- No admin-initiated applications requests are emitted by applications views.

**Functional Requirements**:
- FR-13: The frontend SHALL NOT expose admin applications list/read/status service methods.
- FR-14: The frontend SHALL route admin users to workflow/user-management surfaces, not applications views.
- FR-15: The frontend SHALL redirect admin access attempts to applications routes to `/forbidden`.
- FR-16: The frontend SHALL avoid emitting `/api/applications` requests from admin-only screens.

### Feature 4: Realtime and State Consistency
**User Story**: As any permitted role, I see status changes reflected quickly without manual hard reloads.  
**Acceptance Criteria**:
- Frontend subscribes to near-real-time status updates and reconciles list/detail state.
- Event replays or duplicate messages do not create duplicate UI records.
- State ordering is deterministic when updates arrive out of order.

**Functional Requirements**:
- FR-17: The frontend SHALL consume near-real-time application updates from the backend push channel defined in architecture docs.
- FR-18: The frontend SHALL reconcile updates by `application_id` and `version`.
- FR-19: The frontend SHALL ignore stale updates with lower version than current client state.
- FR-20: The frontend SHALL update visible customer/operation applications views when `ApplicationCreated` or `ApplicationStatusUpdated` related projections arrive.

### Feature 5: Security, Error Handling, and PII Safety
**User Story**: As a security stakeholder, frontend applications services avoid leaking sensitive data and handle auth failures predictably.  
**Acceptance Criteria**:
- All `/api/applications` requests include bearer auth via shared auth-aware fetch behavior.
- Auth failures follow the established flow (`401` clears/redirects, `403` forbidden UX).
- UI models avoid logging/rendering sensitive fields unnecessarily.

**Functional Requirements**:
- FR-21: The frontend SHALL use the auth-aware fetch wrapper installed in bootstrap for all applications API calls.
- FR-22: The frontend SHALL treat `401 TOKEN_INVALID|TOKEN_EXPIRED` as session-expired flow and redirect to `/login`.
- FR-23: The frontend SHALL treat `403 PERMISSION_DENIED` as forbidden UX and keep existing session state.
- FR-24: The frontend SHALL use explicit UI model mapping for application responses and SHALL NOT dump raw payloads into logs.
- FR-25: The frontend SHALL avoid rendering/storing raw sensitive fields outside explicit form contexts where required.

## Technical Design

### Architecture and Boundaries
- Applications frontend code lives under `apps/frontend/src/features/applications/`.
- Role logic is permission-driven via auth principal claims from `auth_store`.
- A shared base API client defines endpoint contracts; role-specific services compose allowed actions.
- Router guards remain in `apps/frontend/src/app/router/`; service-level role checks protect UI action exposure and command invocation paths.
- Admin flows stay outside this feature and continue under dashboard/workflow/user-management modules.

### Proposed Source Layout
```text
apps/frontend/
|-- src/
|   |-- features/
|   |   |-- applications/
|   |   |   |-- api/
|   |   |   |   `-- applications_api.ts
|   |   |   |-- model/
|   |   |   |   `-- application_types.ts
|   |   |   |-- services/
|   |   |   |   |-- customer_applications_service.ts
|   |   |   |   |-- operation_applications_service.ts
|   |   |   |   `-- applications_permission_policy.ts
|   |   |   |-- store/
|   |   |   |   `-- applications_store.ts
|   |   |   |-- realtime/
|   |   |   |   `-- applications_updates_subscriber.ts
|   |   |   |-- views/
|   |   |   |   |-- customer_applications_page.vue
|   |   |   |   |-- operation_applications_page.vue
|   |   |   |   `-- applications_forbidden_page.vue
|   |   |   `-- components/
|   |   |       |-- applications_table.vue
|   |   |       |-- create_application_form.vue
|   |   |       `-- status_transition_dialog.vue
```

### Role Capability Matrix
| Role | Required Permission(s) | Frontend Service Methods | Allowed UI Actions |
|---|---|---|---|
| `customer` | `applications:create`, `applications:list_own` | `createApplication`, `listApplications`, `getApplication` | Create, list own, read own detail |
| `operation` | `applications:list_all`, `applications:update_customer` | `listApplications`, `getApplication`, `updateApplicationStatus` | List global queue, open detail, execute status transition |
| `admin` | `users:manage_operations`, `workflows:manage` | none in applications module | No applications actions; admin uses workflow and user-management modules |

### Frontend Data Models
```ts
export type ApplicationsSupportedRole = "customer" | "operation";

export interface ApplicationSummary {
  id: string;
  country: string;
  status_code: string;
  requested_amount: number;
  created_at: string;
  updated_at: string;
  version?: number;
}

export interface ApplicationDetail extends ApplicationSummary {
  workflow_status?: {
    current_label?: string;
    is_terminal?: boolean;
  };
}

export interface ListApplicationsParams {
  country?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export interface ListApplicationsResponse {
  items: ApplicationSummary[];
  page: number;
  page_size: number;
  total: number;
}

export interface CreateApplicationRequest {
  country: string;
  full_name: string;
  identity_document: string;
  requested_amount: number;
  monthly_income: number;
}

export interface UpdateApplicationStatusRequest {
  status: string;
  reason_code?: string;
  expected_version?: number;
}

export interface ValidationFieldError {
  field: string;
  code: string;
  message: string;
}
```

### Service Interfaces
```ts
export interface CustomerApplicationsService {
  createApplication(input: CreateApplicationRequest): Promise<ApplicationSummary>;
  listApplications(params: ListApplicationsParams): Promise<ListApplicationsResponse>;
  getApplication(applicationId: string): Promise<ApplicationDetail>;
}

export interface OperationApplicationsService {
  listApplications(params: ListApplicationsParams): Promise<ListApplicationsResponse>;
  getApplication(applicationId: string): Promise<ApplicationDetail>;
  updateApplicationStatus(
    applicationId: string,
    input: UpdateApplicationStatusRequest,
  ): Promise<ApplicationSummary>;
}

export interface ApplicationsPermissionPolicy {
  canAccessApplicationsModule(role: "customer" | "operation" | "admin", permissions: string[]): boolean;
  canUpdateApplicationStatus(role: "customer" | "operation" | "admin", permissions: string[]): boolean;
}
```

### API Contracts Used by Frontend
- `POST /api/applications`
  - Request: `{ country, full_name, identity_document, requested_amount, monthly_income }`
  - Success (`201`): `{ id, country, status_code, created_at }`
  - Errors: `400 VALIDATION_ERROR`, `401 TOKEN_INVALID|TOKEN_EXPIRED|AUTH_HEADER_MISSING`, `403 PERMISSION_DENIED`
- `GET /api/applications`
  - Query: `country`, `status`, `page`, `page_size`
  - Success (`200`): paginated summary list
- `GET /api/applications/{application_id}`
  - Success (`200`): application safe-summary detail
  - Errors: `403 PERMISSION_DENIED`, `404 APPLICATION_NOT_FOUND`
- `PATCH /api/applications/{application_id}/status`
  - Request: `{ status, reason_code, expected_version }`
  - Success (`200`): `{ id, previous_status_code, status_code, updated_at, version }`
  - Errors: `403 PERMISSION_DENIED`, `404 APPLICATION_NOT_FOUND`, `409 INVALID_STATUS_TRANSITION`, `409 VERSION_CONFLICT`

### Realtime Update Integration
- Frontend subscription source: backend near-real-time push channel (WebSocket/Socket.IO-style as defined in architecture docs).
- Update reconciliation rules:
  - upsert by `application_id`;
  - apply only if incoming `version` is greater than local version;
  - keep per-role filtered views synchronized from shared store selectors.
- Failure strategy:
  - on socket disconnect, mark realtime state degraded and trigger periodic list refresh fallback.

## Implementation Tracking

### Requirement Traceability
| Requirement | Owner Layer | Concrete Artifact(s) | Test Coverage |
|---|---|---|---|
| FR-1..FR-6 customer service behavior | applications feature services/api | `apps/frontend/src/features/applications/services/customer_applications_service.ts`, `apps/frontend/src/features/applications/api/applications_api.ts`, `apps/frontend/src/features/applications/views/customer_applications_page.vue` | unit + integration |
| FR-7..FR-12 operation service behavior | applications feature services/views | `apps/frontend/src/features/applications/services/operation_applications_service.ts`, `apps/frontend/src/features/applications/components/status_transition_dialog.vue`, `apps/frontend/src/features/applications/views/operation_applications_page.vue` | unit + integration |
| FR-13..FR-16 admin exclusion and deny policy | applications policy + router guards | `apps/frontend/src/features/applications/services/applications_permission_policy.ts`, `apps/frontend/src/app/router/auth_guards.ts`, `apps/frontend/src/shared/ui/forbidden_page.vue` | unit + integration |
| FR-17..FR-20 realtime synchronization | applications store/realtime | `apps/frontend/src/features/applications/realtime/applications_updates_subscriber.ts`, `apps/frontend/src/features/applications/store/applications_store.ts` | integration + e2e |
| FR-21..FR-25 auth/error/PII controls | shared auth bootstrap + applications api mappers | `apps/frontend/src/app/bootstrap/auth_bootstrap.ts`, `apps/frontend/src/features/applications/api/applications_api.ts` | integration + security-focused tests |

### Task Checklist (living tracker)
| ID | Task | Path(s) | Status | Notes |
|---|---|---|---|---|
| FA1 | Scaffold frontend applications feature module | `apps/frontend/src/features/applications/**` | DONE | Feature structure implemented with `api`, `model`, `services`, `store`, `realtime`, `views`, and `components` |
| FA2 | Implement base `/api/applications` client and typed contracts | `apps/frontend/src/features/applications/api/applications_api.ts`, `apps/frontend/src/features/applications/model/application_types.ts` | DONE | Typed API client and error mapping implemented for validation/auth/permission/conflict paths |
| FA3 | Implement customer applications service + view wiring | `apps/frontend/src/features/applications/services/customer_applications_service.ts`, `apps/frontend/src/features/applications/views/customer_applications_page.vue` | DONE | Customer create/list/detail implemented with permission gating, filters, and pagination wiring |
| FA4 | Implement operation applications service + transition workflow | `apps/frontend/src/features/applications/services/operation_applications_service.ts`, `apps/frontend/src/features/applications/components/status_transition_dialog.vue` | DONE | Status transition workflow implemented with in-flight submit lock and actionable `409` conflict handling |
| FA5 | Implement explicit admin deny policy for applications routes/actions | `apps/frontend/src/features/applications/services/applications_permission_policy.ts`, `apps/frontend/src/app/router/auth_guards.ts` | DONE | Admin excluded from applications module, including mixed-role principals, with `/forbidden` routing |
| FA6 | Implement applications store and role-scoped selectors | `apps/frontend/src/features/applications/store/applications_store.ts` | DONE | Shared state and role-scoped loaders implemented with normalized list/detail reconciliation |
| FA7 | Integrate realtime updates and fallback refresh flow | `apps/frontend/src/features/applications/realtime/applications_updates_subscriber.ts` | DONE | Version-aware realtime reconciliation implemented with degraded-channel polling fallback |
| FA8 | Add frontend route entries for applications pages | `apps/frontend/src/app/router/index.ts`, `apps/frontend/src/app/router/auth_guards.ts` | DONE | `/applications`, `/applications/customer`, and `/applications/operation` routes with auth+permission guards implemented |
| FT1 | Add unit tests for role capability policy and services | `apps/frontend/tests/unit/applications/**` | DONE | Unit coverage added for policy gates, API mapping, status error mapping, and stale realtime event handling |
| FT2 | Add integration tests for create/list/detail/status by role | `apps/frontend/tests/integration/applications/**` | DONE | Integration coverage added for customer and operation flows plus admin deny guard behavior |
| FT3 | Add e2e tests for cross-role applications journeys | `apps/frontend/tests/e2e/applications/**` | DONE | Playwright coverage added for customer flow, operation conflict UX, admin deny, and realtime list reflection |

## Testing Strategy
- Unit:
  - Role capability checks and permission-gate helpers.
  - Request/response and error mapping for applications API client.
  - Realtime reducer behavior (upsert, stale-event ignore, version ordering).
- Integration:
  - Customer can create/list/read own applications and cannot invoke status transition actions.
  - Operation can list/read globally and execute status transitions with expected conflict handling.
  - Admin cannot access applications module routes/actions and is redirected to `/forbidden`.
  - Auth-aware fetch behavior on `/api/applications` requests (`401` and `403` handling).
- E2E:
  - Customer create-to-track flow.
  - Operation queue processing and status transition flow.
  - Admin entry into applications route is denied and redirected to `/forbidden`.
  - Realtime update reflection in open list/detail views.

## Implementation Gaps and Mitigations
| Gap/Risk | Impact | Mitigation |
|---|---|---|
| Realtime payload contract drift between backend push channel and frontend parser | Updates may be dropped or misinterpreted if event shape changes | Keep typed event adapter in `applications_updates_subscriber` and add contract assertions in integration/e2e suites |
| Polling fallback during realtime degradation can increase API traffic | Unnecessary load under prolonged websocket outages | Keep fallback interval conservative and tune with backoff when observability data is available |
| Future role-policy changes may unintentionally re-open admin applications access | Authorization/UX drift from agreed scope | Keep explicit admin-deny checks and mixed-role admin tests as release gates |
| Regression risk in conflict UX for status transitions (`409`) | Operator retries could fail without actionable guidance | Preserve conflict mapping tests and operation-flow integration/e2e assertions |
| PII exposure through future ad-hoc logging or response model changes | Security/compliance risk | Maintain explicit response allowlists and avoid logging raw application payloads in UI/service layers |

## Design Decisions

### Decision 1: Role-specific services on top of one shared applications API client
- **Context**: Endpoint contracts are shared, but allowed actions vary by role.
- **Chosen Solution**: Build one typed API client and compose role-specific service modules for allowed behavior.
- **Trade-off**: More modules/files, but clearer separation of concerns and safer role behavior.

### Decision 2: Permission-driven behavior over hardcoded role branching
- **Context**: JWT includes both roles and explicit permissions.
- **Chosen Solution**: Use permissions as final gate for action availability, with roles as UX defaults.
- **Trade-off**: Requires policy helpers in frontend, but aligns with backend authorization semantics.

### Decision 3: Admin is excluded from applications frontend services
- **Context**: Admin scope is limited to operation-user and workflow management.
- **Chosen Solution**: Do not implement admin applications service methods; deny applications routes for admin.
- **Trade-off**: Admin cannot monitor applications directly from this module and must use dedicated admin domains.

### Decision 4: Version-based state reconciliation for realtime updates
- **Context**: Async event delivery can be duplicated or out-of-order.
- **Chosen Solution**: Merge updates by `application_id` and accept only higher-version state.
- **Trade-off**: Requires version in client model, but prevents stale state regression.

## Open Questions
- None currently. Re-open if product scope changes and admin is expected to access `/api/applications`.

## Definition of Done
- Frontend has a dedicated applications feature module with typed `/api/applications` client.
- Role-specific services exist for `customer` and `operation`, with explicit admin deny policy for applications.
- Customer flow supports create/list/detail for owned applications.
- Operation flow supports global list/detail and status transitions with `409` conflict handling.
- Admin cannot access applications module routes/actions and remains scoped to workflows and operation-user management.
- Realtime updates reconcile list/detail state within seconds and handle duplicate/out-of-order updates safely.
- Unit, integration, and e2e tests for role-specific applications behavior are green.
- Implementation remains aligned with:
  - `docs/design-applications-services.md`
  - `docs/design-auth-context.md`
  - `docs/design-frontend-auth-routing.md`
  - `docs/architecture-specification.md`

## References
- `docs/prd-credit-applications-hub.md`
- `docs/architecture-specification.md`
- `docs/design-applications-services.md`
- `docs/design-auth-context.md`
- `docs/design-frontend-auth-routing.md`
- `docs/design-frontend-admin-workflow-services.md`
- `docs/bounded-context-structure.md`
- `AGENTS.md`
