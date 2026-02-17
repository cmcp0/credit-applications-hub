from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class Application:
    id: str
    user_id: str
    country: str
    full_name: str
    identity_document: str
    requested_amount: float
    monthly_income: float
    application_date: date
    status_code: str
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        application_id: str,
        user_id: str,
        country: str,
        full_name: str,
        identity_document: str,
        requested_amount: float,
        monthly_income: float,
        application_date: date,
        initial_status_code: str,
        created_at: datetime,
    ) -> "Application":
        return cls(
            id=application_id,
            user_id=user_id,
            country=country,
            full_name=full_name,
            identity_document=identity_document,
            requested_amount=requested_amount,
            monthly_income=monthly_income,
            application_date=application_date,
            status_code=initial_status_code,
            version=1,
            created_at=created_at,
            updated_at=created_at,
        )

    def transition_status(self, *, target_status_code: str, changed_at: datetime) -> str:
        previous_status_code = self.status_code
        self.status_code = target_status_code
        self.version += 1
        self.updated_at = changed_at
        return previous_status_code
