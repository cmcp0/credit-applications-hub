from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

from src.auth.authentication.domain.ports.token_issuer import IssuedToken, TokenIssuer
from src.auth.shared.domain.errors import TokenExpiredError, TokenInvalidError


@dataclass(frozen=True)
class JwtCodecConfig:
    secret: str
    issuer: str
    audience: str
    ttl_seconds: int
    algorithm: str = "HS256"


class JwtCodec:
    _REQUIRED_CLAIMS = ("sub", "roles", "permissions", "iat", "exp", "iss", "aud")

    def __init__(self, config: JwtCodecConfig) -> None:
        self._config = config

    def issue_token(
        self,
        *,
        subject: str,
        roles: Sequence[str],
        permissions: Sequence[str],
    ) -> IssuedToken:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self._config.ttl_seconds)

        claims: dict[str, Any] = {
            "sub": subject,
            "roles": list(roles),
            "permissions": list(permissions),
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "iss": self._config.issuer,
            "aud": self._config.audience,
        }

        header = {
            "alg": self._config.algorithm,
            "typ": "JWT",
        }
        token = _encode_hs256(header, claims, self._config.secret)
        return IssuedToken(access_token=token, expires_in=self._config.ttl_seconds)

    def decode_token(self, token: str) -> Mapping[str, Any]:
        try:
            header, payload = _decode_hs256(token, self._config.secret)
            if header.get("alg") != self._config.algorithm:
                raise TokenInvalidError("Unexpected JWT algorithm")

            for claim in self._REQUIRED_CLAIMS:
                if claim not in payload:
                    raise TokenInvalidError(f"Missing required claim: {claim}")

            if payload.get("iss") != self._config.issuer:
                raise TokenInvalidError("Invalid issuer")

            audience = payload.get("aud")
            if isinstance(audience, list):
                if self._config.audience not in audience:
                    raise TokenInvalidError("Invalid audience")
            elif audience != self._config.audience:
                raise TokenInvalidError("Invalid audience")

            exp_value = payload.get("exp")
            if not isinstance(exp_value, (int, float)):
                raise TokenInvalidError("Invalid exp claim")

            now = datetime.now(timezone.utc).timestamp()
            if now >= float(exp_value):
                raise TokenExpiredError()

            return payload
        except TokenExpiredError:
            raise
        except TokenInvalidError:
            raise
        except Exception as exc:  # pragma: no cover
            raise TokenInvalidError() from exc


class JwtTokenIssuer(TokenIssuer):
    def __init__(self, codec: JwtCodec) -> None:
        self._codec = codec

    def issue_access_token(
        self,
        *,
        subject: str,
        roles: Sequence[str],
        permissions: Sequence[str],
    ) -> IssuedToken:
        return self._codec.issue_token(subject=subject, roles=roles, permissions=permissions)


def _encode_hs256(header: Mapping[str, Any], payload: Mapping[str, Any], secret: str) -> str:
    header_segment = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    payload_segment = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_segment = _b64url_encode(signature)
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def _decode_hs256(token: str, secret: str) -> tuple[dict[str, Any], dict[str, Any]]:
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenInvalidError("Malformed JWT")

    header_segment, payload_segment, signature_segment = parts
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    expected_signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    decoded_signature = _b64url_decode(signature_segment)

    if not hmac.compare_digest(expected_signature, decoded_signature):
        raise TokenInvalidError("Invalid JWT signature")

    header = json.loads(_b64url_decode(header_segment).decode("utf-8"))
    payload = json.loads(_b64url_decode(payload_segment).decode("utf-8"))

    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise TokenInvalidError("Invalid JWT structure")

    return header, payload


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))
