"""
AETHERTRADE-SWARM — API Key Management Routes
POST   /api/v1/keys/generate   — create new API key (returns raw key once)
GET    /api/v1/keys/list        — list all keys (masked)
DELETE /api/v1/keys/{key_id}    — revoke key
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from api.auth import ApiKeyDep, create_api_key, list_keys, revoke_key
from config import get_settings
from models.schemas import (
    ApiKeyInfo,
    ApiKeyListResponse,
    GenerateKeyRequest,
    GenerateKeyResponse,
    KeyTier,
)

router = APIRouter(prefix="/api/v1/keys", tags=["keys"])
settings = get_settings()


@router.post(
    "/generate",
    response_model=GenerateKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate API key",
)
async def generate_key(
    request: GenerateKeyRequest,
) -> GenerateKeyResponse:
    """
    Generates a new API key. The raw key is returned once and never stored
    in plaintext. Store it securely — it cannot be retrieved later.

    Rate limits by tier:
    - FREE: 100 req/min
    - PRO: 1000 req/min
    - ENTERPRISE: 10000 req/min
    """
    rate_limits = {
        KeyTier.FREE: settings.rate_limit_free,
        KeyTier.PRO: settings.rate_limit_pro,
        KeyTier.ENTERPRISE: settings.rate_limit_enterprise,
    }

    raw_key, record = create_api_key(
        name=request.name,
        tier=request.tier,
        owner_email=request.owner_email,
        description=request.description,
    )

    return GenerateKeyResponse(
        key_id=record["key_id"],
        api_key=raw_key,
        name=record["name"],
        tier=record["tier"],
        rate_limit_per_minute=rate_limits[KeyTier(record["tier"])],
        created_at=datetime.fromisoformat(record["created_at"]),
    )


@router.get("/list", response_model=ApiKeyListResponse, summary="List API keys")
async def list_api_keys(
    _key: ApiKeyDep,
) -> ApiKeyListResponse:
    """
    Returns all API keys with masked prefixes. Full key values are never
    returned after initial creation.
    """
    all_keys = list_keys()
    key_infos = [
        ApiKeyInfo(
            key_id=k["key_id"],
            name=k["name"],
            tier=k["tier"],
            prefix=k["prefix"],
            owner_email=k["owner_email"],
            created_at=datetime.fromisoformat(k["created_at"]),
            last_used_at=datetime.fromisoformat(k["last_used_at"]) if k.get("last_used_at") else None,
            request_count=k["request_count"],
            is_active=k["is_active"],
        )
        for k in all_keys
    ]

    return ApiKeyListResponse(keys=key_infos, total=len(key_infos))


@router.delete("/{key_id}", status_code=status.HTTP_200_OK, summary="Revoke API key")
async def delete_key(
    key_id: str,
    _key: ApiKeyDep,
) -> dict:
    """
    Permanently revokes the specified API key. Any active sessions using
    this key will receive 403 on their next request.
    """
    success = revoke_key(key_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Key '{key_id}' not found.",
        )
    return {"revoked": True, "key_id": key_id}
