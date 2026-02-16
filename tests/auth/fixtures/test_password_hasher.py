from __future__ import annotations

import hashlib
import hmac
import os


class TestPasswordHasher:
    def verify(self, plain_password: str, password_hash: str) -> bool:
        try:
            algorithm, rounds_raw, salt_hex, digest_hex = password_hash.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            rounds = int(rounds_raw)
            expected = bytes.fromhex(digest_hex)
            computed = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                bytes.fromhex(salt_hex),
                rounds,
            )
            return hmac.compare_digest(expected, computed)
        except Exception:
            return False

    def hash_password(self, plain_password: str) -> str:
        salt = os.urandom(16)
        rounds = 390000
        digest = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, rounds)
        return f"pbkdf2_sha256${rounds}${salt.hex()}${digest.hex()}"
