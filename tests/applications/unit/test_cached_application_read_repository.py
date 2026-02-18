from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from src.applications.application.application.queries.get_application import GetApplicationQuery
from src.applications.application.application.queries.list_applications import ListApplicationsQuery
from src.applications.application.domain.ports.application_read_repository import ApplicationReadRepository
from src.applications.application.domain.value_objects import (
    ApplicationDetail,
    ApplicationListPage,
    ApplicationSummary,
)
from src.applications.application.infrastructure.adapters.application_list_cache import (
    InMemoryApplicationListCache,
)
from src.applications.application.infrastructure.adapters.cached_application_read_repository import (
    CachedApplicationReadRepository,
)


class _StubReadRepository(ApplicationReadRepository):
    def __init__(self, page: ApplicationListPage) -> None:
        self._page = page
        self.list_calls = 0
        self.get_calls = 0

    def list_applications(self, query: ListApplicationsQuery) -> ApplicationListPage:
        del query
        self.list_calls += 1
        return self._page

    def get_application(self, query: GetApplicationQuery) -> Optional[ApplicationDetail]:
        del query
        self.get_calls += 1
        return None


def _sample_page() -> ApplicationListPage:
    now = datetime.now(timezone.utc)
    return ApplicationListPage(
        items=(
            ApplicationSummary(
                id="app-1",
                country="MX",
                status_code="PENDING_REVIEW",
                requested_amount=5000.0,
                created_at=now,
                updated_at=now,
            ),
        ),
        page=1,
        page_size=20,
        total=1,
    )


def _sample_query() -> ListApplicationsQuery:
    return ListApplicationsQuery(
        actor_user_id="44444444-4444-4444-4444-444444444441",
        can_list_all=False,
        country="MX",
        status="PENDING_REVIEW",
        page=1,
        page_size=20,
    )


def test_list_applications_uses_cache_for_identical_query() -> None:
    delegate = _StubReadRepository(_sample_page())
    repository = CachedApplicationReadRepository(
        delegate=delegate,
        list_cache=InMemoryApplicationListCache(ttl_seconds=60),
    )
    query = _sample_query()

    first = repository.list_applications(query)
    second = repository.list_applications(query)

    assert first == second
    assert delegate.list_calls == 1


def test_get_application_delegates_without_list_cache_side_effects() -> None:
    delegate = _StubReadRepository(_sample_page())
    repository = CachedApplicationReadRepository(
        delegate=delegate,
        list_cache=InMemoryApplicationListCache(ttl_seconds=60),
    )

    result = repository.get_application(
        GetApplicationQuery(
            actor_user_id="44444444-4444-4444-4444-444444444441",
            can_list_all=False,
            application_id="app-1",
        )
    )

    assert result is None
    assert delegate.get_calls == 1
    assert delegate.list_calls == 0
