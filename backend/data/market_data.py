"""
AetherTrade-Swarm — Market Data Layer
Fetches real market data from yfinance and CoinGecko.
Stores daily OHLCV in Supabase for strategy pods to consume.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import numpy as np

logger = logging.getLogger("aethertrade.market_data")

# Default universe across all pods
EQUITY_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "NFLX",
    "JPM", "GS", "BAC", "V", "UNH", "JNJ", "PG", "HD",
]
ETF_UNIVERSE = ["SPY", "QQQ", "IWM", "DIA", "XLF", "XLE", "XLK", "GLD", "TLT", "USO", "EEM", "HYG"]
CRYPTO_UNIVERSE = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"]
FULL_UNIVERSE = EQUITY_UNIVERSE + ETF_UNIVERSE + CRYPTO_UNIVERSE

# In-memory cache for current session
_price_cache: dict[str, dict[str, Any]] = {}
_cache_expiry: dict[str, datetime] = {}
CACHE_TTL_SECONDS = 300  # 5 min


class MarketDataService:
    """Fetches and caches real market data."""

    def __init__(self, supabase_client: Any = None) -> None:
        self._db = supabase_client

    def fetch_daily(
        self,
        symbol: str,
        period: str = "1y",
    ) -> dict[str, Any]:
        """Fetch daily OHLCV for a symbol via yfinance."""
        cache_key = f"{symbol}:{period}"
        now = datetime.now(tz=timezone.utc)

        if cache_key in _price_cache and _cache_expiry.get(cache_key, now) > now:
            return _price_cache[cache_key]

        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)

            if hist.empty:
                logger.warning("No data for %s", symbol)
                return {"symbol": symbol, "data": [], "error": "No data available"}

            data = []
            for date, row in hist.iterrows():
                data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": round(float(row["Open"]), 4),
                    "high": round(float(row["High"]), 4),
                    "low": round(float(row["Low"]), 4),
                    "close": round(float(row["Close"]), 4),
                    "volume": int(row["Volume"]),
                })

            result = {
                "symbol": symbol,
                "period": period,
                "count": len(data),
                "data": data,
                "last_close": data[-1]["close"] if data else None,
                "fetched_at": now.isoformat(),
            }

            _price_cache[cache_key] = result
            _cache_expiry[cache_key] = now + timedelta(seconds=CACHE_TTL_SECONDS)
            return result

        except ImportError:
            logger.error("yfinance not installed")
            return {"symbol": symbol, "data": [], "error": "yfinance not installed"}
        except Exception as exc:
            logger.error("fetch_daily %s: %s", symbol, exc)
            return {"symbol": symbol, "data": [], "error": str(exc)}

    def fetch_batch(
        self,
        symbols: list[str] | None = None,
        period: str = "6mo",
    ) -> dict[str, dict[str, Any]]:
        """Fetch daily data for multiple symbols."""
        symbols = symbols or FULL_UNIVERSE
        results = {}
        for sym in symbols:
            results[sym] = self.fetch_daily(sym, period)
        return results

    def get_returns(
        self,
        symbol: str,
        period: str = "1y",
    ) -> np.ndarray:
        """Get daily log returns for a symbol."""
        data = self.fetch_daily(symbol, period)
        closes = [d["close"] for d in data.get("data", []) if d.get("close")]
        if len(closes) < 2:
            return np.array([])
        prices = np.array(closes)
        return np.diff(np.log(prices))

    def get_multi_returns(
        self,
        symbols: list[str] | None = None,
        period: str = "1y",
    ) -> dict[str, np.ndarray]:
        """Get returns for multiple symbols."""
        symbols = symbols or ETF_UNIVERSE[:5]
        return {sym: self.get_returns(sym, period) for sym in symbols}

    def get_current_prices(
        self,
        symbols: list[str] | None = None,
    ) -> dict[str, float]:
        """Get latest closing prices."""
        symbols = symbols or FULL_UNIVERSE
        prices = {}
        for sym in symbols:
            data = self.fetch_daily(sym, "5d")
            if data.get("last_close"):
                prices[sym] = data["last_close"]
        return prices

    def store_daily_to_supabase(
        self,
        symbol: str,
        period: str = "1y",
    ) -> int:
        """Fetch and store daily data in Supabase market_data_daily table."""
        if not self._db:
            return 0

        data = self.fetch_daily(symbol, period)
        rows = []
        for d in data.get("data", []):
            rows.append({
                "symbol": symbol,
                "date": d["date"],
                "open": d["open"],
                "high": d["high"],
                "low": d["low"],
                "close": d["close"],
                "volume": d["volume"],
                "source": "yfinance",
            })

        if not rows:
            return 0

        try:
            self._db.table("market_data_daily").upsert(
                rows, on_conflict="symbol,date"
            ).execute()
            logger.info("Stored %d rows for %s", len(rows), symbol)
            return len(rows)
        except Exception as exc:
            logger.error("store_daily %s: %s", symbol, exc)
            return 0

    def backfill_universe(self, period: str = "1y") -> dict[str, int]:
        """Backfill all universe symbols to Supabase."""
        results = {}
        for sym in FULL_UNIVERSE:
            count = self.store_daily_to_supabase(sym, period)
            results[sym] = count
        return results


class CryptoDataService:
    """Fetches crypto data from CoinGecko (free API)."""

    BASE_URL = "https://api.coingecko.com/api/v3"
    COIN_MAP = {
        "BTC-USD": "bitcoin",
        "ETH-USD": "ethereum",
        "SOL-USD": "solana",
        "BNB-USD": "binancecoin",
    }

    def fetch_prices(self, coins: list[str] | None = None) -> dict[str, float]:
        """Fetch current crypto prices in USD."""
        coins = coins or list(self.COIN_MAP.keys())
        ids = [self.COIN_MAP.get(c, c.lower().replace("-usd", "")) for c in coins]

        try:
            import httpx
            resp = httpx.get(
                f"{self.BASE_URL}/simple/price",
                params={"ids": ",".join(ids), "vs_currencies": "usd"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            result = {}
            for coin, cg_id in zip(coins, ids):
                if cg_id in data:
                    result[coin] = data[cg_id].get("usd", 0)
            return result
        except Exception as exc:
            logger.error("CoinGecko fetch: %s", exc)
            return {}


# Singletons
_market_data_service: MarketDataService | None = None
_crypto_service: CryptoDataService | None = None


def get_market_data_service(supabase_client: Any = None) -> MarketDataService:
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService(supabase_client)
    return _market_data_service


def get_crypto_service() -> CryptoDataService:
    global _crypto_service
    if _crypto_service is None:
        _crypto_service = CryptoDataService()
    return _crypto_service
