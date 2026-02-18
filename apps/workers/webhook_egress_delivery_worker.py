from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from apps.backend.database import create_session_factory
from apps.backend.settings import Settings
from apps.webhooks.egress.dependencies import build_egress_delivery_service
from apps.webhooks.egress.dispatcher import dispatch_egress_delivery
from apps.workers.rabbitmq_topology import WEBHOOKS_DLX_EXCHANGE, RabbitMqTopologyManager
from src.applications.webhook.application.services.egress_webhook_delivery_service import (
    EgressDeliveryCommand,
)

logger = logging.getLogger(__name__)


def run() -> None:
    run_worker(
        queue_env_name="WEBHOOK_EGRESS_DELIVERY_QUEUE",
        queue_default="workers.webhook.egress.deliver.q",
        retry_routing_env_name="WEBHOOK_EGRESS_DELIVERY_RETRY_ROUTING_KEY",
        retry_routing_default="workers.webhook.egress.deliver.retry",
        worker_name="workers.webhook.egress.delivery",
    )


def run_worker(
    *,
    queue_env_name: str,
    queue_default: str,
    retry_routing_env_name: str,
    retry_routing_default: str,
    worker_name: str,
) -> None:
    logging.basicConfig(level=os.getenv("WEBHOOK_EGRESS_WORKER_LOG_LEVEL", "INFO"))

    settings = Settings.from_env()
    settings.validate_required()
    if not settings.messaging_enabled:
        raise RuntimeError("MESSAGING_ENABLED must be true for webhook egress worker")

    queue_name = os.getenv(queue_env_name, queue_default)
    prefetch_count = int(os.getenv("WEBHOOK_EGRESS_PREFETCH", "10"))
    max_retries = int(os.getenv("WEBHOOK_EGRESS_MAX_RETRIES", "5"))
    retry_routing_key = os.getenv(retry_routing_env_name, retry_routing_default)

    topology = RabbitMqTopologyManager(
        settings.messaging_url,
        exchange_type=settings.messaging_exchange_type,
    )
    topology.ensure_topology()

    try:
        import pika
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError("pika is required for webhook egress worker") from exc

    session_factory = create_session_factory(settings.database_url)

    connection = pika.BlockingConnection(pika.URLParameters(settings.messaging_url))
    channel = connection.channel()
    channel.basic_qos(prefetch_count=prefetch_count)

    def handle_message(ch, method, properties, body: bytes):
        session = session_factory()
        try:
            payload = _decode_payload(body)
            command = _to_egress_delivery_command(
                payload=payload,
                properties=properties,
                queue_name=queue_name,
                consumer_name=worker_name,
            )
            service = build_egress_delivery_service(session)
            result = dispatch_egress_delivery(service, command=command)

            if result.retry_scheduled:
                retried_count = _extract_retry_count(properties) + 1
                if retried_count > max_retries:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return
                ch.basic_publish(
                    exchange=WEBHOOKS_DLX_EXCHANGE,
                    routing_key=retry_routing_key,
                    body=body,
                    properties=_build_retry_properties(
                        pika=pika,
                        source_properties=properties,
                        retry_count=retried_count,
                    ),
                )
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as exc:  # pragma: no cover - runtime safety
            session.rollback()
            logger.exception(
                "webhook_egress_worker_error",
                extra={
                    "worker": {
                        "queue": queue_name,
                        "message_id": getattr(properties, "message_id", None),
                        "routing_key": getattr(method, "routing_key", None),
                        "error": str(exc),
                    }
                },
            )
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        finally:
            session.close()

    channel.basic_consume(
        queue=queue_name,
        on_message_callback=handle_message,
        auto_ack=False,
    )
    logger.info("webhook_egress_worker_started", extra={"worker": {"queue": queue_name}})
    channel.start_consuming()


def _decode_payload(raw_body: bytes) -> dict[str, Any]:
    payload = json.loads(raw_body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Command payload must be a JSON object")
    return payload


def _to_egress_delivery_command(
    *,
    payload: dict[str, Any],
    properties: Any,
    queue_name: str,
    consumer_name: str,
) -> EgressDeliveryCommand:
    correlation_id = str(
        payload.get("correlation_id")
        or getattr(properties, "correlation_id", None)
        or getattr(properties, "message_id", None)
        or payload.get("request_id")
        or ""
    )
    if not correlation_id:
        raise ValueError("correlation_id is required")

    return EgressDeliveryCommand(
        workflow_id=str(payload["workflow_id"]),
        target_ref=str(payload["target_ref"]),
        input_template=dict(payload.get("input_template") or {}),
        execution_context=dict(payload.get("execution_context") or {}),
        correlation_id=correlation_id,
        idempotency_key=str(payload["idempotency_key"]),
        workflow_revision=int(payload.get("workflow_revision", 1)),
        max_attempts=int(payload.get("max_attempts", 5)),
        application_id=_optional_str(payload.get("application_id")),
        operation_id=_optional_str(payload.get("operation_id")),
        sub_operation_id=_optional_str(payload.get("sub_operation_id")),
        webhook_event_id=_optional_str(payload.get("webhook_event_id")),
        request_id=_optional_str(payload.get("request_id")),
        message_id=_optional_str(getattr(properties, "message_id", None)),
        consumer_name=consumer_name,
        queue_name=queue_name,
    )


def _optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    raw = str(value).strip()
    return raw or None


def _extract_retry_count(properties: Any) -> int:
    headers = getattr(properties, "headers", None)
    if not isinstance(headers, dict):
        return 0
    raw_retry_count = headers.get("x-retry-count", 0)
    try:
        parsed = int(raw_retry_count)
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)


def _build_retry_properties(*, pika: Any, source_properties: Any, retry_count: int) -> Any:
    source_headers = getattr(source_properties, "headers", None)
    headers = dict(source_headers) if isinstance(source_headers, dict) else {}
    headers["x-retry-count"] = retry_count
    headers["x-retried-at"] = datetime.now(timezone.utc).isoformat()
    return pika.BasicProperties(
        content_type=getattr(source_properties, "content_type", "application/json"),
        content_encoding=getattr(source_properties, "content_encoding", None),
        delivery_mode=2,
        headers=headers,
        correlation_id=getattr(source_properties, "correlation_id", None),
        message_id=getattr(source_properties, "message_id", None),
        timestamp=getattr(source_properties, "timestamp", None),
        app_id=getattr(source_properties, "app_id", None),
    )


if __name__ == "__main__":
    run()

