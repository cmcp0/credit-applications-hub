from __future__ import annotations


class EmailAddress:
    @staticmethod
    def normalize(value: str) -> str:
        return value.strip().lower()

