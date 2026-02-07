from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class PricePoint:
    date: str
    close: float
    volume: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None

class BaseDataProvider(ABC):
    """
    Abstract interface for data providers (AShare, Crypto, US Stock, etc.)
    """

    @abstractmethod
    def get_history(self, symbol: str, days: int = 120, period: str = "daily") -> List[PricePoint]:
        """Fetch historical K-line data."""
        pass

    @abstractmethod
    def get_realtime_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch real-time quote.
        Returns:
            {
                "price": float,
                "open": float,
                "high": float,
                "low": float,
                "volume": float,
                "time": str,
                "change": float, # Optional
                "change_pct": float # Optional
            }
        """
        pass

    @abstractmethod
    def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """
        Search for symbols.
        Returns: [{"code": "BTC/USDT", "name": "Bitcoin"}]
        """
        pass
