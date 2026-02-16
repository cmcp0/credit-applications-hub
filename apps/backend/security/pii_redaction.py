from __future__ import annotations

import hashlib
import hmac
import logging
from collections.abc import Mapping
from typing import Any

SENSITIVE_FIELDS = {
    "password",
    "password_hash",
    "authorization",
    "token",
    "access_token",
    "identity_document",
    "monthly_income",
    "provider_payload",
}


def redact_payload(payload: Any) -> Any:
    if isinstance(payload, Mapping):
        return {
            key: _redacted_value(key, value)
            for key, value in payload.items()
        }

    if isinstance(payload, list):
        return [redact_payload(value) for value in payload]

    return payload


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {key: _redacted_value(key, value) for key, value in headers.items()}


def fingerprint(value: str, pepper: str) -> str:
    digest = hmac.new(pepper.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest


def _redacted_value(key: str, value: Any) -> Any:
    if key.lower() in SENSITIVE_FIELDS:
        return "***REDACTED***"

    if isinstance(value, Mapping) or isinstance(value, list):
        return redact_payload(value)

    return value


class PIIRedactionFilter(logging.Filter):
    _CANDIDATE_RECORD_FIELDS = ("auth", "payload", "headers", "request", "response")

    def filter(self, record: logging.LogRecord) -> bool:
        for field_name in self._CANDIDATE_RECORD_FIELDS:
            if hasattr(record, field_name):
                original = getattr(record, field_name)
                setattr(record, field_name, redact_payload(original))

        return True


def install_pii_redaction_filter() -> None:
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if any(isinstance(existing, PIIRedactionFilter) for existing in handler.filters):
            continue
        handler.addFilter(PIIRedactionFilter())
