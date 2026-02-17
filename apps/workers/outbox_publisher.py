from __future__ import annotations

import logging
import os
import time
import uuid

from apps.workers.rabbitmq_topology import RabbitMqTopologyManager
from apps.backend.database import create_session_factory
from apps.backend.settings import Settings
from src.applications.shared.infrastructure.adapters.outbox_event_publisher import (
    OutboxEventPublisher,
    RabbitMqExchangePublisher,
)

logger = logging.getLogger(__name__)


def run() -> None:
    logging.basicConfig(level=os.getenv("OUTBOX_WORKER_LOG_LEVEL", "INFO"))

    settings = Settings.from_env()
    settings.validate_required()

    if not settings.messaging_enabled:
        raise RuntimeError("MESSAGING_ENABLED must be true for outbox publisher worker")

    poll_interval_seconds = float(os.getenv("OUTBOX_POLL_INTERVAL_SECONDS", "1"))
    batch_size = int(os.getenv("OUTBOX_BATCH_SIZE", "100"))
    max_attempts = int(os.getenv("OUTBOX_MAX_ATTEMPTS", "5"))
    lock_timeout_seconds = int(os.getenv("OUTBOX_LOCK_TIMEOUT_SECONDS", "60"))
    base_retry_delay_seconds = int(os.getenv("OUTBOX_BASE_RETRY_DELAY_SECONDS", "5"))

    topology = RabbitMqTopologyManager(
        settings.messaging_url,
        exchange_type=settings.messaging_exchange_type,
    )
    topology.ensure_topology()

    session_factory = create_session_factory(settings.database_url)
    exchange_publisher = RabbitMqExchangePublisher(
        settings.messaging_url,
        exchange_type=settings.messaging_exchange_type,
    )
    outbox_publisher = OutboxEventPublisher(
        session_factory=session_factory,
        exchange_publisher=exchange_publisher,
        worker_id=f"outbox-worker-{uuid.uuid4()}",
        lock_timeout_seconds=lock_timeout_seconds,
        max_attempts=max_attempts,
        base_retry_delay_seconds=base_retry_delay_seconds,
    )

    logger.info("outbox_worker_started")
    while True:
        cycle = outbox_publisher.publish_cycle(limit=batch_size)
        if cycle.claimed_count:
            logger.info(
                "outbox_worker_cycle",
                extra={
                    "events": {
                        "claimed": cycle.claimed_count,
                        "published": cycle.published_count,
                        "retried": cycle.retried_count,
                        "failed": cycle.failed_count,
                    }
                },
            )
        else:
            time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    run()
