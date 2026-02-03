import time
from functools import wraps
import asyncio

def async_ttl_cache(ttl=360, max_entries=128, name="cache"):
    def decorator(func):
        cache = {}
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            now = time.time()
            if key in cache:
                val, timestamp = cache[key]
                if now - timestamp < ttl:
                    return val
            
            res = await func(*args, **kwargs)
            
            # Simple eviction
            if len(cache) > max_entries:
                cache.clear() # Primitive but works
                
            cache[key] = (res, now)
            return res
        return wrapper
    return decorator
