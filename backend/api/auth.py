"""
AETHERTRADE-SWARM — API Key Authentication
SHA-256 hashed key validation with per-tier rate limiting.
"""
from __future__ import annotations

import hashlib
import secrets
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from config import get_settings
from models.schemas import KeyTier

settings = get_settings()

# ---------------------------------------------------------------------------
# In-memory key store (MVP — replace with DB in production)
# ---------------------------------------------------------------------------

_key_store: dict[str, dict] = {}


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def create_api_key(
    name: str,
    tier: KeyTier,
    owner_email: str,
    description: str | None = None,
) -> tuple[str, dict]:
    """
    Create a new API key. Returns (raw_key, key_record).
    Raw key is shown once and never stored in plaintext.
    """
    raw_key = f"orc_{secrets.token_urlsafe(32)}"
    key_id = str(uuid4())
    key_hash = _hash_key(raw_key)

    rate_limits = {
        KeyTier.FREE: settings.rate_limit_free,
        KeyTier.PRO: settings.rate_limit_pro,
        KeyTier.ENTERPRISE: settings.rate_limit_enterprise,
    }

    record = {
        "key_id": key_id,
        "key_hash": key_hash,
        "name": name,
        "tier": tier,
        "owner_email": owner_email,
        "description": description,
        "prefix": raw_key[:8],
        "rate_limit_per_minute": rate_limits[tier],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_used_at": None,
        "request_count": 0,
        "is_active": True,
    }
    _key_store[key_hash] = record
    return raw_key, record


def get_key_record(key_hash: str) -> dict | None:
    return _key_store.get(key_hash)


def list_keys() -> list[dict]:
    return list(_key_store.values())


def revoke_key(key_id: str) -> bool:
    for record in _key_store.values():
        if record["key_id"] == key_id:
            record["is_active"] = False
            return True
    return False


def _touch_key(key_hash: str) -> None:
    if key_hash in _key_store:
        _key_store[key_hash]["request_count"] += 1
        _key_store[key_hash]["last_used_at"] = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Rate limiter — sliding window in-memory
# ---------------------------------------------------------------------------

# { key_id: [timestamp, ...] }
_request_log: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(key_id: str, limit_per_minute: int) -> None:
    now = time.monotonic()
    window_start = now - 60.0
    log = _request_log[key_id]

    # Prune old entries
    _request_log[key_id] = [t for t in log if t > window_start]
    count = len(_request_log[key_id])

    if count >= limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {limit_per_minute} requests/min for your tier. "
                   "Upgrade to PRO or ENTERPRISE for higher limits.",
            headers={"Retry-After": "60"},
        )

    _request_log[key_id].append(now)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(
    raw_key: Annotated[str | None, Security(_api_key_header)],
) -> dict:
    """
    Validate the X-API-Key header. Raises 401/403/429 on failure.
    Returns the key record on success.
    """
    if raw_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include X-API-Key header.",
        )

    key_hash = _hash_key(raw_key)
    record = get_key_record(key_hash)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )

    if not record["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key has been revoked.",
        )

    _check_rate_limit(record["key_id"], record["rate_limit_per_minute"])
    _touch_key(key_hash)

    return record


# Convenience type alias for route signatures
ApiKeyDep = Annotated[dict, Depends(get_api_key)]
