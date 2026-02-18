from __future__ import annotations

import json
from typing import Optional

from src.applications.application.application.queries.get_application import GetApplicationQuery
from src.applications.application.application.queries.list_applications import ListApplicationsQuery
from src.applications.application.domain.ports.application_read_repository import ApplicationReadRepository
from src.applications.application.domain.value_objects import ApplicationDetail, ApplicationListPage
from src.applications.application.infrastructure.adapters.application_list_cache import (
    ApplicationListCache,
)


class CachedApplicationReadRepository(ApplicationReadRepository):
    def __init__(
        self,
        delegate: ApplicationReadRepository,
        list_cache: ApplicationListCache,
    ) -> None:
        self._delegate = delegate
        self._list_cache = list_cache

    def list_applications(self, query: ListApplicationsQuery) -> ApplicationListPage:
        cache_key = _build_list_cache_key(query)
        cached = self._list_cache.get(cache_key)
        if cached is not None:
            return cached

        result = self._delegate.list_applications(query)
        self._list_cache.set(cache_key, result)
        return result

    def get_application(self, query: GetApplicationQuery) -> Optional[ApplicationDetail]:
        return self._delegate.get_application(query)


def _build_list_cache_key(query: ListApplicationsQuery) -> str:
    payload = {
        "actor_user_id": query.actor_user_id,
        "can_list_all": query.can_list_all,
        "country": query.country.strip().upper() if query.country else None,
        "status": query.status.strip().upper() if query.status else None,
        "page": query.page,
        "page_size": query.page_size,
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)
