from passlib.hash import argon2 as passlib_argon2

from src.auth.authentication.domain.ports.password_hasher import PasswordHasher


class Argon2PasswordHasher(PasswordHasher):
    def __init__(self) -> None:
        self._hasher = passlib_argon2.using(type="ID")

    def verify(self, plain_password: str, password_hash: str) -> bool:
        try:
            return self._hasher.verify(plain_password, password_hash)
        except ValueError:
            return False

    def hash_password(self, plain_password: str) -> str:
        return self._hasher.hash(plain_password)
