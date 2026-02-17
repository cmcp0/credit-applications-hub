from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ListApplicationsQuery:
    actor_user_id: str
    can_list_all: bool
    country: Optional[str]
    status: Optional[str]
    page: int
    page_size: int
