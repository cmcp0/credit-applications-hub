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
_FACTORY_SENTINEL = "_pii_redaction_factory_installed"
_ADD_HANDLER_SENTINEL = "_pii_redaction_add_handler_installed"


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
        _redact_record(record)
        return True


def install_pii_redaction_filter() -> None:
    current_factory = logging.getLogRecordFactory()
    if not getattr(current_factory, _FACTORY_SENTINEL, False):
        def _redacting_record_factory(*args, **kwargs) -> logging.LogRecord:
            record = current_factory(*args, **kwargs)
            _redact_record(record)
            return record

        setattr(_redacting_record_factory, _FACTORY_SENTINEL, True)
        logging.setLogRecordFactory(_redacting_record_factory)

    _install_add_handler_hook()

    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if any(isinstance(existing, PIIRedactionFilter) for existing in handler.filters):
            continue
        handler.addFilter(PIIRedactionFilter())


def _redact_record(record: logging.LogRecord) -> None:
    for field_name in PIIRedactionFilter._CANDIDATE_RECORD_FIELDS:
        if hasattr(record, field_name):
            original = getattr(record, field_name)
            setattr(record, field_name, redact_payload(original))


def _install_add_handler_hook() -> None:
    current_add_handler = logging.Logger.addHandler
    if getattr(current_add_handler, _ADD_HANDLER_SENTINEL, False):
        return

    def _add_handler_with_redaction(self, handler: logging.Handler) -> None:
        if not any(isinstance(existing, PIIRedactionFilter) for existing in handler.filters):
            handler.addFilter(PIIRedactionFilter())
        current_add_handler(self, handler)

    setattr(_add_handler_with_redaction, _ADD_HANDLER_SENTINEL, True)
    logging.Logger.addHandler = _add_handler_with_redaction
