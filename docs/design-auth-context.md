# Design Document: Auth Context (FastAPI + PostgreSQL)

## Metadata
- **Related PRD**: `docs/prd-credit-applications-hub.md` (Phase 4: Hardening)
- **Status**: draft
- **Last Updated**: 2026-02-16
- **Author**: Engineering
- **Scope**: Login + Bearer authorization for private API services + RBAC + PII protection controls + public endpoint throttling

## Overview
This design defines authentication and authorization for the credit-applications-hub MVP with these required behaviors:
- `POST /auth/login` accepts `email` and `password` and returns a JWT access token.
- `/api/*` endpoints are private and require `Authorization: Bearer <token>`.
- Auth business logic is implemented under `src/auth/`.
- FastAPI transport and runtime wiring are implemented in `apps/backend/`; ORM models and repositories stay in module `src/auth/*/infrastructure/adapters/` folders.
- PII and sensitive data must be handled with least-privilege and non-exposure defaults.
- Public services are protected by rate limiting, with stricter throttling on `/auth/login`.

The document is implementation-tracking by design: it includes file-level tasks, completion criteria, and risk mitigations for known gaps in the current scaffold.

## Context
- **Problem**: No authentication or authorization slice exists yet; private API endpoints cannot be secured.
- **Goals**:
  - Add credential-based login.
  - Enforce token-based access control on private API routes.
  - Enforce role/permission access for customer, operation, and admin personas.
  - Secure handling of PII and avoid exposing sensitive data in tokens, logs, and API responses.
  - Throttle public service access to mitigate abuse and credential stuffing.
  - Preserve business logic boundaries in `src/auth/`.
  - Integrate user credential lookup against PostgreSQL via `src/auth` infrastructure adapters.
- **Out of scope (initial slice)**:
  - Signup/registration UI/API.
  - Refresh tokens and logout revocation list.
  - Custom ABAC policies beyond defined MVP RBAC matrix.
  - Cross-context schema changes in `applications` (for example adding `applications.user_id`) are deferred to a future applications design doc.

## Functional Specifications

### Feature 1: Login (`POST /auth/login`)
**User Story**: As an API client, I can exchange valid credentials for a JWT to access private endpoints.  
**Acceptance Criteria**:
- Valid email/password returns `200` with `access_token`, `token_type=bearer`, and `expires_in`.
- Invalid credentials return `401` with stable error code.
- Inactive users are rejected with `403`.

**Functional Requirements**:
- FR-1: The system SHALL normalize login email (trim + lowercase) before lookup.
- FR-2: The system SHALL verify password using a secure hash comparison.
- FR-3: The system SHALL issue signed JWT access tokens with expiration.
- FR-4: The system SHALL include identity and authorization claims in the token.

### Feature 2: Authorization Guard for `/api/*`
**User Story**: As a platform owner, private API endpoints are protected from unauthenticated access.  
**Acceptance Criteria**:
- Missing/invalid token on `/api/*` returns `401`.
- Expired token on `/api/*` returns `401`.
- Authenticated requests that fail permission checks return `403 PERMISSION_DENIED`.
- Valid token grants access and exposes authenticated principal to handlers.

**Functional Requirements**:
- FR-5: The system SHALL validate `Authorization: Bearer <token>` on all `/api/*` routes.
- FR-6: The system SHALL reject tokens with invalid signature, issuer, audience, or expiration.
- FR-7: The system SHALL map JWT claims to an authenticated principal object available in route dependencies.

### Feature 3: Role- and Permission-based Access Control
**User Story**: As a platform owner, each persona can only access the operations allowed for its role.  
**Acceptance Criteria**:
- `customer` can create applications and list only their own applications.
- `operation` can list all applications and transition customer application status.
- `admin` can manage operation users and workflows.

**Functional Requirements**:
- FR-8: The system SHALL enforce explicit permission checks for protected `/api/*` endpoints (no implicit role inheritance).
- FR-9: The system SHALL restrict `customer` list/read operations to ownership (`application.user_id == principal.user_id`) when ownership linkage exists in the applications context.
- FR-10: The system SHALL allow `operation` to list all applications and transition customer application status (status updates only; general field updates are out of scope for this slice).
- FR-11: The system SHALL allow `admin` to manage operation users and workflow resources.

### Feature 4: PII and Sensitive Data Protection
**User Story**: As a security stakeholder, PII and sensitive fields are protected against accidental exposure.  
**Acceptance Criteria**:
- API responses never expose password hashes, raw credentials, or internal secrets.
- Auth logs redact or mask sensitive values.
- JWT payload excludes unnecessary PII.

**Functional Requirements**:
- FR-12: The system SHALL never return `password_hash` or raw credentials in API responses.
- FR-13: The system SHALL redact sensitive fields in logs (`password`, `token`, `authorization`, identity document values).
- FR-14: The system SHALL minimize JWT claims to identity and authorization data required for request authorization only.

### Feature 5: Rate Limiting for Public Services (including `/auth/login`)
**User Story**: As a platform owner, public endpoints are protected from abuse while preserving normal user access.  
**Acceptance Criteria**:
- Public endpoints apply throttling and return `429` when limits are exceeded.
- `/auth/login` applies stricter limits than general public services.
- Throttling responses include retry metadata and no sensitive data.

**Functional Requirements**:
- FR-15: The system SHALL apply a rate-limiting policy to all public services, including future public endpoints.
- FR-16: The system SHALL enforce a stricter rate-limiting policy for `POST /auth/login`.
- FR-17: The system SHALL return `429 TOO_MANY_REQUESTS` with `Retry-After` for throttled requests.
- FR-18: The system SHALL implement distributed counters in Redis for consistent enforcement across replicas.
- FR-19: The system SHALL avoid raw PII in limiter keys/logs (for example hash normalized email for login keys).

## Technical Design

### Architecture and Boundaries
- `src/auth/`: authentication and authorization bounded context with `domain/`, `application/`, and `infrastructure/` layers per module.
- `apps/backend/`: FastAPI routing/controllers, dependency wiring, JWT runtime config, middleware, and process bootstrap.
- Infrastructure in `src/auth/` owns ORM models, repository adapters, and policy adapters; `apps/backend/` composes those adapters into HTTP/runtime execution.

### Proposed Source Layout
```text
src/auth/
├── authentication/
│   ├── domain/
│   │   ├── entities.py
│   │   ├── value_objects.py
│   │   └── ports/
│   │       ├── user_credentials_reader.py
│   │       ├── password_hasher.py
│   │       └── token_issuer.py
│   ├── application/
│   │   ├── dto.py
│   │   └── services/
│   │       └── login_service.py
│   └── infrastructure/
│       ├── adapters/
│       │   ├── auth_user_orm_model.py
│       │   ├── auth_user_credentials_repository.py
│       │   └── login_audit_mapper.py
│       └── services/
│           └── credential_policy_service.py
├── authorization/
│   ├── domain/
│   │   ├── entities.py
│   │   └── ports/
│   │       └── permission_policy_reader.py
│   ├── application/
│   │   └── services/
│   │       └── authorize_request_service.py
│   └── infrastructure/
│       ├── adapters/
│       │   ├── rbac_orm_models.py
│       │   ├── permission_policy_repository.py
│       │   └── role_permission_mapper.py
│       └── services/
│           └── permission_resolution_service.py
└── shared/
    └── domain/
        └── errors.py

apps/backend/
├── auth/
│   ├── router.py
│   ├── dependencies.py
│   ├── jwt_codec.py
│   └── schemas.py
├── security/
│   ├── password_hasher.py
│   └── pii_redaction.py
├── rate_limit/
│   ├── middleware.py
│   ├── policies.py
│   ├── key_builder.py
│   └── redis_storage.py
└── main.py
```

### Infrastructure Layer Definition
#### Authentication infrastructure (`src/auth/authentication/infrastructure`)
- Responsibility: auth-user ORM model mapping, credential repository implementations, and adapter-side policy support needed by authentication application services.
- Must not import FastAPI or HTTP transport/request types.
- Examples:
  - ORM model mapping for `auth_users`.
  - Credentials repository adapter for PostgreSQL auth user lookup.
  - Canonical mapping between internal auth events and audit payload contracts.
  - Password policy checks not tied to transport/runtime framework.

#### Authorization infrastructure (`src/auth/authorization/infrastructure`)
- Responsibility: RBAC ORM model mapping, permission policy repository implementations, and effective-permission resolution for authorization application services.
- Must not enforce HTTP concerns; it returns authorization decisions/reasons to caller.
- Examples:
  - ORM model mappings for `auth_roles`, `auth_permissions`, `auth_user_roles`, and `auth_role_permissions`.
  - Permission policy repository for role/permission lookups.
  - Role-to-permission mapping resolver.
  - Permission normalization and cached policy snapshots.

### Data Model (PostgreSQL)
`auth_users` table:
- `id UUID PRIMARY KEY`
- `email CITEXT UNIQUE NOT NULL`
- `password_hash TEXT NOT NULL`
- `is_active BOOLEAN NOT NULL DEFAULT TRUE`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`
- `last_login_at TIMESTAMPTZ NULL`

`auth_roles` table:
- `id UUID PRIMARY KEY`
- `code TEXT UNIQUE NOT NULL` (`customer`, `operation`, `admin`)
- `description TEXT NOT NULL`

`auth_permissions` table:
- `id UUID PRIMARY KEY`
- `code TEXT UNIQUE NOT NULL`
- `description TEXT NOT NULL`

`auth_user_roles` table:
- `user_id UUID NOT NULL REFERENCES auth_users(id)`
- `role_id UUID NOT NULL REFERENCES auth_roles(id)`
- `PRIMARY KEY (user_id, role_id)`

`auth_role_permissions` table:
- `role_id UUID NOT NULL REFERENCES auth_roles(id)`
- `permission_id UUID NOT NULL REFERENCES auth_permissions(id)`
- `PRIMARY KEY (role_id, permission_id)`

Indexes/constraints:
- Unique index on `auth_users.email`.
- Unique indexes on `auth_roles.code` and `auth_permissions.code`.
- Migration prerequisite: enable PostgreSQL CITEXT extension before creating `auth_users.email CITEXT` (`CREATE EXTENSION IF NOT EXISTS citext;`).
- Seed role and permission catalogs in migration.

### API Contracts

#### `POST /auth/login`
Request:
```json
{
  "email": "user@example.com",
  "password": "plain-text-password"
}
```

Success response (`200`):
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 3600
}
```

Error responses:
- `401 INVALID_CREDENTIALS`
- `403 USER_INACTIVE`

#### Protected routes: `/api/*`
- Required header: `Authorization: Bearer <jwt>`
- Error responses:
  - `401 AUTH_HEADER_MISSING`
  - `401 TOKEN_INVALID`
  - `401 TOKEN_EXPIRED`
  - `403 PERMISSION_DENIED`

### JWT Specification
- Algorithm: `HS256` (MVP baseline; move to asymmetric signing in hardening iteration if needed).
- Required claims:
  - `sub` (user id)
  - `roles` (array)
  - `permissions` (array)
  - `iat`
  - `exp`
  - `iss`
  - `aud`
- Config from environment:
  - `AUTH_JWT_SECRET`
  - `AUTH_JWT_ISSUER`
  - `AUTH_JWT_AUDIENCE`
  - `AUTH_JWT_TTL_SECONDS`
- MVP baseline:
  - `AUTH_JWT_TTL_SECONDS=3600` (60 minutes)
  - Shorter values (for example 900-1800) can be enabled later if security posture requires tighter sessions.

### Authorization Strategy
- Router-level dependency applied to `/api` router group.
- Dependency verifies token and returns `AuthenticatedPrincipal`.
- Endpoint dependencies enforce role/permission requirements (for example `require_permissions("applications:list_all")`).
- Failed permission checks return `403 PERMISSION_DENIED` (authenticated but unauthorized).
- Ownership filter service is mandatory for `customer` application reads/lists.

### Rate Limiter Specification
Algorithm and storage:
- Use sliding-window counters in Redis to support distributed backend replicas.
- Limiter state is externalized (no in-process memory counters).

Keying strategy:
- Public endpoints: key by route template + client IP (`rl:public:{route}:{ip}`).
- Login endpoint: dual keys for stronger protection:
  - `rl:login:ip:{ip}`
  - `rl:login:email_ip:{email_hash}:{ip}`
- `email_hash` is derived from normalized email using one-way hash with secret pepper; raw email is never stored in keys.

Default policy (configurable):
- Public services (for example `/health`, `/auth/*` except login): `120 requests / 1 minute / IP`.
- Any future public service endpoint (for example `/auth/forgot-password`) MUST be added to limiter policy at creation time, with at least the public baseline policy.
- `POST /auth/login`:
  - `10 requests / 1 minute / IP`
  - `5 requests / 5 minutes / (email_hash + IP)`

Throttle response contract:
- HTTP status: `429`
- Body:
  - `code`: `RATE_LIMIT_EXCEEDED`
  - `message`: generic throttling message (no key details)
- Headers:
  - `Retry-After`
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`

Failure behavior:
- If Redis is unavailable:
  - `POST /auth/login`: fail-closed with `503 RATE_LIMITER_UNAVAILABLE`.
  - Other public endpoints: fail-open, emit security alert and structured error log.

Configuration (environment):
- `RATE_LIMIT_ENABLED`
- `RATE_LIMIT_REDIS_URL`
- `RATE_LIMIT_PUBLIC_WINDOW_SECONDS`
- `RATE_LIMIT_PUBLIC_MAX_REQUESTS`
- `RATE_LIMIT_LOGIN_IP_WINDOW_SECONDS`
- `RATE_LIMIT_LOGIN_IP_MAX_REQUESTS`
- `RATE_LIMIT_LOGIN_EMAIL_IP_WINDOW_SECONDS`
- `RATE_LIMIT_LOGIN_EMAIL_IP_MAX_REQUESTS`
- `RATE_LIMIT_KEY_PEPPER`

### Roles and Permissions (MVP)
Permission catalog:
- `applications:create`
- `applications:list_own`
- `applications:list_all`
- `applications:update_customer`
- `users:manage_operations`
- `workflows:manage`

Role mapping:
- `customer`:
  - `applications:create`
  - `applications:list_own`
- `operation`:
  - `applications:list_all`
  - `applications:update_customer` (status transition scope only)
- `admin`:
  - `applications:list_all`
  - `users:manage_operations`
  - `workflows:manage`

Permission inheritance:
- Disabled. Each role has explicit permissions only.

Endpoint guard examples:
- `POST /api/applications` requires `applications:create`
- `GET /api/applications`:
  - `customer`: force owner filter (`owner_id = sub`)
  - `operation|admin`: allow global list
- `PATCH /api/applications/{application_id}/status`:
  - `operation`: requires `applications:update_customer`
  - `admin`: allowed only if explicitly granted `applications:update_customer`
- `PATCH /api/applications/{application_id}` (non-status fields): out of scope for `operation` in this auth slice
- `/api/users/operations/*` requires `users:manage_operations`
- `/api/workflows/*` requires `workflows:manage`

### PII and Sensitive Data Handling
Data minimization:
- Do not place email, identity document, income, or provider payload details in JWT claims.
- `POST /auth/login` response returns token metadata only.

Output protection:
- Never expose `password_hash`, secret env values, or raw authorization headers in responses.
- Default response schemas must use explicit allowlists (no ORM model auto-serialization).

Logging and observability:
- Apply redaction for `password`, `authorization`, `access_token`, identity document, and provider PII fields.
- Emit security/audit logs with masked identifiers only (for example hashed email fingerprint).
- Rate-limit logs must include only hashed key identifiers (never raw email).

Storage and transport:
- TLS required for all client/backend and inter-service traffic.
- PostgreSQL encryption-at-rest must be enabled in runtime environment.
- Credentials and JWT secret material loaded from secret manager/environment, never committed to code.

## Implementation Tracking

### Requirement Traceability
| Requirement | Owner Layer | Concrete Artifact(s) | Test Coverage |
|---|---|---|---|
| FR-1/FR-2/FR-3/FR-4 login behavior | `src/auth` + backend transport | `src/auth/authentication/application/services/login_service.py`, `src/auth/authentication/infrastructure/adapters/auth_user_orm_model.py`, `src/auth/authentication/infrastructure/adapters/auth_user_credentials_repository.py`, `apps/backend/auth/router.py` | unit + integration |
| FR-5/FR-6 bearer validation | backend auth layer + `src/auth/authorization` | `apps/backend/auth/dependencies.py`, `apps/backend/auth/jwt_codec.py`, `src/auth/authorization/application/services/authorize_request_service.py` | unit + integration |
| FR-7 principal propagation | backend dependency wiring | `apps/backend/auth/dependencies.py`, protected route examples in `/api` routers | integration |
| FR-8/FR-9/FR-10/FR-11 role & permission enforcement | `src/auth/authorization` + backend routing | `src/auth/authorization/infrastructure/adapters/rbac_orm_models.py`, `src/auth/authorization/infrastructure/adapters/permission_policy_repository.py`, `src/auth/authorization/infrastructure/services/permission_resolution_service.py`, `apps/backend/auth/dependencies.py`, `/api` routers | unit + integration |
| FR-12/FR-13/FR-14 PII/sensitive-data controls | backend security + schemas | `apps/backend/security/pii_redaction.py`, `apps/backend/auth/schemas.py`, logging config | integration + security tests |
| FR-15/FR-16/FR-17/FR-18/FR-19 public throttling + login throttling | backend middleware + redis adapter | `apps/backend/rate_limit/middleware.py`, `apps/backend/rate_limit/policies.py`, `apps/backend/rate_limit/redis_storage.py`, `apps/backend/auth/router.py` | integration + security tests |

### Task Checklist (living tracker)
| ID | Task | Path(s) | Status | Notes |
|---|---|---|---|---|
| A1 | Define auth domain/application contracts and DTOs | `src/auth/**` | TODO | Start with ports for credentials reader, token issuer, password verification |
| A2 | Implement login service business flow | `src/auth/authentication/application/services/login_service.py` | TODO | No FastAPI/ORM imports allowed |
| A3 | Implement authorization service for principal validation | `src/auth/authorization/application/services/authorize_request_service.py` | TODO | Validate claim semantics and principal mapping |
| A4 | Implement auth infrastructure layer modules | `src/auth/authentication/infrastructure/**`, `src/auth/authorization/infrastructure/**` | TODO | Framework-agnostic adapters/services only |
| B1 | Create FastAPI auth router (`POST /auth/login`) | `apps/backend/auth/router.py`, `apps/backend/auth/schemas.py` | TODO | Input/output schema validation |
| B2 | Implement JWT codec and backend auth dependencies | `apps/backend/auth/jwt_codec.py`, `apps/backend/auth/dependencies.py` | TODO | Include issuer/audience/exp checks |
| B3 | Wire `/api/*` authorization guard | `apps/backend/main.py` and API routers | TODO | Attach dependency at router include-level |
| B4 | Add authentication ORM model + credentials repository adapter | `src/auth/authentication/infrastructure/adapters/auth_user_orm_model.py`, `src/auth/authentication/infrastructure/adapters/auth_user_credentials_repository.py` | TODO | Implement email lookup + active flag |
| B5 | Add authorization RBAC ORM models/repositories | `src/auth/authorization/infrastructure/adapters/rbac_orm_models.py`, `src/auth/authorization/infrastructure/adapters/permission_policy_repository.py` | TODO | Role/permission/user-role mappings |
| B6 | Add migrations for auth + RBAC tables | migration directory (tooling to define) | TODO | Must be idempotent/reversible and include `CREATE EXTENSION IF NOT EXISTS citext;` |
| B7 | Implement PII redaction and response-field allowlists | `apps/backend/security/pii_redaction.py`, API schemas/logging config | TODO | Prevent sensitive exposure |
| B8 | Implement rate-limit middleware, policies, and Redis storage | `apps/backend/rate_limit/**` | TODO | Sliding-window enforcement and headers |
| B9 | Apply throttling policies to public routes and `/auth/login` | `apps/backend/main.py`, `apps/backend/auth/router.py` | TODO | Login uses stricter dual-key policy |
| B10 | Add test-environment auth fixture seed | `tests/auth/fixtures/**` | TODO | Seed one active user for each role (`customer`, `operation`, `admin`) to avoid login/bootstrap blockers in tests |
| T1 | Unit tests for login and authorization services | `tests/auth/unit/**` | TODO | Success + invalid + inactive + expired |
| T2 | Integration tests for login endpoint and `/api/*` guard | `tests/auth/integration/**` | TODO | Verify real dependency wiring |
| T3 | RBAC tests for customer/operation/admin scopes | `tests/auth/integration/rbac/**` | TODO | Include ownership vs global list behaviors and operation customer-status-transition authorization |
| T4 | Sensitive-data exposure tests | `tests/auth/integration/security/**` | TODO | Validate redaction and schema allowlists |
| T5 | Rate-limit behavior tests (public + login) | `tests/auth/integration/rate_limit/**` | TODO | 429 contract, retry headers, redis-outage behavior |
| O1 | Observability fields for auth flows | backend logging config | TODO | Include request id, user id, auth outcome |

## Testing Strategy
- Unit:
  - Login service: credential success/failure, inactive user, token issuance calls.
  - Authorization service: valid token principal mapping, expiry handling, issuer/audience mismatch.
  - Permission resolution: role-to-permission expansion and deny-by-default behavior.
- Integration:
  - `POST /auth/login` with seeded Postgres user.
  - Private endpoint under `/api/*` with valid and invalid bearer tokens.
  - RBAC matrix checks for `customer`, `operation`, and `admin`, including `operation` customer-status-transition authorization.
  - Ownership checks validate both list and read behavior for `customer` when `applications.user_id` linkage is available.
  - Public endpoint throttling behavior with configured limits.
  - Stricter throttling on `/auth/login` for IP and email+IP keys.
- Security checks:
  - Password hash verification only (no plaintext compare).
  - JWT tamper test (modified payload/signature) rejected.
  - Response payloads do not include `password_hash`, secrets, or raw tokens.
  - Logs redact sensitive request/response fields.
  - Rate-limiter keys/logs never include raw email.

## Implementation Gaps and Mitigations
| Gap/Risk | Impact | Mitigation |
|---|---|---|
| No backend scaffold files exist yet | Implementation drift and ad-hoc structure | Create target directories/files exactly as listed in this design before coding logic |
| No declared dependency manifests/migration tooling | Auth cannot be deployed consistently | Introduce dependency manifest + migration tool (Alembic recommended) in first implementation task |
| No initial user provisioning flow | Login impossible in fresh environment | Use deterministic role fixtures in test environments and add a bootstrap seed path for non-test environments; keep signup out-of-scope |
| Test auth principals may be missing by role | Integration tests become flaky/blocked | Add deterministic fixtures seeding one active user per role in test environments |
| Global `/api/*` guard may block public endpoints accidentally | Regressions in future routes | Keep only explicit public routers outside `/api` (e.g., `/health`, `/auth/login`) and document convention |
| JWT secret handling misconfiguration | Security vulnerability or auth outage | Enforce startup validation for required auth env vars; fail fast on missing values |
| Token revocation not in MVP | Stolen token valid until expiry | Keep short access token TTL (for example 15-60 min) and plan refresh/revocation in next iteration |
| Password hash algorithm inconsistency across environments | Login failures after deploy | Standardize on Argon2id and pin implementation library/version in dependencies |
| Excess PII in token/response/logging | Data leakage and compliance risk | Enforce claim minimization, explicit response schema allowlists, and centralized log redaction |
| Role sprawl or ambiguous permission mapping | Unauthorized access or blocked operations | Keep seeded permission catalog and deny-by-default policy checks with integration tests |
| Rate limiter misconfiguration (too strict/too lenient) | User lockout or weak abuse protection | Ship safe defaults, expose env-based tuning, and validate with load tests in staging |
| Redis limiter outage | Inconsistent abuse protection | Define deterministic fail-closed/fail-open policy by endpoint class and alert immediately |

## Design Decisions

### Decision 1: Auth business logic and repositories in `src/auth`, transport in backend
- **Context**: Requirement explicitly separates business logic from FastAPI/Postgres integration.
- **Chosen Solution**: Keep domain/application services plus ORM/repository/policy adapters in `src/auth`; keep HTTP transport/runtime wiring in `apps/backend`.
- **Trade-off**: More indirection via ports, but clear separation and higher testability.

### Decision 2: JWT access token for MVP private API protection
- **Context**: Need immediate stateless auth for `/api/*`.
- **Chosen Solution**: Issue and verify signed JWT access tokens with strict claim validation.
- **Trade-off**: No revocation list in MVP; mitigated with short TTL and future refresh-token phase.

### Decision 3: Router-level authorization dependency
- **Context**: Requirement is all `/api/*` private by default.
- **Chosen Solution**: Apply auth dependency at router group level for `/api`.
- **Trade-off**: Requires disciplined route registration but minimizes endpoint-level omissions.

### Decision 4: Permission-driven RBAC with fixed MVP role catalog
- **Context**: The system must support `customer`, `operation`, and `admin` behaviors with clear boundaries.
- **Chosen Solution**: Persist role and permission catalogs and enforce permissions at endpoint/service boundaries.
- **Trade-off**: Slightly more schema complexity than role arrays, but safer and extensible authorization semantics with strict role separation (no inheritance).

### Decision 5: Sensitive-data minimization by default
- **Context**: Secure PII handling and non-exposure were explicitly requested.
- **Chosen Solution**: Minimize JWT claims, enforce response allowlists, and apply centralized redaction.
- **Trade-off**: Additional implementation effort in schema and logging layers, with lower leakage risk.

### Decision 6: Distributed Redis-backed throttling for public endpoints
- **Context**: Public services and login require abuse protection across horizontally scaled backend instances.
- **Chosen Solution**: Use Redis sliding-window counters with policy-based per-endpoint limits and stricter dual-key login checks.
- **Trade-off**: Adds external dependency and operational complexity, but provides consistent cross-replica enforcement and mandatory protection for all public endpoints.

## Open Questions
- Ownership linkage (`applications.user_id`) enforcement implementation detail is deferred to a future applications-context design/implementation doc.

## Definition of Done
- `POST /auth/login` returns JWT for valid credentials and correct failures for invalid/inactive users.
- `/api/*` rejects missing/invalid/expired bearer tokens and accepts valid tokens.
- `customer`, `operation`, and `admin` permissions match the matrix in this document.
- Role permissions are explicit with no implicit inheritance between roles.
- Customer list/read endpoints enforce ownership filters when `applications.user_id` linkage exists.
- Operation endpoints allow global list and customer status transitions only when `applications:update_customer` is present.
- API responses and logs pass sensitive-data non-exposure checks.
- Public services are throttled and return `429` with retry metadata when limits are exceeded.
- `/auth/login` is protected by stricter dual-key throttling.
- All future public endpoints are rate-limited at creation time.
- All auth business rules and ORM/repository implementations are in `src/auth/`; backend contains transport and runtime wiring only.
- Migrations exist for auth and RBAC tables and run successfully.
- Test fixtures provide one active user per role (`customer`, `operation`, `admin`) in test environments.
- Unit + integration tests for auth path are green in CI/local test command.

## References
- `docs/prd-credit-applications-hub.md`
- `docs/architecture-specification.md`
- `docs/bounded-context-structure.md`
- `AGENTS.md`
