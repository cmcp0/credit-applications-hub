from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from apps.backend.database import create_session_factory
from apps.backend.settings import Settings
from apps.workers.rabbitmq_topology import WORKFLOWS_DLX_EXCHANGE, RabbitMqTopologyManager
from src.applications.webhook.infrastructure.adapters.webhook_runtime_repository import (
    SqlAlchemyWebhookRuntimeRepository,
)

logger = logging.getLogger(__name__)


def run() -> None:
    logging.basicConfig(level=os.getenv("WORKFLOW_PROJECTION_WORKER_LOG_LEVEL", "INFO"))

    settings = Settings.from_env()
    settings.validate_required()
    if not settings.messaging_enabled:
        raise RuntimeError("MESSAGING_ENABLED must be true for workflow projection worker")

    queue_name = os.getenv(
        "WORKFLOW_EXECUTION_PROJECTION_QUEUE",
        "backend.workflow.execution.projection.q",
    )
    prefetch_count = int(os.getenv("WORKFLOW_PROJECTION_PREFETCH", "20"))
    retry_routing_key = os.getenv(
        "WORKFLOW_PROJECTION_RETRY_ROUTING_KEY",
        "backend.workflow.execution.projection.retry",
    )

    topology = RabbitMqTopologyManager(
        settings.messaging_url,
        exchange_type=settings.messaging_exchange_type,
    )
    topology.ensure_topology()

    try:
        import pika
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError("pika is required for workflow projection worker") from exc

    session_factory = create_session_factory(settings.database_url)
    connection = pika.BlockingConnection(pika.URLParameters(settings.messaging_url))
    channel = connection.channel()
    channel.basic_qos(prefetch_count=prefetch_count)

    def handle_message(ch, method, properties, body: bytes):
        session = session_factory()
        try:
            payload = _decode_payload(body)
            repository = SqlAlchemyWebhookRuntimeRepository(session)
            message_id = str(
                getattr(properties, "message_id", None)
                or payload.get("event_id")
                or uuid.uuid4()
            )
            correlation_id = _safe_uuid(payload.get("correlation_id") or getattr(properties, "correlation_id", None))

            consumed = repository.record_event_consumption(
                consumer_name="backend.workflow.execution.projection",
                queue_name=queue_name,
                message_id=message_id,
                correlation_id=correlation_id,
                payload_hash=None,
                consumed_at=datetime.now(timezone.utc),
            )
            if consumed:
                repository.commit()
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as exc:  # pragma: no cover - runtime safety
            session.rollback()
            logger.exception(
                "workflow_projection_worker_error",
                extra={
                    "worker": {
                        "queue": queue_name,
                        "message_id": getattr(properties, "message_id", None),
                        "routing_key": getattr(method, "routing_key", None),
                        "error": str(exc),
                    }
                },
            )
            ch.basic_publish(
                exchange=WORKFLOWS_DLX_EXCHANGE,
                routing_key=retry_routing_key,
                body=body,
                properties=properties,
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
        finally:
            session.close()

    channel.basic_consume(
        queue=queue_name,
        on_message_callback=handle_message,
        auto_ack=False,
    )
    logger.info("workflow_projection_worker_started", extra={"worker": {"queue": queue_name}})
    channel.start_consuming()


def _decode_payload(raw_body: bytes) -> dict[str, Any]:
    payload = json.loads(raw_body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Projection payload must be a JSON object")
    return payload


def _safe_uuid(raw: Any) -> uuid.UUID | None:
    if raw is None:
        return None
    try:
        return uuid.UUID(str(raw).strip())
    except ValueError:
        return None


if __name__ == "__main__":
    run()

