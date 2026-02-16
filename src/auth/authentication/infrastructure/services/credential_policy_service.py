from __future__ import annotations

import re


class CredentialPolicyService:
    _EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    @staticmethod
    def normalize_email(value: str) -> str:
        return value.strip().lower()

    def validate_email(self, value: str) -> bool:
        return bool(self._EMAIL_PATTERN.match(value.strip().lower()))

