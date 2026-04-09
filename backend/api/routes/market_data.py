"""
AetherTrade-Swarm — Market Data API Routes
Real price data from yfinance + CoinGecko.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from data.market_data import get_market_data_service, get_crypto_service, FULL_UNIVERSE

router = APIRouter(prefix="/api/v1/market-data", tags=["market-data"])


@router.get("/{symbol}", summary="Get daily OHLCV for a symbol")
async def get_symbol_data(symbol: str, period: str = Query("6mo", regex="^(1mo|3mo|6mo|1y|2y|5y|max)$")):
    svc = get_market_data_service()
    return svc.fetch_daily(symbol.upper(), period)


@router.get("/batch/prices", summary="Get current prices for multiple symbols")
async def get_batch_prices(symbols: str = Query(None, description="Comma-separated symbols")):
    svc = get_market_data_service()
    sym_list = [s.strip().upper() for s in symbols.split(",")] if symbols else FULL_UNIVERSE[:20]
    return svc.get_current_prices(sym_list)


@router.get("/crypto/prices", summary="Get crypto prices from CoinGecko")
async def get_crypto_prices():
    svc = get_crypto_service()
    return svc.fetch_prices()
