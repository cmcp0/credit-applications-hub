from __future__ import annotations

import hmac
import hashlib


def verify_hmac_sha256_signature(
    *,
    payload_bytes: bytes,
    provided_signature: str,
    secret: str,
) -> bool:
    if not provided_signature.strip() or not secret:
        return False

    expected = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()
    normalized_provided = provided_signature.strip()
    if normalized_provided.startswith("sha256="):
        normalized_provided = normalized_provided[len("sha256=") :]
    return hmac.compare_digest(expected, normalized_provided)

