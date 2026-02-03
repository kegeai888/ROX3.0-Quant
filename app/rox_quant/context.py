from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class Portfolio:
    cash: float
    positions: Dict[str, int] = field(default_factory=dict) # symbol -> shares
    total_value: float = 0.0
    market_value: float = 0.0
    
    def update(self, current_prices: Dict[str, float]):
        self.market_value = 0.0
        for symbol, shares in self.positions.items():
            price = current_prices.get(symbol, 0.0)
            self.market_value += shares * price
        self.total_value = self.cash + self.market_value

@dataclass
class Context:
    portfolio: Portfolio
    config: Dict[str, Any] = field(default_factory=dict)
    now: Any = None # datetime or str
    data: Any = None # Current snapshot data
    
    # 策略运行时的临时变量
    user_data: Dict[str, Any] = field(default_factory=dict)

    def __init__(self, initial_capital: float, config: Dict[str, Any] = None):
        self.portfolio = Portfolio(cash=initial_capital, total_value=initial_capital)
        self.config = config or {}
