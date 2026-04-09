"""
AETHERTRADE-SWARM — Supabase Database Client
Async-compatible Supabase client with graceful fallback for development.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger("oracle.database")


class InMemoryStore:
    """
    Fallback in-memory store when Supabase is not configured.
    Used in development / demo mode.
    """

    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {
            "api_keys": [],
            "regime_history": [],
            "risk_alerts": [],
        }

    def table(self, name: str) -> "InMemoryTable":
        if name not in self._tables:
            self._tables[name] = []
        return InMemoryTable(self._tables[name])


class InMemoryTable:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self._data = data
        self._filters: list[tuple[str, Any]] = []
        self._limit_n: int | None = None
        self._order_col: str | None = None
        self._order_desc: bool = False

    def insert(self, record: dict[str, Any]) -> "InMemoryTable":
        self._data.append(record)
        return self

    def select(self, columns: str = "*") -> "InMemoryTable":
        return self

    def eq(self, column: str, value: Any) -> "InMemoryTable":
        self._filters.append((column, value))
        return self

    def order(self, column: str, desc: bool = False) -> "InMemoryTable":
        self._order_col = column
        self._order_desc = desc
        return self

    def limit(self, n: int) -> "InMemoryTable":
        self._limit_n = n
        return self

    def delete(self) -> "InMemoryTable":
        # Applied on execute
        return self

    def update(self, record: dict[str, Any]) -> "InMemoryTable":
        for item in self._data:
            match = all(item.get(col) == val for col, val in self._filters)
            if match:
                item.update(record)
        return self

    def execute(self) -> "InMemoryResult":
        result = list(self._data)
        for col, val in self._filters:
            result = [r for r in result if r.get(col) == val]
        if self._order_col:
            result.sort(key=lambda x: x.get(self._order_col, ""), reverse=self._order_desc)
        if self._limit_n is not None:
            result = result[: self._limit_n]
        return InMemoryResult(result)


class InMemoryResult:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class DatabaseClient:
    """
    Thin wrapper around supabase-py with in-memory fallback.
    """

    def __init__(self, url: str, key: str) -> None:
        self._client = None
        self._fallback = InMemoryStore()
        self._use_fallback = False

        if url.startswith("https://placeholder") or not key or key == "placeholder_key":
            logger.warning(
                "Supabase credentials not configured — using in-memory store. "
                "Set SUPABASE_URL and SUPABASE_KEY in .env for persistence."
            )
            self._use_fallback = True
            return

        try:
            from supabase import create_client, Client  # type: ignore

            self._client: Client = create_client(url, key)
            logger.info("Supabase client initialised (url=%s)", url[:30])
        except Exception as exc:
            logger.warning("Failed to connect to Supabase (%s) — using in-memory store.", exc)
            self._use_fallback = True

    @property
    def is_fallback(self) -> bool:
        return self._use_fallback

    def table(self, name: str) -> Any:
        if self._use_fallback:
            return self._fallback.table(name)
        return self._client.table(name)

    # ------------------------------------------------------------------
    # High-level helpers
    # ------------------------------------------------------------------

    async def upsert_api_key(self, record: dict[str, Any]) -> None:
        if self._use_fallback:
            existing = [k for k in self._fallback._tables["api_keys"] if k["key_id"] == record["key_id"]]
            if existing:
                existing[0].update(record)
            else:
                self._fallback._tables["api_keys"].append(record)
            return
        self._client.table("api_keys").upsert(record).execute()

    async def get_api_key(self, key_hash: str) -> dict[str, Any] | None:
        if self._use_fallback:
            matches = [k for k in self._fallback._tables["api_keys"] if k.get("key_hash") == key_hash and k.get("is_active")]
            return matches[0] if matches else None
        result = (
            self._client.table("api_keys")
            .select("*")
            .eq("key_hash", key_hash)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    async def list_api_keys(self) -> list[dict[str, Any]]:
        if self._use_fallback:
            return list(self._fallback._tables["api_keys"])
        result = self._client.table("api_keys").select("*").order("created_at", desc=True).execute()
        return result.data or []

    async def deactivate_api_key(self, key_id: str) -> bool:
        if self._use_fallback:
            found = False
            for k in self._fallback._tables["api_keys"]:
                if k.get("key_id") == key_id:
                    k["is_active"] = False
                    found = True
            return found
        self._client.table("api_keys").update({"is_active": False}).eq("key_id", key_id).execute()
        return True

    async def increment_key_usage(self, key_id: str) -> None:
        if self._use_fallback:
            for k in self._fallback._tables["api_keys"]:
                if k.get("key_id") == key_id:
                    k["request_count"] = k.get("request_count", 0) + 1
                    k["last_used_at"] = datetime.now(timezone.utc).isoformat()
            return
        # Use RPC for atomic increment in production
        try:
            self._client.rpc("increment_key_usage", {"p_key_id": key_id}).execute()
        except Exception:
            pass  # Non-critical

    async def store_regime_transition(self, record: dict[str, Any]) -> None:
        if self._use_fallback:
            self._fallback._tables["regime_history"].append(record)
            return
        self._client.table("regime_history").insert(record).execute()

    async def get_regime_history(self, limit: int = 50) -> list[dict[str, Any]]:
        if self._use_fallback:
            data = sorted(
                self._fallback._tables["regime_history"],
                key=lambda x: x.get("timestamp", ""),
                reverse=True,
            )
            return data[:limit]
        result = (
            self._client.table("regime_history")
            .select("*")
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []


# Module-level singleton — initialised in lifespan
_db_client: DatabaseClient | None = None


def init_db(url: str, key: str) -> DatabaseClient:
    global _db_client
    _db_client = DatabaseClient(url, key)
    return _db_client


def get_db() -> DatabaseClient:
    if _db_client is None:
        raise RuntimeError("Database client not initialised. Call init_db() first.")
    return _db_client
