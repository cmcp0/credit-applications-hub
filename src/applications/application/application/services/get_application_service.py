from __future__ import annotations

from src.applications.application.application.queries.get_application import GetApplicationQuery
from src.applications.application.domain.ports.application_read_repository import ApplicationReadRepository
from src.applications.application.domain.value_objects import ApplicationDetail
from src.applications.shared.domain.errors import ApplicationNotFoundError


class GetApplicationService:
    def __init__(self, application_read_repository: ApplicationReadRepository) -> None:
        self._application_read_repository = application_read_repository

    def get(self, query: GetApplicationQuery) -> ApplicationDetail:
        application = self._application_read_repository.get_application(query)
        if application is None:
            raise ApplicationNotFoundError()
        return application
