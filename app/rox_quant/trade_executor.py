import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, List

logger = logging.getLogger("rox-trader")

class BaseTrader(ABC):
    """
    交易执行器基类 (Abstract Base Class)
    定义了实盘/模拟盘的标准接口
    """
    
    @abstractmethod
    def connect(self, **kwargs) -> bool:
        """连接交易账户"""
        pass

    @abstractmethod
    def get_balance(self) -> Dict[str, float]:
        """获取资金状况: {total, available, market_value}"""
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict]:
        """获取持仓列表"""
        pass

    @abstractmethod
    def buy(self, security: str, price: float, amount: int) -> Dict:
        """买入接口"""
        pass

    @abstractmethod
    def sell(self, security: str, price: float, amount: int) -> Dict:
        """卖出接口"""
        pass

class EasyTraderAdapter(BaseTrader):
    """
    EasyTrader 适配器
    封装 easytrader 的调用逻辑
    """
    def __init__(self, broker: str = 'ths', read_only: bool = True):
        self.user = None
        self.broker = broker
        self.read_only = read_only
        self._is_connected = False

    def connect(self, client_path: str = None, **kwargs) -> bool:
        try:
            import easytrader
            # 支持: ths (同花顺), yh (银河), xq (雪球), etc.
            self.user = easytrader.use(self.broker)
            
            # 连接客户端
            if self.broker == 'xq':
                # 雪球需要 user.prepare('user.json') 或 user.prepare(user='...', password='...')
                # 为了安全，建议使用 cookie 文件
                # kwargs: {'config_path': 'xq.json'}
                config = kwargs.get('config_path', 'xq.json')
                self.user.prepare(config)
            elif client_path:
                self.user.connect(client_path)
            else:
                # 尝试自动查找或无需路径
                self.user.connect()
                
            self._is_connected = True
            logger.info(f"EasyTrader connected to {self.broker} (ReadOnly: {self.read_only})")
            return True
        except ImportError:
            logger.error("easytrader module not found. Please pip install easytrader")
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def get_balance(self) -> Dict[str, float]:
        if not self._is_connected: return {}
        try:
            # easytrader 返回格式通常为列表或字典
            balance = self.user.balance
            # 标准化返回格式
            if isinstance(balance, list) and len(balance) > 0:
                data = balance[0]
                return {
                    "total": float(data.get('资产总值', 0)),
                    "available": float(data.get('可用金额', 0)),
                    "market_value": float(data.get('证券市值', 0))
                }
            return {}
        except Exception as e:
            logger.error(f"Get balance error: {e}")
            return {}

    def get_positions(self) -> List[Dict]:
        if not self._is_connected: return []
        try:
            return self.user.position
        except Exception as e:
            logger.error(f"Get position error: {e}")
            return []

    def buy(self, security: str, price: float, amount: int) -> Dict:
        if not self._is_connected: return {"status": "error", "msg": "Not connected"}
        if self.read_only:
            logger.warning(f"[READ-ONLY] Blocked BUY request: {security}, {amount} @ {price}")
            return {"status": "blocked", "msg": "Read-only mode enabled"}
            
        try:
            logger.info(f"Executing BUY: {security}, {amount} shares @ {price}")
            # easytrader 接口: user.buy('162411', price=0.55, amount=100)
            res = self.user.buy(security, price=price, amount=amount)
            return {"status": "sent", "raw": res}
        except Exception as e:
            return {"status": "error", "msg": str(e)}

    def sell(self, security: str, price: float, amount: int) -> Dict:
        if not self._is_connected: return {"status": "error", "msg": "Not connected"}
        if self.read_only:
            logger.warning(f"[READ-ONLY] Blocked SELL request: {security}, {amount} @ {price}")
            return {"status": "blocked", "msg": "Read-only mode enabled"}
            
        try:
            logger.info(f"Executing SELL: {security}, {amount} shares @ {price}")
            res = self.user.sell(security, price=price, amount=amount)
            return {"status": "sent", "raw": res}
        except Exception as e:
            return {"status": "error", "msg": str(e)}

class MockTrader(BaseTrader):
    """
    模拟交易器 (用于开发测试)
    """
    def connect(self, **kwargs):
        return True
        
    def get_balance(self):
        return {"total": 100000.0, "available": 50000.0, "market_value": 50000.0}
        
    def get_positions(self):
        return [{"stock_code": "000001", "stock_name": "平安银行", "current_amount": 1000, "cost_price": 10.5, "market_value": 10800}]
        
    def buy(self, security, price, amount):
        logger.info(f"[MOCK] Buying {security}: {amount} @ {price}")
        return {"status": "mock_success"}
        
    def sell(self, security, price, amount):
        logger.info(f"[MOCK] Selling {security}: {amount} @ {price}")
        return {"status": "mock_success"}

# 工厂模式
def get_trader(mode: str = 'mock', **kwargs) -> BaseTrader:
    if mode == 'real':
        # Load from environment variables if not provided
        import os
        read_only = kwargs.get('read_only', os.getenv('EASYTRADER_READ_ONLY', 'True').lower() == 'true')
        broker = kwargs.get('broker', os.getenv('EASYTRADER_BROKER', 'ths'))
        
        # Log configuration status
        logger.info(f"Initializing Real Trader: Broker={broker}, ReadOnly={read_only}")
        
        return EasyTraderAdapter(broker=broker, read_only=read_only)
    return MockTrader()
