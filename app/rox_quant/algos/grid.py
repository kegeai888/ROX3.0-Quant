from typing import List, Dict
from app.rox_quant.backtest.tick_engine import Tick, OrderBook
from .twap import BaseAlgo

class GridAlgo(BaseAlgo):
    """
    Classic Grid Trading Algorithm.
    """
    def __init__(self, symbol: str, initial_price: float, lower_limit: float, upper_limit: float, grid_num: int, inv_per_grid: float):
        super().__init__(symbol, "mixed", grid_num * inv_per_grid)
        self.initial_price = initial_price
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit
        self.grid_num = grid_num
        self.inv_per_grid = inv_per_grid
        
        # Calculate Grid Lines
        self.grid_step = (upper_limit - lower_limit) / grid_num
        self.grids = [lower_limit + i * self.grid_step for i in range(grid_num + 1)]
        self.active_orders = [] # Simulated list of active orders
        self.positions = []
        
        self._init_grids(initial_price)

    def _init_grids(self, current_price):
        """Place initial buy orders below current and sell orders above."""
        self.active_orders = []
        for level in self.grids:
            if level < current_price:
                # Buy order at this level
                self.active_orders.append({"price": level, "side": "buy", "qty": self.inv_per_grid / level})
            elif level > current_price:
                # Sell order? Only if we have position. For init, maybe just skip.
                pass
                
    def on_tick(self, tick: Tick, book: OrderBook):
        # Check for fills
        current_price = tick.price
        
        new_orders = []
        for order in self.active_orders:
            filled = False
            
            if order['side'] == 'buy' and current_price <= order['price']:
                # Buy Filled
                # print(f"[GRID] BUY Filled @ {order['price']:.2f}")
                self.positions.append({"price": order['price'], "qty": order['qty']})
                self.orders.append({"time": tick.timestamp, "side": "buy", "price": order['price'], "qty": order['qty']})
                
                # Place Sell Order one grid up
                sell_price = order['price'] + self.grid_step
                new_orders.append({"price": sell_price, "side": "sell", "qty": order['qty']})
                filled = True
                
            elif order['side'] == 'sell' and current_price >= order['price']:
                # Sell Filled
                # print(f"[GRID] SELL Filled @ {order['price']:.2f}")
                self.orders.append({"time": tick.timestamp, "side": "sell", "price": order['price'], "qty": order['qty']})
                
                # Place Buy Order one grid down
                buy_price = order['price'] - self.grid_step
                new_orders.append({"price": buy_price, "side": "buy", "qty": order['qty']})
                filled = True
                
            if not filled:
                new_orders.append(order)
                
        self.active_orders = new_orders
