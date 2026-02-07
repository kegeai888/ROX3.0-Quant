import ccxt.async_support as ccxt
import ccxt as ccxt_sync
import asyncio
from typing import List, Dict, Any
from datetime import datetime
from .base import BaseDataProvider, PricePoint
import logging

logger = logging.getLogger("rox-crypto")

class CryptoProvider(BaseDataProvider):
    def __init__(self, exchange_id: str = 'binance'):
        self.exchange_id = exchange_id
        # Use sync client for simple calls, async for high throughput if needed
        try:
            self.exchange = getattr(ccxt_sync, exchange_id)()
            self.exchange.timeout = 5000  # 5s
            # Optional: Load markets on init? Might be slow.
            # self.exchange.load_markets() 
        except Exception as e:
            logger.error(f"Failed to init exchange {exchange_id}: {e}")
            self.exchange = None

    def get_history(self, symbol: str, days: int = 120, period: str = "daily") -> List[PricePoint]:
        if not self.exchange:
            return []
            
        # CCXT timeframe mapping
        timeframe = '1d'
        if period == 'weekly': timeframe = '1w'
        elif period == 'monthly': timeframe = '1M'
        elif period == 'hourly': timeframe = '1h'
        elif period == '15m': timeframe = '15m'
        elif period == '5m': timeframe = '5m'
        elif period == '1m': timeframe = '1m'

        try:
            # Calculate limit based on days (approx)
            limit = days
            if period == 'hourly': limit = days * 24
            
            # Fetch OHLCV
            # symbol format: "BTC/USDT"
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            res = []
            for candle in ohlcv:
                # [timestamp, open, high, low, close, volume]
                ts = candle[0]
                dt = datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M:%S')
                res.append(PricePoint(
                    date=dt,
                    open=float(candle[1]),
                    high=float(candle[2]),
                    low=float(candle[3]),
                    close=float(candle[4]),
                    volume=float(candle[5])
                ))
            return res
        except Exception as e:
            logger.error(f"Crypto history failed for {symbol}: {e}")
            return []

    def get_realtime_quote(self, symbol: str) -> Dict[str, Any]:
        if not self.exchange:
            return {}
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            # Ticker structure: 
            # {symbol, timestamp, datetime, high, low, bid, bidVolume, ask, askVolume, vwap, open, close, last, previousClose, change, percentage, average, baseVolume, quoteVolume, info}
            return {
                "price": ticker.get('last', 0.0),
                "open": ticker.get('open', 0.0),
                "high": ticker.get('high', 0.0),
                "low": ticker.get('low', 0.0),
                "volume": ticker.get('baseVolume', 0.0), # or quoteVolume
                "time": ticker.get('datetime', ''),
                "change": ticker.get('change', 0.0),
                "change_pct": ticker.get('percentage', 0.0)
            }
        except Exception as e:
            logger.error(f"Crypto quote failed for {symbol}: {e}")
            return {}

    def search_symbols(self, query: str) -> List[Dict[str, str]]:
        if not self.exchange:
            return []
        try:
            if not self.exchange.markets:
                self.exchange.load_markets()
            
            q = query.upper()
            results = []
            count = 0
            for symbol in self.exchange.symbols:
                if q in symbol:
                    results.append({"code": symbol, "name": symbol})
                    count += 1
                    if count >= 20: break
            return results
        except Exception as e:
            return []
