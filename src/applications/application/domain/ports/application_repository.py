from __future__ import annotations

from typing import Optional, Protocol

from src.applications.application.domain.entities import Application


class ApplicationRepository(Protocol):
    def add(self, application: Application) -> None:
        ...

    def get_by_id(self, application_id: str) -> Optional[Application]:
        ...

    def save(self, application: Application, expected_previous_version: int) -> None:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...
