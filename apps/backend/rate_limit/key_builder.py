from __future__ import annotations

from fastapi import Request

from apps.backend.security.pii_redaction import fingerprint


def client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()

    if request.client:
        return request.client.host

    return "unknown"


def public_key(route_template: str, ip_address: str) -> str:
    return f"rl:public:{route_template}:{ip_address}"


def login_ip_key(ip_address: str) -> str:
    return f"rl:login:ip:{ip_address}"


def login_email_ip_key(normalized_email: str, ip_address: str, pepper: str) -> str:
    email_hash = fingerprint(normalized_email, pepper)
    return f"rl:login:email_ip:{email_hash}:{ip_address}"

