import logging
from typing import List, Dict
from dataclasses import dataclass

logger = logging.getLogger("rox-copytrade")

@dataclass
class Signal:
    source_id: str
    symbol: str
    side: str # buy/sell
    price: float
    time: str

class SignalSource:
    """
    Abstract source of trading signals.
    """
    def __init__(self, source_id: str):
        self.source_id = source_id
        
    def get_latest_signal(self) -> Signal:
        raise NotImplementedError

class MockUserSource(SignalSource):
    """
    Simulates a 'Guru' user sending signals.
    """
    def get_latest_signal(self) -> Signal:
        # In reality, this would query DB for latest trade from this user
        import random
        from datetime import datetime
        if random.random() > 0.8:
            return Signal(
                source_id=self.source_id,
                symbol="BTC/USDT",
                side="buy",
                price=95000.0,
                time=datetime.now().isoformat()
            )
        return None

class CopyEngine:
    """
    Executes trades based on signals.
    """
    def __init__(self):
        self.sources: Dict[str, SignalSource] = {}
        self.active = False
        
    def follow(self, source_id: str):
        self.sources[source_id] = MockUserSource(source_id)
        logger.info(f"Following {source_id}")
        
    def check_signals(self) -> List[Signal]:
        signals = []
        for src in self.sources.values():
            sig = src.get_latest_signal()
            if sig:
                signals.append(sig)
                logger.info(f"COPY TRADE: Received signal {sig} from {src.source_id}")
        return signals

# Singleton
copy_engine = CopyEngine()
