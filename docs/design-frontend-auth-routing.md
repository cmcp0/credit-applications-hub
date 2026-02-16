# Design Document: Frontend Auth and Role-Based Dashboard Routing (Vue.js)

## Metadata
- **Related PRD**: `docs/prd-credit-applications-hub.md` (Phase 4: Hardening)
- **Related Backend Design**: `docs/design-auth-context.md`
- **Status**: draft
- **Last Updated**: 2026-02-16
- **Author**: Engineering
- **Scope**: Frontend login page, auth session handling, protected-route guards, and role-based dashboard redirects

## Overview
This design defines frontend behavior for authentication UX and post-login routing in `apps/frontend/`. It aligns with backend auth contracts and RBAC semantics already defined in `docs/design-auth-context.md`.

The frontend must:
- Render a login page that calls `POST /auth/login`.
- Store and apply bearer tokens for protected API requests.
- Redirect authenticated users to dashboard routes based on role.
- Enforce protected-route access and handle unauthorized/expired sessions predictably.

## Context
- **Problem**: Auth contracts exist, but frontend behavior for login/session/role routing is not yet specified.
- **Goals**:
  - Provide a production-usable login UX for MVP.
  - Route users to the correct dashboard by role (`customer`, `operation`, `admin`).
  - Keep frontend authorization behavior aligned with backend permission model.
  - Handle auth failures (`401`, `403`, `429`) without leaking sensitive data.
- **Out of scope (this slice)**:
  - Signup, forgot-password, MFA, SSO.
  - Role switching UI for multi-role users.
  - Non-status application edits by `operation` role.
  - Backend ownership-linkage implementation details (for example `applications.user_id` schema rollout).

## Functional Specifications

### Feature 1: Login Page (`/login`)
**User Story**: As a user, I can authenticate with email/password and enter the app.  
**Acceptance Criteria**:
- Login form includes `email` and `password` with client-side required validation.
- Submit calls `POST /auth/login` and handles loading, success, and error states.
- Success stores auth session and redirects to role dashboard.
- Error handling:
  - `401 INVALID_CREDENTIALS`: show generic invalid credentials message.
  - `403 USER_INACTIVE`: show inactive account message.
  - `429 RATE_LIMIT_EXCEEDED`: show throttling message and retry guidance.

**Functional Requirements**:
- FR-1: The UI SHALL provide email and password inputs and disable submit while request is in flight.
- FR-2: The UI SHALL never log or persist plaintext password values.
- FR-3: The UI SHALL call `POST /auth/login` using backend contract from `docs/design-auth-context.md`.
- FR-4: On success, the UI SHALL store `access_token`, `token_type`, and computed expiry metadata for session checks.

### Feature 2: Session Lifecycle and Auth Bootstrap
**User Story**: As an authenticated user, I remain logged in until token expiry or explicit logout.  
**Acceptance Criteria**:
- App restores a valid session on browser refresh.
- Expired/invalid session clears auth state and redirects to `/login`.
- Logout clears session state and redirects to `/login`.

**Functional Requirements**:
- FR-5: The frontend SHALL attach `Authorization: Bearer <token>` to `/api/*` requests when authenticated.
- FR-6: The frontend SHALL initialize auth state during app bootstrap from persisted session state.
- FR-7: The frontend SHALL reject locally expired tokens (using `exp`) before sending protected API calls.
- FR-8: On API `401 TOKEN_INVALID` or `401 TOKEN_EXPIRED`, the frontend SHALL clear session and redirect to `/login`.

### Feature 3: Role-Based Dashboard Redirection
**User Story**: As an authenticated user, I land on the dashboard relevant to my role.  
**Acceptance Criteria**:
- `customer` redirects to `/dashboard/customer`.
- `operation` redirects to `/dashboard/operation`.
- `admin` redirects to `/dashboard/admin`.
- If an authenticated principal has no supported role or no permitted dashboard route, route to `/forbidden`.
- If an authenticated user opens `/login` or `/`, redirect to the resolved dashboard route.

**Functional Requirements**:
- FR-9: The frontend SHALL derive role-based redirect target from JWT claims (`roles`) after login/bootstrap.
- FR-10: The frontend SHALL use deterministic role priority when multiple roles are present: `admin` > `operation` > `customer`.
- FR-11: The frontend SHALL treat `operation` dashboard actions as status-transition focused (aligned with backend auth scope).
- FR-15: The frontend SHALL redirect authenticated users away from `/login` and `/` to the resolved dashboard route.
- FR-18: The frontend SHALL resolve dashboard target using role priority plus required-permission checks, selecting the highest-priority permitted dashboard and routing directly to `/forbidden` when none is permitted.

### Feature 4: Protected Routes and Authorization UX
**User Story**: As a user, I can only access pages allowed for my role.  
**Acceptance Criteria**:
- Unauthenticated users accessing protected routes are redirected to `/login`.
- Authenticated users accessing disallowed dashboards (missing required permission) are redirected to `/forbidden`.
- Protected API `403` responses show forbidden UX without exposing backend internals.
- `POST /auth/login` `403 USER_INACTIVE` remains an inline login-page error and does not redirect to `/forbidden`.

**Functional Requirements**:
- FR-12: The router SHALL guard `/dashboard/*` routes and require authenticated principal state.
- FR-13: The router SHALL enforce per-dashboard required permissions from JWT `permissions` claims (aligned with backend permission checks):
  - `/dashboard/customer`: requires `applications:list_own`
  - `/dashboard/operation`: requires `applications:list_all`
  - `/dashboard/admin`: requires at least one admin-management permission (`users:manage_operations` OR `workflows:manage`)
- FR-14: The frontend SHALL expose a `/forbidden` route for authorization denials.
- FR-16: The frontend SHALL treat `403 USER_INACTIVE` from `POST /auth/login` as login-form error state and SHALL NOT route to `/forbidden`.
- FR-17: The frontend SHALL treat `403` from protected `/api/*` requests as authorization denial, keep session state, and route to `/forbidden`.

## Technical Design

### Architecture and Boundaries
- Frontend implementation lives in `apps/frontend/`.
- Backend remains the source of truth for authentication and permission decisions.
- Frontend route guards are UX constraints only; backend authorization remains authoritative.
- New screens/components must use `shadcn-vue` and existing frontend design tokens per `docs/architecture-specification.md`.

### Proposed Source Layout
```text
apps/frontend/
|-- src/
|   |-- app/
|   |   |-- router/
|   |   |   |-- index.ts
|   |   |   `-- auth_guards.ts
|   |   `-- bootstrap/
|   |       `-- auth_bootstrap.ts
|   |-- features/
|   |   |-- auth/
|   |   |   |-- api/
|   |   |   |   `-- auth_api.ts
|   |   |   |-- model/
|   |   |   |   `-- auth_types.ts
|   |   |   |-- services/
|   |   |   |   |-- token_storage.ts
|   |   |   |   `-- role_redirect.ts
|   |   |   |-- store/
|   |   |   |   `-- auth_store.ts
|   |   |   |-- views/
|   |   |   |   `-- login_page.vue
|   |   |   `-- components/
|   |   |       `-- login_form.vue
|   |   `-- dashboards/
|   |       |-- customer_dashboard_page.vue
|   |       |-- operation_dashboard_page.vue
|   |       `-- admin_dashboard_page.vue
|   `-- shared/
|       `-- ui/
|           `-- forbidden_page.vue
```

### Data Models (Frontend)
```ts
export type RoleCode = "customer" | "operation" | "admin";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface AuthPrincipal {
  sub: string;
  roles: RoleCode[];
  permissions: string[];
  exp: number;
  iss: string;
  aud: string;
}

export interface AuthSessionState {
  token: string;
  tokenType: "bearer";
  expiresAtEpochSeconds: number;
  principal: AuthPrincipal;
}
```

### AuthSessionState Construction and Retrieval
Construction on login success:
1. Read `access_token`, `token_type`, and `expires_in` from `POST /auth/login` response.
2. Decode JWT payload from `access_token`.
3. Validate required claims from backend auth contract: `sub`, `roles`, `permissions`, `exp`, `iss`, `aud`.
4. Build `AuthSessionState`:
   - `token`: `access_token`
   - `tokenType`: `token_type` (`bearer`)
   - `expiresAtEpochSeconds`: `exp` (required; treat missing `exp` as invalid session)
   - `principal`: `{ sub, roles, permissions, exp, iss, aud }`
5. Persist serialized state under a single `sessionStorage` key (for example `auth_session`).

Retrieval on app bootstrap:
1. Load serialized `auth_session` from `sessionStorage`.
2. Parse and validate shape against `AuthSessionState`.
3. If parse or shape validation fails, clear storage key and treat user as unauthenticated.
4. If `expiresAtEpochSeconds <= now`, clear storage key and treat user as unauthenticated.
5. If valid and not expired, hydrate auth store with `AuthSessionState`.

### API Contracts Used by Frontend
- `POST /auth/login`
  - Request: `{ "email": string, "password": string }`
  - Success: `{ "access_token": string, "token_type": "bearer", "expires_in": number }`
  - Errors:
    - `401 INVALID_CREDENTIALS`
    - `403 USER_INACTIVE`
    - `429 RATE_LIMIT_EXCEEDED`
- Protected APIs under `/api/*` require `Authorization: Bearer <token>`.
  - Expected auth errors include:
    - `401 TOKEN_INVALID`
    - `401 TOKEN_EXPIRED`
    - `403` (permission denied / forbidden)

### Routing and Redirect Logic
- Public routes:
  - `/login`
  - `/forbidden`
- Protected routes:
  - `/dashboard/customer`
  - `/dashboard/operation`
  - `/dashboard/admin`

Redirect algorithm:
1. Build candidate dashboard routes from roles with priority `admin` > `operation` > `customer`.
2. Filter candidates by required dashboard permissions.
3. Resolve target dashboard as the highest-priority permitted candidate; if none exists, resolve to `/forbidden`.
4. If route is `/`:
   - authenticated: redirect to resolved target.
   - unauthenticated: redirect to `/login`.
5. If route is `/login` and session is authenticated, redirect to resolved target.
6. If route is protected and session is unauthenticated, redirect to `/login`.
7. If route is protected and principal lacks required permission for that dashboard route, redirect to `/forbidden`.

### Session Storage Strategy (MVP)
- Persist session token and metadata in `sessionStorage` (not `localStorage`) for current browser session continuity.
- Keep password values in memory only during submit.
- Future hardening can migrate to cookie-based session strategy when backend supports it.

## Implementation Tracking

### Requirement Traceability
| Requirement | Owner Layer | Concrete Artifact(s) | Test Coverage |
|---|---|---|---|
| FR-1/FR-2/FR-3/FR-4 login UX and API contract | frontend auth feature | `apps/frontend/src/features/auth/views/login_page.vue`, `apps/frontend/src/features/auth/components/login_form.vue`, `apps/frontend/src/features/auth/api/auth_api.ts` | unit + integration |
| FR-5/FR-6/FR-7/FR-8 session lifecycle and token handling | frontend auth store/services | `apps/frontend/src/features/auth/store/auth_store.ts`, `apps/frontend/src/features/auth/services/token_storage.ts`, `apps/frontend/src/app/bootstrap/auth_bootstrap.ts` | unit + integration |
| FR-9/FR-10/FR-11/FR-15/FR-18 role-based redirect, permission-aware target resolution, and entry-route behavior | frontend auth services/router | `apps/frontend/src/features/auth/services/role_redirect.ts`, `apps/frontend/src/app/router/auth_guards.ts` | unit + integration |
| FR-12/FR-13/FR-14/FR-16/FR-17 protected route enforcement and 403 disambiguation | router + forbidden/login UX | `apps/frontend/src/app/router/index.ts`, `apps/frontend/src/app/router/auth_guards.ts`, `apps/frontend/src/shared/ui/forbidden_page.vue`, `apps/frontend/src/features/auth/components/login_form.vue` | integration + e2e |

### Task Checklist (living tracker)
| ID | Task | Path(s) | Status | Notes |
|---|---|---|---|---|
| F1 | Scaffold frontend auth and dashboard route modules | `apps/frontend/src/**` | DONE | Vue app baseline, auth modules, router, and dashboard shells created |
| F2 | Implement login form and submit UX | `apps/frontend/src/features/auth/components/login_form.vue`, `apps/frontend/src/features/auth/views/login_page.vue` | DONE | Required field validation, loading disable, and `401/403/429` mapping implemented |
| F3 | Implement auth API client and token decode helpers | `apps/frontend/src/features/auth/api/auth_api.ts`, `apps/frontend/src/features/auth/model/auth_types.ts` | DONE | Login contract validation + JWT claim decoding + `AuthSessionState` builder implemented |
| F4 | Implement session persistence and bootstrap | `apps/frontend/src/features/auth/store/auth_store.ts`, `apps/frontend/src/features/auth/services/token_storage.ts`, `apps/frontend/src/app/bootstrap/auth_bootstrap.ts` | DONE | `sessionStorage` key `auth_session` with shape/expiry validation and bootstrap hydration implemented |
| F5 | Implement route guards and role redirect utility | `apps/frontend/src/app/router/auth_guards.ts`, `apps/frontend/src/features/auth/services/role_redirect.ts` | DONE | Deterministic priority (`admin > operation > customer`) with permission-aware resolution implemented |
| F6 | Create role dashboard shell pages | `apps/frontend/src/features/dashboards/*.vue` | DONE | Customer/operation/admin dashboard pages and shared shell implemented |
| F7 | Add forbidden page and unauthorized handling UX | `apps/frontend/src/shared/ui/forbidden_page.vue` | DONE | `/forbidden` page implemented with authenticated/unauthenticated recovery actions |
| F8 | Wire logout behavior and auth error recovery | `apps/frontend/src/features/auth/store/auth_store.ts`, `apps/frontend/src/app/bootstrap/auth_bootstrap.ts` | DONE | Logout clears session; protected API `401` clears+redirects `/login`; protected API `403` redirects `/forbidden`; login `403 USER_INACTIVE` remains inline |
| F9 | Add root/login redirect handling | `apps/frontend/src/app/router/auth_guards.ts` | DONE | `/` and authenticated `/login` resolve via role+permission target logic |
| FT1 | Unit tests for redirect and token/session utilities | `apps/frontend/tests/unit/auth/**` | DONE | Unit coverage added for redirect priority, token/session parsing, and login form behavior |
| FT2 | Integration tests for router guards and login flows | `apps/frontend/tests/integration/auth/**` | DONE | Guard/login/401/403 disambiguation flows added |
| FT3 | E2E tests for role-based dashboard entry | `apps/frontend/tests/e2e/auth/**` | DONE | Playwright scenarios for customer/operation/admin redirects and throttled login added |

## Testing Strategy
- Unit:
  - Role-resolution utility (`admin` > `operation` > `customer`).
  - Token expiry checks and session serialization/deserialization.
  - `AuthSessionState` builder validation (required JWT claims present, invalid payload rejected).
  - Login form validation and error-state mapping.
- Integration:
  - Login success redirects to expected dashboard by role.
  - Authenticated access to `/login` and `/` redirects to expected dashboard.
  - Authenticated principal without any permitted dashboard is routed directly to `/forbidden` (no intermediate dashboard hop).
  - Protected route guard redirects unauthenticated users to `/login`.
  - Authenticated but unauthorized dashboard access (missing permission) redirects to `/forbidden`.
  - API `401` handling clears session and redirects to `/login`.
  - API `403` handling:
    - `POST /auth/login` with `403 USER_INACTIVE` shows inline login error.
    - Protected API `403` routes to `/forbidden` without clearing session.
- E2E:
  - Customer login lands on `/dashboard/customer`.
  - Operation login lands on `/dashboard/operation`.
  - Admin login lands on `/dashboard/admin`.
  - Throttled login (`429`) displays retry guidance and avoids session creation.

## Implementation Gaps and Mitigations
| Gap/Risk | Impact | Mitigation |
|---|---|---|
| Frontend app scaffold maturity and convention drift over time | Future onboarding friction if architecture diverges | Keep this design tracker and test suite as the contract for frontend auth/routing behavior |
| Backend ownership filtering is deferred to applications context | Customer dashboard data-scope assumptions may drift | Keep frontend role routing independent of ownership schema; enforce backend response-driven rendering |
| Multiple role assignment could be non-deterministic without policy | Inconsistent user landing routes | Enforce explicit role priority in `role_redirect` utility and unit tests |
| Session token storage strategy carries XSS risk | Token exposure in compromised runtime | Use `sessionStorage`, minimize token lifetime, and follow strict frontend input/output sanitization |

## Design Decisions

### Decision 1: Role-based redirect with deterministic priority
- **Context**: Backend roles are modeled as many-to-many, but frontend must choose one landing page.
- **Chosen Solution**: Route by role with deterministic priority `admin` > `operation` > `customer`.
- **Trade-off**: Users with multiple roles get a single default landing page and no role switcher in MVP.

### Decision 2: Frontend route guards for UX + backend as authorization source of truth
- **Context**: Frontend must prevent obvious misuse while backend remains authoritative.
- **Chosen Solution**: Implement strict router guards using JWT permissions (role used for landing-page resolution only) and forbidden UX, while backend remains authoritative.
- **Trade-off**: Slight duplication of permission policy in frontend for UX consistency.

### Decision 3: Session persistence in `sessionStorage` for MVP
- **Context**: Backend currently returns JWT in login response body and does not define cookie sessions.
- **Chosen Solution**: Persist bearer token/session metadata in `sessionStorage` and clear on logout/401/expiry.
- **Trade-off**: Better UX across refreshes, with known browser-session token storage risk until hardened cookie flow is introduced.

## Open Questions
- None currently. Re-open if backend token transport strategy changes (for example moving to HTTP-only cookies).

## Definition of Done
- Login page is implemented and calls `POST /auth/login` with correct request/response handling.
- Authenticated users are redirected by role:
  - `customer` -> `/dashboard/customer`
  - `operation` -> `/dashboard/operation`
  - `admin` -> `/dashboard/admin`
- Authenticated users visiting `/` or `/login` are redirected to their resolved dashboard route.
- Protected route guards enforce authentication and permission-allowed dashboards.
- `401`, `403`, and `429` are handled with stable user-facing behavior and no sensitive data leaks.
- `403 USER_INACTIVE` from login is handled inline on `/login`; protected API `403` routes to `/forbidden` without session clear.
- Session bootstrap, expiry handling, logout, and 401 auto-clear behavior are implemented.
- Frontend implementation uses `shadcn-vue` for new auth/dashboard UI components.
- Unit + integration + e2e tests for auth/routing scenarios are green.

## References
- `docs/prd-credit-applications-hub.md`
- `docs/architecture-specification.md`
- `docs/design-auth-context.md`
- `docs/bounded-context-structure.md`
- `AGENTS.md`
