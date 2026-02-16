from __future__ import annotations

from typing import Any
from typing import Optional


def map_login_audit_event(
    *,
    hashed_email: str,
    outcome: str,
    ip_address: Optional[str],
) -> dict[str, Any]:
    return {
        "event": "auth.login",
        "outcome": outcome,
        "email_fingerprint": hashed_email,
        "ip_address": ip_address,
    }
