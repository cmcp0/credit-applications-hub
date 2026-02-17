from __future__ import annotations

import logging

from apps.backend.security.pii_redaction import PIIRedactionFilter, install_pii_redaction_filter


def test_pii_redaction_filter_masks_sensitive_auth_fields() -> None:
    logger = logging.getLogger("test.auth.filter")
    record = logger.makeRecord(
        name=logger.name,
        level=logging.INFO,
        fn=__file__,
        lno=1,
        msg="auth event",
        args=(),
        exc_info=None,
        extra={
            "auth": {
                "password": "secret",
                "authorization": "Bearer abc",
                "email_fingerprint": "safe",
            }
        },
    )

    pii_filter = PIIRedactionFilter()
    allowed = pii_filter.filter(record)

    assert allowed is True
    assert record.auth["password"] == "***REDACTED***"
    assert record.auth["authorization"] == "***REDACTED***"
    assert record.auth["email_fingerprint"] == "safe"


def test_install_pii_redaction_filter_redacts_records_for_handlers_added_later() -> None:
    class CaptureHandler(logging.Handler):
        def __init__(self) -> None:
            super().__init__()
            self.records: list[logging.LogRecord] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    original_factory = logging.getLogRecordFactory()
    original_add_handler = logging.Logger.addHandler
    logger = logging.getLogger("test.auth.install.filter")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    try:
        install_pii_redaction_filter()
        capture_handler = CaptureHandler()
        logger.addHandler(capture_handler)

        logger.info(
            "auth event",
            extra={
                "auth": {
                    "password": "secret",
                    "authorization": "Bearer abc",
                    "email_fingerprint": "safe",
                }
            },
        )

        assert capture_handler.records
        record = capture_handler.records[0]
        assert record.auth["password"] == "***REDACTED***"
        assert record.auth["authorization"] == "***REDACTED***"
        assert record.auth["email_fingerprint"] == "safe"
    finally:
        logging.setLogRecordFactory(original_factory)
        logging.Logger.addHandler = original_add_handler
        logger.handlers.clear()
        logger.propagate = True
