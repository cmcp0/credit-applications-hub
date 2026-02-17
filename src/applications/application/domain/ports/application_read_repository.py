from __future__ import annotations

from typing import Optional, Protocol

from src.applications.application.application.queries.get_application import GetApplicationQuery
from src.applications.application.application.queries.list_applications import ListApplicationsQuery
from src.applications.application.domain.value_objects import ApplicationDetail, ApplicationListPage


class ApplicationReadRepository(Protocol):
    def list_applications(self, query: ListApplicationsQuery) -> ApplicationListPage:
        ...

    def get_application(self, query: GetApplicationQuery) -> Optional[ApplicationDetail]:
        ...
