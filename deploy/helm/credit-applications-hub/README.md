# credit-applications-hub Helm Chart

Installs local development stack for:
- backend API
- frontend (Nginx static + reverse proxy to backend)
- webhooks API
- workers
- mock CO bank provider
- postgres, redis, rabbitmq
- migration + fixture seed jobs

Default values are tuned for Docker Desktop local usage.
