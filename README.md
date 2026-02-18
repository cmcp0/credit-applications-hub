# Credit Applications Hub

`credit-applications-hub` is a multi-service MVP for credit application intake and workflow orchestration across countries.

It is organized with DDD + Hexagonal boundaries:
- `apps/` contains runtime entrypoints (FastAPI APIs, workers, frontend).
- `src/` contains business capabilities by bounded context.

## What Works Today

- JWT auth with RBAC (`customer`, `operation`, `admin`).
- Create/list/read/update status for credit applications.
- Country-scoped workflow/status definitions.
- Admin workflow endpoints (graph, publish, webhook endpoint config, replay hooks).
- Outbox-based event publishing to RabbitMQ.
- Async workers for workflow/webhook processing and projection.
- Near real-time application updates over WebSocket (`/api/realtime/applications/ws`).
- Frontend app (Vue 3 + Pinia + Router) with role-based dashboards.

## Stack

- Backend/Webhooks: FastAPI + SQLAlchemy
- Frontend: Vue 3 + Vite + TypeScript
- Database: PostgreSQL
- Messaging: RabbitMQ
- Cache/Rate-limit storage: Redis
- Migrations: Alembic
- Python package management: `uv` (lockfile included)

## Repo Layout

```text
apps/
  backend/       # Main API (auth, applications, workflows, users/operations)
  webhooks/      # Inbound webhook API
  workers/       # Async consumers/processors
  mock_provider/ # Local mock CO banking provider
  frontend/      # Vue frontend
src/
  applications/  # Application/workflow/execution/webhook bounded context
  auth/          # Authentication + authorization bounded context
  shared/        # Cross-context shared pieces
deploy/
  helm/          # Local Kubernetes Helm chart
  docker/        # Dockerfiles
scripts/
  seed_local_data.py
```

## Assumptions

- PostgreSQL is the system of record for transactional and workflow/runtime data.
- RabbitMQ is available for async processing; Redis is available for rate limiting and read caching.
- `MESSAGING_ENABLED=true` is required to run workers and full async flow.
- Local development targets Docker Desktop Kubernetes or local Docker containers.
- The project optimizes for MVP correctness and operability first; production hardening is incremental.

## Data Model (High Level)

Core tables are created via Alembic migrations and grouped by capability:

- Auth/RBAC:
  - `auth_users`, `auth_roles`, `auth_permissions`, `auth_user_roles`, `auth_role_permissions`
- Applications/Workflow:
  - `applications`, `application_status_history`, `workflows`, `statuses`, `status_transitions`
- Async/Reliability:
  - `outbox_events`, `worker_jobs`, `event_consumptions`
- Webhooks and workflow runtime:
  - `operations`, `sub_operations`, `sub_operation_triggers`
  - `webhook_endpoints`, `webhook_events`, `webhook_delivery_attempts`

Important relationships:

- One `application` belongs to one owner (`auth_users`) and one country workflow.
- `statuses` and `status_transitions` define allowed lifecycle transitions per workflow.
- `outbox_events` decouples DB transaction commit from broker publish.
- `worker_jobs` and `event_consumptions` enforce idempotent async handling.

## Technical Decisions

- DDD + Hexagonal structure:
  - Business logic in `src/`, transport/bootstrap in `apps/`.
- FastAPI + SQLAlchemy for backend and webhooks:
  - Keeps API and domain orchestration explicit and testable.
- PostgreSQL as primary datastore:
  - Needed for relational integrity and JSONB-capable payload storage.
- RabbitMQ topic exchanges + queue-per-consumer:
  - Supports independent retries, DLQ behavior, and worker scaling by use case.
- Outbox pattern for event publishing:
  - Reduces dual-write risk between DB and broker.
- Redis for hot-path concerns:
  - Sliding-window rate limit storage and short TTL list cache.
- Helm-based local deployment:
  - Provides local parity for multi-process runtime behavior.

## Security Considerations

- Authentication and authorization:
  - JWT tokens for API access and RBAC permission checks per route.
- Rate limiting:
  - Public and login-specific policies, with fail-closed behavior on login limiter failures.
- Sensitive data handling:
  - PII/log redaction filter for known sensitive fields (`password`, `token`, `identity_document`, etc.).
- Webhook integrity:
  - HMAC-SHA256 signature verification support for inbound webhook validation.
- Secrets management:
  - Runtime secrets are environment-driven; Helm injects secrets via Kubernetes Secret.

Production hardening to enforce outside MVP baseline:

- Secret rotation and centralized secret manager integration.
- Network policies, mTLS/TLS termination strategy, and stricter ingress controls.
- Audit retention policy and key management governance.

## Scalability and High-Volume Data Strategy

- Horizontal scaling:
  - Backend and worker processes are stateless and can scale independently.
- Queue isolation:
  - Dedicated queues per consumer/use case avoid cross-workload contention.
- Retry/DLQ control:
  - RabbitMQ topology defines retry queues and DLQs with per-queue timing controls.
- Idempotency:
  - `event_consumptions` uniqueness and `worker_jobs.idempotency_key` avoid duplicate side effects.
- Efficient read paths:
  - Short-TTL Redis list caching for applications and DB indexes on filter/access columns.

Current large-volume risks and next steps:

- Add autoscaling policies (HPA/KEDA) tied to queue depth and CPU.
- Add read-replica and partitioning strategy for growth-heavy tables.
- Add stronger observability SLOs (queue lag, retry rates, publish latency, cache hit ratio).

## Concurrency, Queues, Cache, and Webhooks Strategy

- Concurrency model:
  - Status updates require expected version checks and transition validation.
  - Async consumers are designed for at-least-once delivery with idempotent processing.
- Queue strategy:
  - Topic exchanges per domain/context (`applications`, `workflows`, `webhooks`).
  - Queues per consumer/use case (worker command/event handlers, projection consumers).
- Cache strategy:
  - Redis-backed list cache with in-memory fallback and short TTL.
  - Redis sliding-window limiter for auth/public protection.
- Webhook strategy:
  - Ingress API receives provider events, validates signature, persists runtime event.
  - Egress workers deliver/retry/replay webhook calls and record delivery attempts.
  - Webhook/admin APIs control endpoint lifecycle and replay flows.

## Task Shortcuts (Makefile)

Common shortcuts are available via `Makefile`:

```bash
make help
make k8s-preflight
make build-images
make helm-lint
make deploy-fast
make deploy
make status
make logs-backend
make logs-workers
make undeploy
```

## Local Environment (Recommended): Full Stack via Helm

This path gives you the closest thing to a full local environment (frontend + backend + webhooks + workers + postgres + redis + rabbitmq + seed jobs).

### Fast Installation (<5 minutes)

Use this installation path when setup and run must complete quickly with standard tools:

```bash
make build-images
make deploy-fast
```

What this profile does:
- Keeps `backend`, `frontend`, and `postgres`.
- Disables `workers`, `webhooks`, `mock provider`, `redis`, and `rabbitmq`.
- Keeps `migrate` + `seed` hooks enabled, so fixtures are loaded automatically.
- Uses a `5m` Helm timeout with reduced migration retry windows.
- Reinstalls the release on each `make deploy-fast` run for a clean/fast environment.
- Cleans orphaned non-fast deployments/services left from prior profile switches.

1. Prerequisites:
- Docker Desktop with Kubernetes enabled
- `kubectl`
- `helm` v3

2. Build local images from repo root:

```bash
make build-images
```

3. Install fast profile:

```bash
make deploy-fast
```

4. Wait for pods:

```bash
kubectl get pods -n credit-apps -w
```

5. Open the app:
- [http://localhost:30080](http://localhost:30080)

6. Login with seeded users (all use `P@ssw0rd123`):
- `customer@example.com`
- `operation@example.com`
- `admin@example.com`

7. Optional: expose backend API on `localhost:8000` (required for local `curl`/Swagger access):

```bash
make pf-backend
```

8. Optional checks (in another terminal):

```bash
curl http://localhost:8000/health
```

9. Teardown:

```bash
make undeploy
```

## Local Environment (Process Mode): API/Workers on Localhost

Use this when you want fast local backend iteration without Kubernetes.

1. Start infrastructure:

```bash
docker run -d --name cah-postgres \
  -e POSTGRES_DB=credit_applications_hub \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 postgres:16-alpine

docker run -d --name cah-redis \
  -p 6379:6379 redis:7-alpine

docker run -d --name cah-rabbitmq \
  -e RABBITMQ_DEFAULT_USER=guest \
  -e RABBITMQ_DEFAULT_PASS=guest \
  -p 5672:5672 -p 15672:15672 rabbitmq:3.13-management-alpine
```

2. Install Python dependencies:

```bash
uv sync --extra test
```

3. Export local env vars:

```bash
export DATABASE_URL='postgresql+psycopg://postgres:postgres@localhost:5432/credit_applications_hub'
export AUTH_JWT_SECRET='local-dev-jwt-secret'
export AUTH_JWT_ISSUER='credit-applications-hub'
export AUTH_JWT_AUDIENCE='credit-applications-hub-api'
export AUTH_JWT_TTL_SECONDS='3600'
export RATE_LIMIT_ENABLED='true'
export RATE_LIMIT_KEY_PEPPER='local-dev-rate-limit-pepper'
export RATE_LIMIT_REDIS_URL='redis://localhost:6379/0'
export APPLICATIONS_READ_CACHE_ENABLED='true'
export APPLICATIONS_READ_CACHE_REDIS_URL='redis://localhost:6379/1'
export MESSAGING_ENABLED='true'
export MESSAGING_URL='amqp://guest:guest@localhost:5672/'
export MESSAGING_EXCHANGE_TYPE='topic'
export MOCK_CO_BANK_PROVIDER_URL='http://localhost:8085/providers/co/banking-data'
```

4. Migrate and seed:

```bash
uv run alembic upgrade head
uv run python scripts/seed_local_data.py
```

5. Run APIs (separate terminals):

```bash
uv run uvicorn apps.backend.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
uv run uvicorn apps.webhooks.main:app --reload --host 0.0.0.0 --port 8001
```

```bash
uv run uvicorn apps.mock_provider.main:app --reload --host 0.0.0.0 --port 8085
```

6. Run workers (separate terminals):

```bash
uv run python -m apps.workers.outbox_publisher
uv run python -m apps.workers.status_update_command_worker
uv run python -m apps.workers.workflow_execute_worker
uv run python -m apps.workers.workflow_execution_projection_worker
uv run python -m apps.workers.webhook_ingress_normalize_worker
uv run python -m apps.workers.webhook_egress_delivery_worker
uv run python -m apps.workers.webhook_replay_worker
```

7. Smoke checks:

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8085/health
```

8. Frontend note:
- Browser end-to-end is best through the Helm path (`localhost:30080`) because it includes same-origin reverse proxying for `/auth` and `/api`.
- If you run `apps/frontend` with `npm run dev`, you are in frontend-dev mode and should wire proxy/CORS intentionally for API calls.

## Testing

Backend:

```bash
uv run pytest
```

Frontend:

```bash
cd apps/frontend
npm ci
npm run test
```

## Useful Docs

- `docs/architecture-specification.md`
- `docs/design-applications-services.md`
- `docs/design-auth-context.md`
- `docs/design-admin-workflow-services.md`
- `docs/messaging-rule.md`
- `deploy/README.md`
