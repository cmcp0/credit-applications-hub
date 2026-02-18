from __future__ import annotations

from apps.workers.webhook_egress_delivery_worker import run_worker


def run() -> None:
    run_worker(
        queue_env_name="WEBHOOK_REPLAY_QUEUE",
        queue_default="workers.webhook.egress.replay.q",
        retry_routing_env_name="WEBHOOK_REPLAY_RETRY_ROUTING_KEY",
        retry_routing_default="workers.webhook.egress.replay.retry",
        worker_name="workers.webhook.egress.replay",
    )


if __name__ == "__main__":
    run()

