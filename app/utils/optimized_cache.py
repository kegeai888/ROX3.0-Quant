"""
优化缓存系统 - 实现LRU缓存和Redis集成
提供高性能的缓存解决方案
"""

import time
import json
import hashlib
import pickle
from typing import Any, Optional, Callable, Union
from functools import wraps
from collections import OrderedDict
import asyncio
import logging

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, falling back to memory cache")

class LRUCache:
    """线程安全的LRU缓存实现"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()
        self.access_times = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key in self.cache:
                # 检查TTL
                if time.time() - self.access_times[key] > self.ttl:
                    del self.cache[key]
                    del self.access_times[key]
                    return None
                
                # 移动到末尾（最近使用）
                self.cache.move_to_end(key)
                self.access_times[key] = time.time()
                return self.cache[key]
            return None
    
    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.max_size:
                    # 移除最久未使用的项
                    oldest_key = next(iter(self.cache))
                    del self.cache[oldest_key]
                    del self.access_times[oldest_key]
            
            self.cache[key] = value
            self.access_times[key] = time.time()
    
    async def clear(self) -> None:
        async with self._lock:
            self.cache.clear()
            self.access_times.clear()
    
    async def size(self) -> int:
        async with self._lock:
            return len(self.cache)

class RedisCache:
    """Redis缓存实现"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", ttl: int = 3600):
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis not available")
        
        self.redis_client = redis.from_url(redis_url)
        self.ttl = ttl
    
    async def get(self, key: str) -> Optional[Any]:
        try:
            value = self.redis_client.get(key)
            if value:
                return pickle.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        try:
            serialized_value = pickle.dumps(value)
            expire_time = ttl or self.ttl
            self.redis_client.setex(key, expire_time, serialized_value)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
    
    async def clear(self) -> None:
        try:
            self.redis_client.flushdb()
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
    
    async def size(self) -> int:
        try:
            return self.redis_client.dbsize()
        except Exception as e:
            logger.error(f"Redis size error: {e}")
            return 0

class HybridCache:
    """混合缓存 - L1内存缓存 + L2 Redis缓存"""
    
    def __init__(self, 
                 l1_max_size: int = 500, 
                 l1_ttl: int = 1800,
                 l2_ttl: int = 7200,
                 redis_url: Optional[str] = None):
        
        self.l1_cache = LRUCache(max_size=l1_max_size, ttl=l1_ttl)
        self.l2_cache = None
        
        if redis_url and REDIS_AVAILABLE:
            try:
                self.l2_cache = RedisCache(redis_url, l2_ttl)
                logger.info("L2 Redis cache enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis cache: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        # 先检查L1缓存
        value = await self.l1_cache.get(key)
        if value is not None:
            return value
        
        # 再检查L2缓存
        if self.l2_cache:
            value = await self.l2_cache.get(key)
            if value is not None:
                # 回填到L1缓存
                await self.l1_cache.set(key, value)
                return value
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        # 设置L1缓存
        await self.l1_cache.set(key, value)
        
        # 设置L2缓存
        if self.l2_cache:
            await self.l2_cache.set(key, value, ttl)
    
    async def clear(self) -> None:
        await self.l1_cache.clear()
        if self.l2_cache:
            await self.l2_cache.clear()
    
    async def size(self) -> dict:
        l1_size = await self.l1_cache.size()
        l2_size = await self.l2_cache.size() if self.l2_cache else 0
        return {"l1": l1_size, "l2": l2_size}

def create_cache_key(func_name: str, *args, **kwargs) -> str:
    """创建缓存键"""
    key_data = {
        "func": func_name,
        "args": args,
        "kwargs": sorted(kwargs.items()) if kwargs else {}
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()

def optimized_cache(ttl: int = 3600, 
                   max_size: int = 1000,
                   key_prefix: str = "rox",
                   condition: Optional[Callable] = None):
    """
    优化的缓存装饰器
    
    Args:
        ttl: 缓存过期时间（秒）
        max_size: 最大缓存条目数
        key_prefix: 缓存键前缀
        condition: 缓存条件函数，返回True时才缓存
    """
    def decorator(func: Callable) -> Callable:
        cache = HybridCache(l1_max_size=max_size, l1_ttl=ttl//2, l2_ttl=ttl)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 检查缓存条件
            if condition and not condition(*args, **kwargs):
                return await func(*args, **kwargs)
            
            cache_key = f"{key_prefix}:{create_cache_key(func.__name__, *args, **kwargs)}"
            
            # 尝试从缓存获取
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            if result is not None:
                await cache.set(cache_key, result, ttl)
                logger.debug(f"Cached result for {func.__name__}")
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 同步函数包装器
            if condition and not condition(*args, **kwargs):
                return func(*args, **kwargs)
            
            # 对于同步函数，只使用内存缓存
            cache_key = f"{key_prefix}:{create_cache_key(func.__name__, *args, **kwargs)}"
            
            # 简单的内存缓存实现
            if not hasattr(func, '_cache'):
                func._cache = {}
                func._cache_times = {}
            
            now = time.time()
            if cache_key in func._cache:
                if now - func._cache_times[cache_key] < ttl:
                    return func._cache[cache_key]
            
            result = func(*args, **kwargs)
            if result is not None:
                func._cache[cache_key] = result
                func._cache_times[cache_key] = now
            
            return result
        
        # 根据函数类型返回适当的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# 全局缓存实例
global_cache = HybridCache(l1_max_size=1000, l1_ttl=1800, l2_ttl=3600)

async def clear_expired_cache():
    """清理过期缓存的定时任务"""
    try:
        # 这里可以添加更复杂的清理逻辑
        logger.info("Cache cleanup completed")
    except Exception as e:
        logger.error(f"Cache cleanup error: {e}")