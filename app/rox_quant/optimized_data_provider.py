"""
优化的数据提供器 - 减少重复API调用，提高性能
"""

import asyncio
import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import akshare as ak
from concurrent.futures import ThreadPoolExecutor
import time

logger = logging.getLogger(__name__)

@dataclass
class PricePoint:
    date: str
    close: float
    volume: Optional[float] = None

@dataclass
class StockData:
    symbol: str
    data: pd.DataFrame
    last_update: datetime
    ttl_seconds: int = 300  # 5分钟缓存

    def is_expired(self) -> bool:
        return datetime.now() - self.last_update > timedelta(seconds=self.ttl_seconds)

class OptimizedDataProvider:
    """高性能数据提供器，支持缓存和批量处理"""
    
    def __init__(self, 
                 cache_ttl: int = 300,
                 max_workers: int = 4,
                 enable_bulk_fetch: bool = True):
        
        self.cache_ttl = cache_ttl
        self.enable_bulk_fetch = enable_bulk_fetch
        self._cache: Dict[str, StockData] = {}
        self._cache_lock = asyncio.Lock()
        
        # 线程池用于CPU密集型操作
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 批量请求队列
        self._bulk_queue: Dict[str, asyncio.Future] = {}
        self._bulk_timer: Optional[asyncio.Task] = None
        
        logger.info(f"OptimizedDataProvider initialized with cache_ttl={cache_ttl}s")
    
    async def _get_from_cache(self, key: str) -> Optional[pd.DataFrame]:
        """从缓存获取数据"""
        async with self._cache_lock:
            if key in self._cache and not self._cache[key].is_expired():
                logger.debug(f"Cache hit for {key}")
                return self._cache[key].data.copy()
            return None
    
    async def _set_cache(self, key: str, data: pd.DataFrame, ttl: Optional[int] = None) -> None:
        """设置缓存"""
        async with self._cache_lock:
            self._cache[key] = StockData(
                symbol=key,
                data=data.copy(),
                last_update=datetime.now(),
                ttl_seconds=ttl or self.cache_ttl
            )
            logger.debug(f"Cached data for {key}, cache size: {len(self._cache)}")
    
    async def _bulk_fetch_worker(self):
        """批量获取工作器"""
        await asyncio.sleep(0.1)  # 等待100ms收集请求
        
        if not self._bulk_queue:
            return
        
        # 获取当前队列中的所有请求
        symbols = list(self._bulk_queue.keys())
        futures = list(self._bulk_queue.values())
        self._bulk_queue.clear()
        
        logger.info(f"Bulk fetching {len(symbols)} symbols: {symbols}")
        
        try:
            # 批量获取数据
            tasks = [self._fetch_single_stock_data(symbol) for symbol in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果并通知等待的协程
            for symbol, result, future in zip(symbols, results, futures):
                if isinstance(result, Exception):
                    logger.error(f"Failed to fetch {symbol}: {result}")
                    future.set_exception(result)
                else:
                    future.set_result(result)
        
        except Exception as e:
            logger.error(f"Bulk fetch error: {e}")
            for future in futures:
                future.set_exception(e)
    
    async def _fetch_single_stock_data(self, symbol: str, days: int = 120) -> pd.DataFrame:
        """获取单只股票数据"""
        try:
            # 使用akshare获取历史数据
            df = ak.stock_zh_a_hist(symbol=symbol, adjust="qfq")
            
            if df is None or df.empty:
                logger.warning(f"No data returned for {symbol}, using synthetic data")
                return self._generate_synthetic_data(days)
            
            # 标准化列名
            df.columns = [col.lower() for col in df.columns]
            
            # 确保必要的列存在
            required_cols = ['日期', '收盘', '成交量', '开盘', '最高', '最低']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                logger.warning(f"Missing columns for {symbol}: {missing_cols}")
                return self._generate_synthetic_data(days)
            
            # 按日期排序并限制数据量
            df = df.tail(days).copy()
            
            # 数据类型转换和清理
            df['日期'] = pd.to_datetime(df['日期'])
            numeric_cols = ['收盘', '成交量', '开盘', '最高', '最低']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 移除无效数据
            df = df.dropna(subset=['收盘'])
            
            logger.debug(f"Fetched {len(df)} records for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return self._generate_synthetic_data(days)
    
    def _generate_synthetic_data(self, days: int) -> pd.DataFrame:
        """生成合成数据作为后备"""
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
        base_price = 10.0
        
        # 生成随机价格数据
        returns = np.random.normal(0.001, 0.02, days)  # 平均0.1%日收益，2%波动率
        prices = [base_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # 生成OHLC数据
        data = {
            '日期': dates,
            '开盘': prices,
            '最高': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            '最低': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            '收盘': prices,
            '成交量': np.random.randint(100000, 1000000, days)
        }
        
        df = pd.DataFrame(data)
        logger.warning(f"Generated synthetic data for {days} days")
        return df
    
    async def get_history(self, symbol: str, days: int = 120) -> List[PricePoint]:
        """获取历史价格数据（主要接口）"""
        cache_key = f"history_{symbol}_{days}"
        
        # 检查缓存
        cached_data = await self._get_from_cache(cache_key)
        if cached_data is not None:
            return self._convert_to_price_points(cached_data)
        
        # 批量获取或单个获取
        if self.enable_bulk_fetch:
            # 添加到批量队列
            if symbol not in self._bulk_queue:
                future = asyncio.Future()
                self._bulk_queue[symbol] = future
                
                # 启动批量定时器
                if self._bulk_timer is None or self._bulk_timer.done():
                    self._bulk_timer = asyncio.create_task(self._bulk_fetch_worker())
                
                data = await future
            else:
                data = await self._bulk_queue[symbol]
        else:
            data = await self._fetch_single_stock_data(symbol, days)
        
        # 缓存结果
        await self._set_cache(cache_key, data)
        
        return self._convert_to_price_points(data)
    
    def _convert_to_price_points(self, df: pd.DataFrame) -> List[PricePoint]:
        """转换DataFrame为PricePoint列表"""
        if df.empty:
            return []
        
        # 获取最近的数据
        df_sorted = df.sort_values('日期', ascending=False)
        
        price_points = []
        for _, row in df_sorted.iterrows():
            price_point = PricePoint(
                date=row['日期'].strftime('%Y-%m-%d') if isinstance(row['日期'], pd.Timestamp) else str(row['日期']),
                close=float(row['收盘']),
                volume=float(row['成交量']) if pd.notna(row['成交量']) else None
            )
            price_points.append(price_point)
        
        return price_points
    
    async def get_history_k(self, symbol: str, period: str = "daily", limit: int = 120) -> List[PricePoint]:
        """获取K线数据"""
        cache_key = f"kline_{symbol}_{period}_{limit}"
        
        # 检查缓存
        cached_data = await self._get_from_cache(cache_key)
        if cached_data is not None:
            return self._convert_to_price_points(cached_data)
        
        try:
            # 获取K线数据
            p = "daily" if period not in ["daily", "weekly", "monthly"] else period
            df = ak.stock_zh_a_hist(symbol=symbol, adjust="qfq", period=p)
            
            if df is None or df.empty:
                return await self.get_history(symbol, days=limit)
            
            if limit:
                df = df.tail(limit)
            
            # 标准化数据
            df.columns = [col.lower() for col in df.columns]
            
            # 缓存结果
            await self._set_cache(cache_key, df)
            
            return self._convert_to_price_points(df)
            
        except Exception as e:
            logger.error(f"Error getting K-line data for {symbol}: {e}")
            return await self.get_history(symbol, days=limit)
    
    async def get_spot_price(self, symbol: str) -> Optional[float]:
        """获取实时价格"""
        cache_key = f"spot_{symbol}"
        
        # 检查缓存（实时数据缓存时间较短）
        cached_data = await self._get_from_cache(cache_key)
        if cached_data is not None and not cached_data.empty:
            latest_price = cached_data.iloc[-1]['收盘']
            return float(latest_price)
        
        try:
            # 获取实时数据
            df = ak.stock_zh_a_spot()
            if df is None or df.empty:
                return None
            
            # 查找指定股票
            code_cols = [c for c in df.columns if ("代码" in c) or ("code" in c.lower())]
            price_cols = [c for c in df.columns if ("最新价" in c) or ("最新" in c) or ("price" in c.lower())]
            
            if not code_cols or not price_cols:
                return None
            
            ccol = code_cols[0]
            pcol = price_cols[0]
            
            row = df[df[ccol].astype(str) == str(symbol)]
            if row.empty:
                return None
            
            price = float(row.iloc[0][pcol])
            
            # 缓存实时数据（缓存30秒）
            await self._set_cache(cache_key, pd.DataFrame({'收盘': [price]}), ttl=30)
            
            return price
            
        except Exception as e:
            logger.error(f"Error getting spot price for {symbol}: {e}")
            return None
    
    async def get_batch_prices(self, symbols: List[str]) -> Dict[str, Optional[float]]:
        """批量获取价格"""
        tasks = [self.get_spot_price(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        prices = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.error(f"Error getting price for {symbol}: {result}")
                prices[symbol] = None
            else:
                prices[symbol] = result
        
        return prices
    
    async def cleanup_cache(self):
        """清理过期缓存"""
        async with self._cache_lock:
            expired_keys = [
                key for key, stock_data in self._cache.items() 
                if stock_data.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
        if hasattr(self, '_bulk_timer') and self._bulk_timer and not self._bulk_timer.done():
            self._bulk_timer.cancel()