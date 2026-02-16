from __future__ import annotations

import os
from dataclasses import dataclass


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    database_url: str
    auth_jwt_secret: str
    auth_jwt_issuer: str
    auth_jwt_audience: str
    auth_jwt_ttl_seconds: int
    rate_limit_enabled: bool
    rate_limit_redis_url: str
    rate_limit_public_window_seconds: int
    rate_limit_public_max_requests: int
    rate_limit_login_ip_window_seconds: int
    rate_limit_login_ip_max_requests: int
    rate_limit_login_email_ip_window_seconds: int
    rate_limit_login_email_ip_max_requests: int
    rate_limit_key_pepper: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.getenv(
                "DATABASE_URL",
                "sqlite+pysqlite:///./credit_applications_hub.db",
            ),
            auth_jwt_secret=os.getenv("AUTH_JWT_SECRET", ""),
            auth_jwt_issuer=os.getenv("AUTH_JWT_ISSUER", ""),
            auth_jwt_audience=os.getenv("AUTH_JWT_AUDIENCE", ""),
            auth_jwt_ttl_seconds=_int_env("AUTH_JWT_TTL_SECONDS", 3600),
            rate_limit_enabled=_bool_env("RATE_LIMIT_ENABLED", True),
            rate_limit_redis_url=os.getenv("RATE_LIMIT_REDIS_URL", "redis://localhost:6379/0"),
            rate_limit_public_window_seconds=_int_env("RATE_LIMIT_PUBLIC_WINDOW_SECONDS", 60),
            rate_limit_public_max_requests=_int_env("RATE_LIMIT_PUBLIC_MAX_REQUESTS", 120),
            rate_limit_login_ip_window_seconds=_int_env("RATE_LIMIT_LOGIN_IP_WINDOW_SECONDS", 60),
            rate_limit_login_ip_max_requests=_int_env("RATE_LIMIT_LOGIN_IP_MAX_REQUESTS", 10),
            rate_limit_login_email_ip_window_seconds=_int_env(
                "RATE_LIMIT_LOGIN_EMAIL_IP_WINDOW_SECONDS",
                300,
            ),
            rate_limit_login_email_ip_max_requests=_int_env(
                "RATE_LIMIT_LOGIN_EMAIL_IP_MAX_REQUESTS",
                5,
            ),
            rate_limit_key_pepper=os.getenv("RATE_LIMIT_KEY_PEPPER", ""),
        )

    def validate_required(self) -> None:
        required = {
            "AUTH_JWT_SECRET": self.auth_jwt_secret,
            "AUTH_JWT_ISSUER": self.auth_jwt_issuer,
            "AUTH_JWT_AUDIENCE": self.auth_jwt_audience,
        }
        if self.rate_limit_enabled:
            required["RATE_LIMIT_KEY_PEPPER"] = self.rate_limit_key_pepper
        missing = [name for name, value in required.items() if not value]
        if missing:
            joined = ", ".join(sorted(missing))
            raise RuntimeError(f"Missing required environment variables: {joined}")
