from __future__ import annotations

import hashlib
import hmac
import os
from base64 import b64decode, b64encode

try:  # pragma: no cover - exercised when passlib is installed
    from passlib.hash import argon2 as passlib_argon2
except ModuleNotFoundError:  # pragma: no cover - exercised in minimal test envs
    passlib_argon2 = None

from src.auth.authentication.domain.ports.password_hasher import PasswordHasher


class Argon2PasswordHasher(PasswordHasher):
    def __init__(self) -> None:
        if passlib_argon2 is None:
            self._hasher = _FallbackPasswordHasher()
        else:
            self._hasher = passlib_argon2.using(type="ID")

    def verify(self, plain_password: str, password_hash: str) -> bool:
        try:
            return self._hasher.verify(plain_password, password_hash)
        except ValueError:
            return False

    def hash_password(self, plain_password: str) -> str:
        return self._hasher.hash(plain_password)


class _FallbackPasswordHasher:
    _ITERATIONS = 120_000
    _ALGORITHM = "sha256"
    _SALT_BYTES = 16

    def hash(self, plain_password: str) -> str:
        salt = os.urandom(self._SALT_BYTES)
        digest = hashlib.pbkdf2_hmac(
            self._ALGORITHM,
            plain_password.encode("utf-8"),
            salt,
            self._ITERATIONS,
        )
        return f"pbkdf2${self._ITERATIONS}${b64encode(salt).decode('ascii')}${b64encode(digest).decode('ascii')}"

    def verify(self, plain_password: str, password_hash: str) -> bool:
        try:
            _, iterations, encoded_salt, encoded_digest = password_hash.split("$", 3)
            salt = b64decode(encoded_salt.encode("ascii"))
            expected_digest = b64decode(encoded_digest.encode("ascii"))
            computed_digest = hashlib.pbkdf2_hmac(
                self._ALGORITHM,
                plain_password.encode("utf-8"),
                salt,
                int(iterations),
            )
            return hmac.compare_digest(computed_digest, expected_digest)
        except Exception:
            return False
