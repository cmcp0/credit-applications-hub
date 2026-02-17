from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from apps.backend.api.applications.actor_authorizer import StatusUpdateActorAuthorizer
from apps.backend.api.applications.command_consumer import (
    UpdateApplicationStatusCommandConsumer,
    UpdateApplicationStatusMessage,
)
from apps.backend.database import create_session_factory
from apps.backend.settings import Settings
from apps.workers.rabbitmq_topology import APPLICATIONS_DLX_EXCHANGE, RabbitMqTopologyManager
from src.applications.application.application.services.update_application_status_service import (
    UpdateApplicationStatusService,
)
from src.applications.application.infrastructure.adapters.application_repository import (
    SqlAlchemyApplicationRepository,
)
from src.applications.application.infrastructure.adapters.status_history_repository import (
    SqlAlchemyStatusHistoryRepository,
)
from src.applications.shared.domain.errors import ApplicationError
from src.applications.shared.infrastructure.adapters.outbox_event_repository import (
    SqlAlchemyOutboxEventRepository,
)
from src.applications.workflow.application.services.validate_status_transition_service import (
    ValidateStatusTransitionService,
)
from src.applications.workflow.infrastructure.adapters.workflow_repository import SqlAlchemyWorkflowRepository

logger = logging.getLogger(__name__)


def run() -> None:
    logging.basicConfig(level=os.getenv("STATUS_COMMAND_WORKER_LOG_LEVEL", "INFO"))

    settings = Settings.from_env()
    settings.validate_required()
    if not settings.messaging_enabled:
        raise RuntimeError("MESSAGING_ENABLED must be true for status command worker")

    queue_name = os.getenv("STATUS_UPDATE_COMMAND_QUEUE", "backend.applications.update_status.q")
    prefetch_count = int(os.getenv("STATUS_UPDATE_PREFETCH", "10"))
    max_retries = int(os.getenv("STATUS_UPDATE_MAX_RETRIES", "5"))
    retry_routing_key = os.getenv(
        "STATUS_UPDATE_RETRY_ROUTING_KEY",
        "backend.applications.update_status.retry",
    )

    topology = RabbitMqTopologyManager(
        settings.messaging_url,
        exchange_type=settings.messaging_exchange_type,
    )
    topology.ensure_topology()

    try:
        import pika
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError("pika is required for status command worker") from exc

    session_factory = create_session_factory(settings.database_url)

    connection = pika.BlockingConnection(pika.URLParameters(settings.messaging_url))
    channel = connection.channel()
    channel.basic_qos(prefetch_count=prefetch_count)

    def handle_message(ch, method, properties, body: bytes):
        session = session_factory()
        try:
            payload = _decode_payload(body)
            message = _to_status_update_message(
                payload,
                producer=(payload.get("producer") or properties.app_id or "unknown.producer"),
                message_id=properties.message_id,
            )

            workflow_repository = SqlAlchemyWorkflowRepository(session)
            update_service = UpdateApplicationStatusService(
                application_repository=SqlAlchemyApplicationRepository(session),
                outbox_event_writer=SqlAlchemyOutboxEventRepository(session),
                status_history_repository=SqlAlchemyStatusHistoryRepository(session),
                validate_status_transition_service=ValidateStatusTransitionService(workflow_repository),
            )
            command_consumer = UpdateApplicationStatusCommandConsumer(
                update_service=update_service,
                trusted_producers=settings.applications_trusted_command_producers,
                actor_authorizer=StatusUpdateActorAuthorizer(session),
            )
            command_consumer.consume(message)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except (ApplicationError, ValueError, KeyError) as exc:
            session.rollback()
            logger.warning(
                "status_update_command_rejected",
                extra={
                    "command": {
                        "routing_key": method.routing_key,
                        "message_id": properties.message_id,
                        "error": str(exc),
                    }
                },
            )
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as exc:  # pragma: no cover - runtime safety
            session.rollback()
            retry_count = _extract_retry_count(properties)
            logger.exception(
                "status_update_command_transient_error",
                extra={
                    "command": {
                        "routing_key": method.routing_key,
                        "message_id": properties.message_id,
                        "retry_count": retry_count,
                        "error": str(exc),
                    }
                },
            )
            if retry_count >= max_retries:
                logger.error(
                    "status_update_command_retries_exhausted",
                    extra={
                        "command": {
                            "routing_key": method.routing_key,
                            "message_id": properties.message_id,
                            "retry_count": retry_count,
                        }
                    },
                )
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            else:
                retried_count = retry_count + 1
                try:
                    ch.basic_publish(
                        exchange=APPLICATIONS_DLX_EXCHANGE,
                        routing_key=retry_routing_key,
                        body=body,
                        properties=_build_retry_properties(
                            pika=pika,
                            source_properties=properties,
                            retry_count=retried_count,
                        ),
                    )
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as retry_exc:  # pragma: no cover - runtime safety
                    logger.exception(
                        "status_update_command_retry_enqueue_failed",
                        extra={
                            "command": {
                                "routing_key": method.routing_key,
                                "message_id": properties.message_id,
                                "retry_count": retried_count,
                                "error": str(retry_exc),
                            }
                        },
                    )
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        finally:
            session.close()

    channel.basic_consume(
        queue=queue_name,
        on_message_callback=handle_message,
        auto_ack=False,
    )

    logger.info("status_command_worker_started", extra={"command": {"queue": queue_name}})
    channel.start_consuming()


def _decode_payload(raw_body: bytes) -> dict[str, Any]:
    payload = json.loads(raw_body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Command payload must be a JSON object")
    return payload


def _to_status_update_message(
    payload: dict[str, Any],
    *,
    producer: str,
    message_id: Optional[str],
) -> UpdateApplicationStatusMessage:
    target_status_code = payload.get("target_status_code") or payload.get("status")
    if target_status_code is None:
        raise KeyError("target_status_code")

    requested_at = _parse_optional_datetime(payload.get("requested_at"))
    correlation_id = str(payload.get("correlation_id") or message_id or payload.get("request_id") or "")
    request_id = str(payload.get("request_id") or correlation_id)

    if not correlation_id:
        raise ValueError("correlation_id is required")

    return UpdateApplicationStatusMessage(
        application_id=str(payload["application_id"]),
        target_status_code=str(target_status_code),
        actor_user_id=str(payload["actor_user_id"]),
        actor_role=str(payload.get("actor_role") or "operation"),
        expected_version=int(payload["expected_version"]),
        reason_code=str(payload["reason_code"]) if payload.get("reason_code") is not None else None,
        request_id=request_id,
        correlation_id=correlation_id,
        producer=producer,
        command_id=str(payload["command_id"]) if payload.get("command_id") else None,
        message_id=message_id,
        requested_at=requested_at,
    )


def _parse_optional_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("requested_at must be an ISO datetime string")

    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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
