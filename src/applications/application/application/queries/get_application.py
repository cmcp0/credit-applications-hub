from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetApplicationQuery:
    actor_user_id: str
    can_list_all: bool
    application_id: str
