from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request

app = FastAPI(title="Credit Applications Hub Mock CO Bank Provider")

# Deterministic fixture values keyed by CC for local testing.
_MOCK_DEBT_BY_DOCUMENT = {
    "10000001": 450.0,
    "10000002": 900.0,
    "10000003": 1800.0,
    "10000004": 3200.0,
}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/providers/co/banking-data")
async def get_banking_data(
    request: Request,
    identity_document: Optional[str] = Query(default=None, min_length=6, max_length=12),
) -> dict[str, object]:
    resolved_document = identity_document
    if not resolved_document:
        payload: dict[str, object] = {}
        try:
            raw_payload = await request.json()
            if isinstance(raw_payload, dict):
                payload = raw_payload
        except Exception:
            payload = {}

        candidate = payload.get("identity_document")
        if isinstance(candidate, str) and candidate.strip():
            resolved_document = candidate.strip()

    if not resolved_document:
        raise HTTPException(status_code=422, detail="identity_document is required")

    normalized = resolved_document.strip()
    if not normalized.isdigit():
        raise HTTPException(status_code=422, detail="identity_document must be numeric for CO CC")

    total_debt = _MOCK_DEBT_BY_DOCUMENT.get(normalized)
    if total_debt is None:
        # Deterministic fallback to keep local testing predictable.
        total_debt = float((int(normalized[-2:]) + 10) * 75)

    return {
        "provider_code": "mock-co-bank",
        "country": "CO",
        "document_type": "CC",
        "identity_document": normalized,
        "total_debt": total_debt,
        "currency": "COP",
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
