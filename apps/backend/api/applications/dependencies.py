from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from apps.backend.auth.dependencies import get_db_session, get_settings
from apps.backend.settings import Settings
from apps.backend.api.applications.actor_authorizer import StatusUpdateActorAuthorizer
from src.applications.application.application.services.create_application_service import (
    CreateApplicationService,
)
from src.applications.application.application.services.get_application_service import GetApplicationService
from src.applications.application.application.services.list_applications_service import (
    ListApplicationsService,
)
from src.applications.application.application.services.update_application_status_service import (
    UpdateApplicationStatusService,
)
from src.applications.application.domain.ports.application_repository import ApplicationRepository
from src.applications.application.domain.ports.application_read_repository import ApplicationReadRepository
from src.applications.application.domain.ports.outbox_event_writer import OutboxEventWriter
from src.applications.application.domain.ports.status_history_repository import StatusHistoryRepository
from src.applications.application.infrastructure.adapters.application_read_repository import (
    SqlAlchemyApplicationReadRepository,
)
from src.applications.application.infrastructure.adapters.application_list_cache import (
    ApplicationListCache,
    build_application_list_cache,
)
from src.applications.application.infrastructure.adapters.cached_application_read_repository import (
    CachedApplicationReadRepository,
)
from src.applications.application.infrastructure.adapters.application_repository import (
    SqlAlchemyApplicationRepository,
)
from src.applications.application.infrastructure.adapters.status_history_repository import (
    SqlAlchemyStatusHistoryRepository,
)
from src.applications.shared.infrastructure.adapters.outbox_event_repository import (
    SqlAlchemyOutboxEventRepository,
)
from src.applications.workflow.application.services.resolve_initial_status_service import (
    ResolveInitialStatusService,
)
from src.applications.workflow.application.services.validate_status_transition_service import (
    ValidateStatusTransitionService,
)
from src.applications.workflow.domain.ports.workflow_repository import WorkflowRepository
from src.applications.workflow.infrastructure.adapters.workflow_repository import SqlAlchemyWorkflowRepository

from apps.backend.api.applications.command_consumer import UpdateApplicationStatusCommandConsumer


def get_workflow_repository(
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorkflowRepository:
    return SqlAlchemyWorkflowRepository(db_session)


def get_resolve_initial_status_service(
    workflow_repository: Annotated[WorkflowRepository, Depends(get_workflow_repository)],
) -> ResolveInitialStatusService:
    return ResolveInitialStatusService(workflow_repository)


def get_validate_status_transition_service(
    workflow_repository: Annotated[WorkflowRepository, Depends(get_workflow_repository)],
) -> ValidateStatusTransitionService:
    return ValidateStatusTransitionService(workflow_repository)


def get_application_repository(
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ApplicationRepository:
    return SqlAlchemyApplicationRepository(db_session)


def get_application_read_repository(
    settings: Annotated[Settings, Depends(get_settings)],
    db_session: Annotated[Session, Depends(get_db_session)],
    workflow_repository: Annotated[WorkflowRepository, Depends(get_workflow_repository)],
    list_cache: Annotated[ApplicationListCache, Depends(get_application_list_cache)],
) -> ApplicationReadRepository:
    base_repository = SqlAlchemyApplicationReadRepository(db_session, workflow_repository)
    if not settings.applications_read_cache_enabled:
        return base_repository

    return CachedApplicationReadRepository(
        delegate=base_repository,
        list_cache=list_cache,
    )


def get_application_list_cache(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ApplicationListCache:
    cache = getattr(request.app.state, "application_list_cache", None)
    if cache is None:
        cache = build_application_list_cache(
            enabled=settings.applications_read_cache_enabled,
            redis_url=settings.applications_read_cache_redis_url,
            ttl_seconds=settings.applications_read_cache_ttl_seconds,
        )
        request.app.state.application_list_cache = cache
    return cache


def get_status_history_repository(
    db_session: Annotated[Session, Depends(get_db_session)],
) -> StatusHistoryRepository:
    return SqlAlchemyStatusHistoryRepository(db_session)


def get_outbox_event_writer(
    db_session: Annotated[Session, Depends(get_db_session)],
) -> OutboxEventWriter:
    return SqlAlchemyOutboxEventRepository(db_session)


def get_create_application_service(
    application_repository: Annotated[ApplicationRepository, Depends(get_application_repository)],
    outbox_event_writer: Annotated[OutboxEventWriter, Depends(get_outbox_event_writer)],
    resolve_initial_status_service: Annotated[
        ResolveInitialStatusService,
        Depends(get_resolve_initial_status_service),
    ],
) -> CreateApplicationService:
    return CreateApplicationService(
        application_repository=application_repository,
        outbox_event_writer=outbox_event_writer,
        resolve_initial_status_service=resolve_initial_status_service,
    )


def get_update_application_status_service(
    application_repository: Annotated[ApplicationRepository, Depends(get_application_repository)],
    outbox_event_writer: Annotated[OutboxEventWriter, Depends(get_outbox_event_writer)],
    status_history_repository: Annotated[StatusHistoryRepository, Depends(get_status_history_repository)],
    validate_status_transition_service: Annotated[
        ValidateStatusTransitionService,
        Depends(get_validate_status_transition_service),
    ],
) -> UpdateApplicationStatusService:
    return UpdateApplicationStatusService(
        application_repository=application_repository,
        outbox_event_writer=outbox_event_writer,
        status_history_repository=status_history_repository,
        validate_status_transition_service=validate_status_transition_service,
    )


def get_list_applications_service(
    application_read_repository: Annotated[ApplicationReadRepository, Depends(get_application_read_repository)],
) -> ListApplicationsService:
    return ListApplicationsService(application_read_repository)


def get_get_application_service(
    application_read_repository: Annotated[ApplicationReadRepository, Depends(get_application_read_repository)],
) -> GetApplicationService:
    return GetApplicationService(application_read_repository)


def get_trusted_status_update_producers(
    settings: Annotated[Settings, Depends(get_settings)],
) -> tuple[str, ...]:
    return settings.applications_trusted_command_producers


def get_update_application_status_command_consumer(
    update_service: Annotated[
        UpdateApplicationStatusService,
        Depends(get_update_application_status_service),
    ],
    actor_authorizer: Annotated[
        StatusUpdateActorAuthorizer,
        Depends(get_status_update_actor_authorizer),
    ],
    trusted_producers: Annotated[
        tuple[str, ...],
        Depends(get_trusted_status_update_producers),
    ],
) -> UpdateApplicationStatusCommandConsumer:
    return UpdateApplicationStatusCommandConsumer(
        update_service=update_service,
        actor_authorizer=actor_authorizer,
        trusted_producers=trusted_producers,
    )


def get_status_update_actor_authorizer(
    db_session: Annotated[Session, Depends(get_db_session)],
) -> StatusUpdateActorAuthorizer:
    return StatusUpdateActorAuthorizer(db_session)
