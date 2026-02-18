from __future__ import annotations

from src.applications.webhook.application.services.egress_webhook_delivery_service import (
    EgressDeliveryCommand,
    EgressDeliveryResult,
    EgressWebhookDeliveryService,
)


def dispatch_egress_delivery(
    service: EgressWebhookDeliveryService,
    *,
    command: EgressDeliveryCommand,
) -> EgressDeliveryResult:
    return service.deliver(command)

