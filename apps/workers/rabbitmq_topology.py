from __future__ import annotations

from dataclasses import dataclass

APPLICATIONS_EVENTS_EXCHANGE = "applications.events"
APPLICATIONS_COMMANDS_EXCHANGE = "applications.commands"
APPLICATIONS_DLX_EXCHANGE = "applications.dlx"
WORKFLOWS_EVENTS_EXCHANGE = "workflows.events"
WORKFLOWS_COMMANDS_EXCHANGE = "workflows.commands"
WORKFLOWS_DLX_EXCHANGE = "workflows.dlx"
WEBHOOKS_EVENTS_EXCHANGE = "webhooks.events"
WEBHOOKS_COMMANDS_EXCHANGE = "webhooks.commands"
WEBHOOKS_DLX_EXCHANGE = "webhooks.dlx"


@dataclass(frozen=True)
class QueueBinding:
    queue_name: str
    exchange_name: str
    routing_key: str
    dead_letter_routing_key: str
    retry_routing_key: str
    dlx_exchange: str = APPLICATIONS_DLX_EXCHANGE
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
    QueueBinding(
        queue_name="workers.workflow.execute.q",
        exchange_name=WORKFLOWS_EVENTS_EXCHANGE,
        routing_key="credit.workflow.execution.queued",
        dead_letter_routing_key="workers.workflow.execute.dead",
        retry_routing_key="workers.workflow.execute.retry",
        dlx_exchange=WORKFLOWS_DLX_EXCHANGE,
        retry_delay_ms=5000,
    ),
    QueueBinding(
        queue_name="workers.webhook.ingress.normalize.q",
        exchange_name=WEBHOOKS_EVENTS_EXCHANGE,
        routing_key="credit.webhook.ingress.received",
        dead_letter_routing_key="workers.webhook.ingress.dead",
        retry_routing_key="workers.webhook.ingress.retry",
        dlx_exchange=WEBHOOKS_DLX_EXCHANGE,
        retry_delay_ms=2000,
    ),
    QueueBinding(
        queue_name="workers.webhook.egress.deliver.q",
        exchange_name=WEBHOOKS_COMMANDS_EXCHANGE,
        routing_key="credit.webhook.egress.deliver",
        dead_letter_routing_key="workers.webhook.egress.deliver.dead",
        retry_routing_key="workers.webhook.egress.deliver.retry",
        dlx_exchange=WEBHOOKS_DLX_EXCHANGE,
        retry_delay_ms=5000,
    ),
    QueueBinding(
        queue_name="workers.webhook.egress.replay.q",
        exchange_name=WEBHOOKS_COMMANDS_EXCHANGE,
        routing_key="credit.webhook.egress.replay",
        dead_letter_routing_key="workers.webhook.egress.replay.dead",
        retry_routing_key="workers.webhook.egress.replay.retry",
        dlx_exchange=WEBHOOKS_DLX_EXCHANGE,
        retry_delay_ms=5000,
    ),
    QueueBinding(
        queue_name="backend.workflow.execution.projection.q",
        exchange_name=WORKFLOWS_EVENTS_EXCHANGE,
        routing_key="credit.workflow.execution.*",
        dead_letter_routing_key="backend.workflow.execution.projection.dead",
        retry_routing_key="backend.workflow.execution.projection.retry",
        dlx_exchange=WORKFLOWS_DLX_EXCHANGE,
        retry_delay_ms=5000,
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
            channel.exchange_declare(
                exchange=WORKFLOWS_EVENTS_EXCHANGE,
                exchange_type=self._exchange_type,
                durable=self._durable,
            )
            channel.exchange_declare(
                exchange=WORKFLOWS_COMMANDS_EXCHANGE,
                exchange_type=self._exchange_type,
                durable=self._durable,
            )
            channel.exchange_declare(
                exchange=WORKFLOWS_DLX_EXCHANGE,
                exchange_type=self._exchange_type,
                durable=self._durable,
            )
            channel.exchange_declare(
                exchange=WEBHOOKS_EVENTS_EXCHANGE,
                exchange_type=self._exchange_type,
                durable=self._durable,
            )
            channel.exchange_declare(
                exchange=WEBHOOKS_COMMANDS_EXCHANGE,
                exchange_type=self._exchange_type,
                durable=self._durable,
            )
            channel.exchange_declare(
                exchange=WEBHOOKS_DLX_EXCHANGE,
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
            exchange=binding.dlx_exchange,
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
            exchange=binding.dlx_exchange,
            routing_key=binding.retry_routing_key,
        )

        channel.queue_declare(
            queue=binding.queue_name,
            durable=self._durable,
            arguments={
                "x-dead-letter-exchange": binding.dlx_exchange,
                "x-dead-letter-routing-key": binding.dead_letter_routing_key,
            },
        )
        channel.queue_bind(
            queue=binding.queue_name,
            exchange=binding.exchange_name,
            routing_key=binding.routing_key,
        )
