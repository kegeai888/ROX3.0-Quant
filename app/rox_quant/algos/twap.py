from abc import ABC, abstractmethod
from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.rox_quant.backtest.tick_engine import Tick, OrderBook

class BaseAlgo(ABC):
    """
    Abstract Base Class for Execution Algorithms.
    """
    def __init__(self, symbol: str, side: str, quantity: float):
        self.symbol = symbol
        self.side = side # 'buy' or 'sell'
        self.quantity = quantity
        self.filled_qty = 0.0
        self.orders = []
        self.status = "pending" # pending, running, finished

    @abstractmethod
    def on_tick(self, tick: Tick, book: OrderBook):
        pass

class TWAPAlgo(BaseAlgo):
    """
    Time-Weighted Average Price Algorithm.
    Splits order evenly over a duration.
    """
    def __init__(self, symbol: str, side: str, total_quantity: float, start_time: datetime, end_time: datetime, slices: int = 10):
        super().__init__(symbol, side, total_quantity)
        self.start_time = start_time
        self.end_time = end_time
        self.slices = slices
        self.slice_qty = total_quantity / slices
        self.slice_interval = (end_time - start_time) / slices
        self.next_slice_time = start_time
        self.slice_count = 0
        
    def on_tick(self, tick: Tick, book: OrderBook):
        if self.filled_qty >= self.quantity:
            self.status = "finished"
            return

        if tick.timestamp >= self.next_slice_time and self.slice_count < self.slices:
            # Execute one slice
            price = book.best_ask if self.side == 'buy' else book.best_bid
            
            # Record Simulation
            # In a real engine, this would send an order and wait for callback.
            # Here we simulate immediate fill for simplicity (impact model omitted).
            self.filled_qty += self.slice_qty
            self.orders.append({
                "time": tick.timestamp,
                "price": price,
                "qty": self.slice_qty,
                "side": self.side
            })
            
            self.current_slice_done = True
            self.slice_count += 1
            self.next_slice_time += self.slice_interval
            
            # print(f"[TWAP] Slice {self.slice_count}/{self.slices} Filled: {self.slice_qty} @ {price}")
