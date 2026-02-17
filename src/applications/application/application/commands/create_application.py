from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateApplicationCommand:
    owner_id: str
    country: str
    full_name: str
    identity_document: str
    requested_amount: float
    monthly_income: float
    request_id: str
    correlation_id: str
