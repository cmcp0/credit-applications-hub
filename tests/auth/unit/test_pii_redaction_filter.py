from __future__ import annotations

import logging

from apps.backend.security.pii_redaction import PIIRedactionFilter


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
