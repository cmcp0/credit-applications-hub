# Local Kubernetes Deployment (Docker Desktop)

This project includes a Helm chart and Dockerfiles to run the stack locally on Docker Desktop Kubernetes.

## Prerequisites
- Docker Desktop with Kubernetes enabled
- `kubectl`
- `helm` (v3)

## Build local images
From repository root:

```bash
docker build -f deploy/docker/python.Dockerfile -t credit-applications-hub-python:local .
docker build -f deploy/docker/frontend.Dockerfile -t credit-applications-hub-frontend:local .
```

## Install / upgrade with Helm

```bash
helm upgrade --install credit-apps deploy/helm/credit-applications-hub \
  --namespace credit-apps \
  --create-namespace
```

Wait for workloads:

```bash
kubectl get pods -n credit-apps -w
```

## Access the app
Frontend is exposed as `NodePort` by default on port `30080`:

- [http://localhost:30080](http://localhost:30080)

API is routed through frontend Nginx (`/auth`, `/api`, websocket `/api/realtime/*`), so browser auth/API calls stay same-origin.

## Seeded local fixtures
A post-install Helm hook seeds local fixtures:

- Users:
  - `customer@example.com`
  - `operation@example.com`
  - `admin@example.com`
- Password for all: `P@ssw0rd123`
- Workflows include ES and CO fixtures:
  - ES: DNI verification + additional review threshold
  - CO: mocked banking provider HTTP integration + DTI evaluation workflow metadata

## Optional useful commands
RabbitMQ management UI:

```bash
kubectl port-forward -n credit-apps svc/credit-apps-credit-applications-hub-rabbitmq 15672:15672
```

Then open [http://localhost:15672](http://localhost:15672) (default `guest` / `guest`).

Backend health check:

```bash
kubectl port-forward -n credit-apps svc/credit-apps-credit-applications-hub-backend 8000:8000
curl http://localhost:8000/health
```

## Uninstall

```bash
helm uninstall credit-apps -n credit-apps
```
