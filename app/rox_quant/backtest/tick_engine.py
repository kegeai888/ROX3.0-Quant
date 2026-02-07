import pandas as pd
import numpy as np
from typing import List, Dict, Callable, Optional, Generator
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class Tick:
    symbol: str
    timestamp: datetime
    price: float
    volume: float
    bid1: float
    ask1: float
    bid1_vol: float
    ask1_vol: float

class TickGenerator:
    """
    Synthesizes ticks from OHLCV data for backtesting.
    Standard: 4 ticks per minute (Open, High/Low, Low/High, Close).
    HighFidelity: Geometric Brownian Motion interpolation (TODO).
    """
    @staticmethod
    def from_kline(df: pd.DataFrame, ticks_per_bar: int = 4) -> Generator[Tick, None, None]:
        """
        Yields Tick objects from a K-line DataFrame.
        DF must have 'date', 'open', 'high', 'low', 'close', 'volume'.
        """
        for _, row in df.iterrows():
            ts_start = row['date'] if isinstance(row['date'], datetime) else pd.to_datetime(row['date'])
            o, h, l, c = row['open'], row['high'], row['low'], row['close']
            vol = row['volume'] / ticks_per_bar
            
            # Simple Logic: O -> L -> H -> C or O -> H -> L -> C depending on candle color
            # Just mimicking volatility.
            
            # Minute Candle split into 4 timestamps
            delta = timedelta(seconds=60 / ticks_per_bar)
            
            # Points: Open, Low, High, Close (Bullish assumption for simplicity order)
            # Better: if Close > Open, go O -> L -> H -> C. Else O -> H -> L -> C.
            if c >= o:
                path = [o, l, h, c]
            else:
                path = [o, h, l, c]
                
            for i, price in enumerate(path):
                t = ts_start + delta * i
                # Simulate spread (0.1%)
                spread = price * 0.001
                yield Tick(
                    symbol="UNKNOWN",
                    timestamp=t,
                    price=price,
                    volume=vol,
                    bid1=price - spread/2,
                    ask1=price + spread/2,
                    bid1_vol=vol * 5, # ample depth
                    ask1_vol=vol * 5
                )

class OrderBook:
    """
    Simulated Limit Order Book (L2).
    """
    def __init__(self):
        self.bids = {} # price -> volume
        self.asks = {} 
        self.best_bid = 0.0
        self.best_ask = 0.0

    def update(self, tick: Tick):
        self.best_bid = tick.bid1
        self.best_ask = tick.ask1
        # Simple simulation: infinite depth at best prices
        self.bids[self.best_bid] = tick.bid1_vol
        self.asks[self.best_ask] = tick.ask1_vol

class TickEngine:
    """
    Event-driven Tick Backtest Engine.
    """
    def __init__(self):
        self.subscribers: List[Callable[[Tick], None]] = []
        self.order_book = OrderBook()
        self.current_time = None
        
    def add_strategy(self, strategy_callback):
        self.subscribers.append(strategy_callback)
        
    def run(self, ticks: Generator[Tick, None, None]):
        """
        Run the event loop.
        """
        count = 0
        for tick in ticks:
            self.current_time = tick.timestamp
            self.order_book.update(tick)
            
            # Notify strategies
            for sub in self.subscribers:
                sub(tick, self.order_book)
            
            count += 1
        return count
