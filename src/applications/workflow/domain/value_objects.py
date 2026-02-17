from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TransitionValidation:
    country: str
    from_status_code: str
    to_status_code: str
