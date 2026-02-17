from __future__ import annotations

from src.applications.application.application.queries.list_applications import ListApplicationsQuery
from src.applications.application.domain.ports.application_read_repository import ApplicationReadRepository
from src.applications.application.domain.value_objects import ApplicationListPage


class ListApplicationsService:
    def __init__(self, application_read_repository: ApplicationReadRepository) -> None:
        self._application_read_repository = application_read_repository

    def list(self, query: ListApplicationsQuery) -> ApplicationListPage:
        return self._application_read_repository.list_applications(query)
