from __future__ import annotations

from typing import Optional

from apps.workers.rabbitmq_topology import (
    APPLICATIONS_COMMANDS_EXCHANGE,
    APPLICATIONS_DLX_EXCHANGE,
    DEFAULT_QUEUE_BINDINGS,
    RabbitMqTopologyManager,
)


class _RecordingChannel:
    def __init__(self) -> None:
        self.declarations: list[tuple[str, bool, dict[str, object]]] = []
        self.bindings: list[tuple[str, str, str]] = []

    def queue_declare(
        self,
        *,
        queue: str,
        durable: bool,
        arguments: Optional[dict[str, object]] = None,
    ) -> None:
        self.declarations.append((queue, durable, arguments or {}))

    def queue_bind(self, *, queue: str, exchange: str, routing_key: str) -> None:
        self.bindings.append((queue, exchange, routing_key))


def test_default_topology_includes_status_update_command_binding() -> None:
    binding = next(
        item
        for item in DEFAULT_QUEUE_BINDINGS
        if item.queue_name == "backend.applications.update_status.q"
    )

    assert binding.exchange_name == APPLICATIONS_COMMANDS_EXCHANGE
    assert binding.routing_key == "credit.application.status.update"
    assert binding.dead_letter_routing_key == "backend.applications.update_status.dead"
    assert binding.retry_routing_key == "backend.applications.update_status.retry"
    assert binding.retry_delay_ms > 0


def test_queue_declaration_adds_dlq_and_retry_policy_for_status_update_queue() -> None:
    manager = RabbitMqTopologyManager.__new__(RabbitMqTopologyManager)
    manager._durable = True

    binding = next(
        item
        for item in DEFAULT_QUEUE_BINDINGS
        if item.queue_name == "backend.applications.update_status.q"
    )
    channel = _RecordingChannel()

    manager._declare_queue(channel, binding)

    declarations = {queue: (durable, args) for queue, durable, args in channel.declarations}
    main_queue_args = declarations[binding.queue_name][1]
    retry_queue_args = declarations[f"{binding.queue_name}.retry"][1]

    assert main_queue_args["x-dead-letter-exchange"] == APPLICATIONS_DLX_EXCHANGE
    assert main_queue_args["x-dead-letter-routing-key"] == binding.dead_letter_routing_key

    assert retry_queue_args["x-message-ttl"] == binding.retry_delay_ms
    assert retry_queue_args["x-dead-letter-exchange"] == binding.exchange_name
    assert retry_queue_args["x-dead-letter-routing-key"] == binding.routing_key

    assert (
        f"{binding.queue_name}.dlq",
        APPLICATIONS_DLX_EXCHANGE,
        binding.dead_letter_routing_key,
    ) in channel.bindings
    assert (
        f"{binding.queue_name}.retry",
        APPLICATIONS_DLX_EXCHANGE,
        binding.retry_routing_key,
    ) in channel.bindings
