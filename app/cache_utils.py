import hashlib
import time
import logging
from collections import OrderedDict
from functools import wraps
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger(__name__)

class TTLCache:
    """基于时间的缓存实现，支持LRU和TTL"""
    
    def __init__(self, ttl: int = 300, max_entries: int = 128, name: str = ""):
        """max_entries 默认 128，瘦身减少内存囤积；需要更多时可传入 256 等"""
        self.ttl = ttl
        self.max_entries = int(max_entries) if max_entries else 0
        self.name = name or "unnamed"
        self.cache: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self.hits = 0
        self.misses = 0
        logger.debug(f"缓存 '{self.name}' 已初始化 (TTL={ttl}s, MaxSize={max_entries})")

    def _is_expired(self, ts: float) -> bool:
        """检查缓存项是否过期"""
        return (time.time() - ts) >= self.ttl

    def prune(self):
        """清理过期项和超大小项"""
        if not self.cache:
            return
        
        # 清理过期项
        keys_to_delete = []
        for k, entry in self.cache.items():
            ts = float(entry.get("timestamp") or 0.0)
            if self._is_expired(ts):
                keys_to_delete.append(k)
        
        for k in keys_to_delete:
            try:
                del self.cache[k]
            except KeyError:
                pass
        
        if keys_to_delete:
            logger.debug(f"缓存 '{self.name}' 清理了 {len(keys_to_delete)} 个过期项")
        
        # 超出大小限制时，删除最旧的项
        if self.max_entries and len(self.cache) > self.max_entries:
            excess = len(self.cache) - self.max_entries
            for _ in range(excess):
                try:
                    self.cache.popitem(last=False)
                except Exception:
                    break
            logger.debug(f"缓存 '{self.name}' 删除了 {excess} 个最旧的项")

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self.cache:
            entry = self.cache[key]
            ts = float(entry.get("timestamp") or 0.0)
            
            # 检查是否过期
            if not self._is_expired(ts):
                self.hits += 1
                try:
                    # 将访问的项移到末尾（LRU）
                    self.cache.move_to_end(key)
                except Exception:
                    pass
                return entry.get("value")
            
            # 清理过期项
            try:
                del self.cache[key]
            except KeyError:
                pass
        
        self.misses += 1
        return None

    def set(self, key: str, value: Any):
        """设置缓存值"""
        self.cache[key] = {
            "value": value,
            "timestamp": time.time(),
        }
        try:
            # 将新项移到末尾
            self.cache.move_to_end(key)
        except Exception:
            pass
        
        # 执行清理
        self.prune()

    def delete(self, key: str) -> bool:
        """删除缓存项"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self):
        """清空所有缓存"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info(f"缓存 '{self.name}' 已清空")

    def info(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "name": self.name,
            "ttl": self.ttl,
            "max_entries": self.max_entries,
            "current_size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.2f}%"
        }


_CACHE_REGISTRY: List[TTLCache] = []

def create_cache(name: str, ttl: int = 300, max_entries: int = 128) -> TTLCache:
    """工厂函数：创建并注册缓存"""
    cache = TTLCache(ttl=ttl, max_entries=max_entries, name=name)
    _CACHE_REGISTRY.append(cache)
    logger.info(f"创建缓存: {name}")
    return cache

def cache_decorator(cache: TTLCache):
    """装饰器：为函数结果缓存"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 生成缓存键
            key = hashlib.md5(f"{func.__name__}_{args}_{kwargs}".encode()).hexdigest()
            
            # 尝试从缓存获取
            cached_value = cache.get(key)
            if cached_value is not None:
                logger.debug(f"缓存命中: {func.__name__}")
                return cached_value
            
            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            cache.set(key, result)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 生成缓存键
            key = hashlib.md5(f"{func.__name__}_{args}_{kwargs}".encode()).hexdigest()
            
            # 尝试从缓存获取
            cached_value = cache.get(key)
            if cached_value is not None:
                logger.debug(f"缓存命中: {func.__name__}")
                return cached_value
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        
        # 返回合适的包装器
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def get_cache_stats() -> Dict[str, Dict[str, Any]]:
    """获取所有缓存的统计信息"""
    return {cache.name: cache.info() for cache in _CACHE_REGISTRY}

def clear_all_caches():
    """清空所有缓存"""
    for cache in _CACHE_REGISTRY:
        cache.clear()
    logger.info(f"已清空 {len(_CACHE_REGISTRY)} 个缓存")

def get_cache_infos() -> List[Dict[str, Any]]:
    for c in list(_CACHE_REGISTRY):
        try:
            c.prune()
        except Exception:
            pass
    out = []
    for c in list(_CACHE_REGISTRY):
        try:
            out.append(c.info())
        except Exception:
            pass
    out.sort(key=lambda x: (str(x.get("name") or ""), int(x.get("size") or 0)), reverse=True)
    return out

def ttl_cache(ttl: int = 300, max_entries: int = 128, name: str = ""):
    cache = TTLCache(ttl=ttl, max_entries=max_entries, name=name)
    _CACHE_REGISTRY.append(cache)
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            raw = f"{func.__module__}.{func.__qualname__}:{args!r}:{kwargs!r}"
            digest = hashlib.blake2b(raw.encode("utf-8", "ignore"), digest_size=16).hexdigest()
            key = f"{func.__name__}:{digest}"
            result = cache.get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        return wrapper
    return decorator

# 异步版本的缓存装饰器
def async_ttl_cache(ttl: int = 300, max_entries: int = 128, name: str = ""):
    cache = TTLCache(ttl=ttl, max_entries=max_entries, name=name)
    _CACHE_REGISTRY.append(cache)
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            raw = f"{func.__module__}.{func.__qualname__}:{args!r}:{kwargs!r}"
            digest = hashlib.blake2b(raw.encode("utf-8", "ignore"), digest_size=16).hexdigest()
            key = f"{func.__name__}:{digest}"
            result = cache.get(key)
            if result is not None:
                return result
            result = await func(*args, **kwargs)
            cache.set(key, result)
            return result
        return wrapper
    return decorator
