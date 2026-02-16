from __future__ import annotations

from typing import Optional


class AuthError(Exception):
    status_code = 400
    code = "AUTH_ERROR"
    message = "Authentication error"

    def __init__(self, message: Optional[str] = None):
        super().__init__(message or self.message)
        self.message = message or self.message


class InvalidCredentialsError(AuthError):
    status_code = 401
    code = "INVALID_CREDENTIALS"
    message = "Invalid credentials"


class UserInactiveError(AuthError):
    status_code = 403
    code = "USER_INACTIVE"
    message = "User is inactive"


class AuthHeaderMissingError(AuthError):
    status_code = 401
    code = "AUTH_HEADER_MISSING"
    message = "Authorization header is missing"


class TokenInvalidError(AuthError):
    status_code = 401
    code = "TOKEN_INVALID"
    message = "Token is invalid"


class TokenExpiredError(AuthError):
    status_code = 401
    code = "TOKEN_EXPIRED"
    message = "Token is expired"


class PermissionDeniedError(AuthError):
    status_code = 403
    code = "PERMISSION_DENIED"
    message = "Permission denied"


class RateLimiterUnavailableError(AuthError):
    status_code = 503
    code = "RATE_LIMITER_UNAVAILABLE"
    message = "Rate limiter is unavailable"
