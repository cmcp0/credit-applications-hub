from __future__ import annotations

from dataclasses import dataclass

APPLICATIONS_EVENTS_EXCHANGE = "applications.events"
APPLICATIONS_COMMANDS_EXCHANGE = "applications.commands"
APPLICATIONS_DLX_EXCHANGE = "applications.dlx"


@dataclass(frozen=True)
class QueueBinding:
    queue_name: str
    exchange_name: str
    routing_key: str
    dead_letter_routing_key: str
    retry_routing_key: str
    retry_delay_ms: int = 5000


DEFAULT_QUEUE_BINDINGS: tuple[QueueBinding, ...] = (
    QueueBinding(
        queue_name="workers.application_created.q",
        exchange_name=APPLICATIONS_EVENTS_EXCHANGE,
        routing_key="credit.application.created",
        dead_letter_routing_key="workers.application_created.dead",
        retry_routing_key="workers.application_created.retry",
        retry_delay_ms=5000,
    ),
    QueueBinding(
        queue_name="workers.status_changed.q",
        exchange_name=APPLICATIONS_EVENTS_EXCHANGE,
        routing_key="credit.application.status.updated",
        dead_letter_routing_key="workers.status_changed.dead",
        retry_routing_key="workers.status_changed.retry",
        retry_delay_ms=5000,
    ),
    QueueBinding(
        queue_name="backend.applications.update_status.q",
        exchange_name=APPLICATIONS_COMMANDS_EXCHANGE,
        routing_key="credit.application.status.update",
        dead_letter_routing_key="backend.applications.update_status.dead",
        retry_routing_key="backend.applications.update_status.retry",
        retry_delay_ms=10000,
    ),
)


class RabbitMqTopologyManager:
    def __init__(
        self,
        amqp_url: str,
        *,
        exchange_type: str = "topic",
        durable: bool = True,
        queue_bindings: tuple[QueueBinding, ...] = DEFAULT_QUEUE_BINDINGS,
    ) -> None:
        try:
            import pika
        except ModuleNotFoundError as exc:  # pragma: no cover - runtime dependency
            raise RuntimeError("pika is required for RabbitMQ topology setup") from exc

        self._pika = pika
        self._amqp_url = amqp_url
        self._exchange_type = exchange_type
        self._durable = durable
        self._queue_bindings = queue_bindings

    def ensure_topology(self) -> None:
        connection = self._pika.BlockingConnection(self._pika.URLParameters(self._amqp_url))
        try:
            channel = connection.channel()
            channel.exchange_declare(
                exchange=APPLICATIONS_EVENTS_EXCHANGE,
                exchange_type=self._exchange_type,
                durable=self._durable,
            )
            channel.exchange_declare(
                exchange=APPLICATIONS_COMMANDS_EXCHANGE,
                exchange_type=self._exchange_type,
                durable=self._durable,
            )
            channel.exchange_declare(
                exchange=APPLICATIONS_DLX_EXCHANGE,
                exchange_type=self._exchange_type,
                durable=self._durable,
            )

            for binding in self._queue_bindings:
                self._declare_queue(channel, binding)
        finally:
            connection.close()

    def _declare_queue(self, channel, binding: QueueBinding) -> None:
        dlq_name = f"{binding.queue_name}.dlq"
        retry_queue_name = f"{binding.queue_name}.retry"

        channel.queue_declare(queue=dlq_name, durable=self._durable)
        channel.queue_bind(
            queue=dlq_name,
            exchange=APPLICATIONS_DLX_EXCHANGE,
            routing_key=binding.dead_letter_routing_key,
        )

        channel.queue_declare(
            queue=retry_queue_name,
            durable=self._durable,
            arguments={
                "x-message-ttl": binding.retry_delay_ms,
                "x-dead-letter-exchange": binding.exchange_name,
                "x-dead-letter-routing-key": binding.routing_key,
            },
        )
        channel.queue_bind(
            queue=retry_queue_name,
            exchange=APPLICATIONS_DLX_EXCHANGE,
            routing_key=binding.retry_routing_key,
        )

        channel.queue_declare(
            queue=binding.queue_name,
            durable=self._durable,
            arguments={
                "x-dead-letter-exchange": APPLICATIONS_DLX_EXCHANGE,
                "x-dead-letter-routing-key": binding.dead_letter_routing_key,
            },
        )
        channel.queue_bind(
            queue=binding.queue_name,
            exchange=binding.exchange_name,
            routing_key=binding.routing_key,
        )
