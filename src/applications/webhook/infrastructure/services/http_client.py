from __future__ import annotations

import ipaddress
import json
import os
import socket
import time
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

from src.applications.webhook.application.services.egress_webhook_delivery_service import (
    HttpResponse,
)


class UrllibWebhookHttpClient:
    def send_json(
        self,
        *,
        method: str,
        url: str,
        payload: dict[str, object],
        timeout_ms: int,
        headers: dict[str, str],
    ) -> HttpResponse:
        _enforce_egress_policy(url)

        encoded = json.dumps(payload).encode("utf-8")
        outbound = request.Request(url=url, method=method.upper(), data=encoded)
        for key, value in headers.items():
            outbound.add_header(key, value)

        started_at = time.monotonic()
        try:
            with request.urlopen(outbound, timeout=timeout_ms / 1000) as response:
                body = response.read().decode("utf-8", errors="replace")
                latency_ms = int((time.monotonic() - started_at) * 1000)
                return HttpResponse(
                    status_code=int(getattr(response, "status", 200)),
                    body=body,
                    latency_ms=latency_ms,
                )
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            latency_ms = int((time.monotonic() - started_at) * 1000)
            return HttpResponse(status_code=exc.code, body=body, latency_ms=latency_ms)
        except URLError as exc:  # pragma: no cover - network path
            raise RuntimeError(str(exc.reason)) from exc


def _enforce_egress_policy(url: str) -> None:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").strip().lower()

    if not hostname:
        raise RuntimeError("Webhook URL must include host")

    allow_http = os.getenv("WEBHOOK_EGRESS_ALLOW_HTTP", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if scheme != "https" and not allow_http:
        raise RuntimeError("Only HTTPS egress is allowed")

    allowlist = _read_allowlist()
    if allowlist and not _host_allowed(hostname, allowlist):
        raise RuntimeError("Webhook host is not in allowlist")

    allow_private = os.getenv("WEBHOOK_EGRESS_ALLOW_PRIVATE_NETWORKS", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if not allow_private:
        _assert_public_host(hostname)


def _read_allowlist() -> tuple[str, ...]:
    raw = os.getenv("WEBHOOK_EGRESS_DOMAIN_ALLOWLIST", "")
    items = [item.strip().lower() for item in raw.split(",")]
    return tuple(item for item in items if item)


def _host_allowed(hostname: str, allowlist: tuple[str, ...]) -> bool:
    for allowed in allowlist:
        if hostname == allowed or hostname.endswith(f".{allowed}"):
            return True
    return False


def _assert_public_host(hostname: str) -> None:
    if hostname == "localhost":
        raise RuntimeError("Private destinations are not allowed")

    candidate_ips: list[str]
    try:
        candidate_ips = list(
            {info[4][0] for info in socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)}
        )
    except socket.gaierror as exc:
        raise RuntimeError("Unable to resolve webhook host") from exc

    for raw_ip in candidate_ips:
        ip = ipaddress.ip_address(raw_ip)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise RuntimeError("Private destinations are not allowed")

