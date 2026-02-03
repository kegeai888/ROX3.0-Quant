"""
数据库优化工具 - 查询优化和索引管理
"""

import sqlite3
import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
from contextlib import contextmanager
import time
from dataclasses import dataclass
from functools import wraps
import json
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class QueryStats:
    """查询统计信息"""
    query: str
    execution_time: float
    rows_affected: int
    query_plan: Optional[Dict[str, Any]] = None

class DatabaseOptimizer:
    """数据库优化器"""
    
    def __init__(self, db_path: str, enable_query_cache: bool = True):
        self.db_path = db_path
        self.enable_query_cache = enable_query_cache
        self.query_cache: Dict[str, Any] = {}
        self.query_stats: List[QueryStats] = []
        self.cache_ttl = 300  # 5分钟缓存
        
        logger.info(f"DatabaseOptimizer initialized for {db_path}")
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
            
            # 设置性能优化参数
            conn.execute("PRAGMA journal_mode=WAL")  # 写前日志模式
            conn.execute("PRAGMA synchronous=NORMAL")  # 同步模式
            conn.execute("PRAGMA cache_size=-20000")  # 20MB缓存
            conn.execute("PRAGMA temp_store=MEMORY")  # 临时表存储在内存
            
            yield conn
            
        finally:
            if conn:
                conn.close()
    
    def execute_optimized_query(self, query: str, params: tuple = None, 
                              use_cache: bool = True, cache_ttl: int = None) -> List[Dict[str, Any]]:
        """执行优化的查询"""
        
        start_time = time.time()
        cache_key = None
        
        # 检查查询缓存
        if self.enable_query_cache and use_cache:
            cache_key = hashlib.md5(f"{query}_{params}".encode()).hexdigest()
            if cache_key in self.query_cache:
                cached_result, cache_time = self.query_cache[cache_key]
                if time.time() - cache_time < (cache_ttl or self.cache_ttl):
                    logger.debug(f"Query cache hit for: {query[:50]}...")
                    return cached_result
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 执行查询
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                # 获取结果
                rows = cursor.fetchall()
                results = [dict(row) for row in rows]
                
                # 记录查询统计
                execution_time = time.time() - start_time
                query_stats = QueryStats(
                    query=query,
                    execution_time=execution_time,
                    rows_affected=len(results)
                )
                self.query_stats.append(query_stats)
                
                # 缓存结果
                if self.enable_query_cache and use_cache and cache_key:
                    self.query_cache[cache_key] = (results, time.time())
                
                logger.debug(f"Query executed in {execution_time:.3f}s, {len(results)} rows returned")
                return results
                
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def create_optimized_indexes(self, table_name: str, index_columns: List[str]) -> None:
        """创建优化的索引"""
        
        logger.info(f"Creating optimized indexes for table {table_name}")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取现有索引
            cursor.execute("PRAGMA index_list(?)", (table_name,))
            existing_indexes = {row[1] for row in cursor.fetchall()}
            
            # 为常用查询列创建索引
            for column in index_columns:
                index_name = f"idx_{table_name}_{column}"
                
                if index_name not in existing_indexes:
                    try:
                        create_index_sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({column})"
                        cursor.execute(create_index_sql)
                        logger.info(f"Created index {index_name}")
                    except Exception as e:
                        logger.warning(f"Failed to create index {index_name}: {e}")
            
            conn.commit()
    
    def analyze_query_performance(self, query: str, params: tuple = None) -> Dict[str, Any]:
        """分析查询性能"""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取查询计划
                explain_query = f"EXPLAIN QUERY PLAN {query}"
                if params:
                    cursor.execute(explain_query, params)
                else:
                    cursor.execute(explain_query)
                
                query_plan = [dict(row) for row in cursor.fetchall()]
                
                # 执行查询并测量时间
                start_time = time.time()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                execution_time = time.time() - start_time
                
                return {
                    'query': query,
                    'execution_time': execution_time,
                    'query_plan': query_plan,
                    'params': params
                }
                
        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            return {'error': str(e)}
    
    def vacuum_database(self) -> None:
        """清理和优化数据库"""
        
        logger.info("Vacuuming database...")
        
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
                logger.info("Database vacuum completed")
        except Exception as e:
            logger.error(f"Database vacuum failed: {e}")
    
    def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """获取表统计信息"""
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取行数
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                
                # 获取索引信息
                cursor.execute("PRAGMA index_list(?)", (table_name,))
                indexes = [dict(row) for row in cursor.fetchall()]
                
                # 获取表结构
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'table_name': table_name,
                    'row_count': row_count,
                    'indexes': indexes,
                    'columns': columns
                }
                
        except Exception as e:
            logger.error(f"Failed to get table stats for {table_name}: {e}")
            return {'error': str(e)}
    
    def cleanup_query_cache(self):
        """清理查询缓存"""
        
        current_time = time.time()
        expired_keys = [
            key for key, (result, cache_time) in self.query_cache.items()
            if current_time - cache_time > self.cache_ttl
        ]
        
        for key in expired_keys:
            del self.query_cache[key]
        
        logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        
        if not self.query_stats:
            return {'message': 'No query statistics available'}
        
        total_queries = len(self.query_stats)
        total_time = sum(stats.execution_time for stats in self.query_stats)
        avg_time = total_time / total_queries if total_queries > 0 else 0
        
        slow_queries = [stats for stats in self.query_stats if stats.execution_time > 1.0]
        
        return {
            'total_queries': total_queries,
            'total_execution_time': total_time,
            'average_execution_time': avg_time,
            'slow_queries_count': len(slow_queries),
            'slow_queries': [
                {
                    'query': stats.query[:100] + '...' if len(stats.query) > 100 else stats.query,
                    'execution_time': stats.execution_time,
                    'rows_affected': stats.rows_affected
                }
                for stats in slow_queries[:10]  # 只显示前10个慢查询
            ],
            'cache_size': len(self.query_cache)
        }

class AsyncDatabaseOptimizer:
    """异步数据库优化器"""
    
    def __init__(self, db_path: str, enable_query_cache: bool = True):
        self.sync_optimizer = DatabaseOptimizer(db_path, enable_query_cache)
        self._lock = asyncio.Lock()
    
    async def execute_optimized_query_async(self, query: str, params: tuple = None, 
                                          use_cache: bool = True, cache_ttl: int = None) -> List[Dict[str, Any]]:
        """异步执行优化的查询"""
        async with self._lock:
            return await asyncio.to_thread(
                self.sync_optimizer.execute_optimized_query,
                query, params, use_cache, cache_ttl
            )
    
    async def create_optimized_indexes_async(self, table_name: str, index_columns: List[str]) -> None:
        """异步创建优化的索引"""
        async with self._lock:
            await asyncio.to_thread(
                self.sync_optimizer.create_optimized_indexes,
                table_name, index_columns
            )
    
    async def analyze_query_performance_async(self, query: str, params: tuple = None) -> Dict[str, Any]:
        """异步分析查询性能"""
        return await asyncio.to_thread(
            self.sync_optimizer.analyze_query_performance,
            query, params
        )
    
    async def vacuum_database_async(self) -> None:
        """异步清理和优化数据库"""
        async with self._lock:
            await asyncio.to_thread(self.sync_optimizer.vacuum_database)
    
    async def get_table_stats_async(self, table_name: str) -> Dict[str, Any]:
        """异步获取表统计信息"""
        return await asyncio.to_thread(
            self.sync_optimizer.get_table_stats,
            table_name
        )
    
    async def cleanup_query_cache_async(self) -> None:
        """异步清理查询缓存"""
        async with self._lock:
            await asyncio.to_thread(self.sync_optimizer.cleanup_query_cache)
    
    async def get_performance_stats_async(self) -> Dict[str, Any]:
        """异步获取性能统计"""
        return await asyncio.to_thread(self.sync_optimizer.get_performance_stats)

def database_query_cache(ttl: int = 300):
    """数据库查询缓存装饰器"""
    def decorator(func: Callable) -> Callable:
        cache = {}
        cache_times = {}
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 创建缓存键
            cache_key = hashlib.md5(
                f"{func.__name__}_{str(args)}_{str(kwargs)}".encode()
            ).hexdigest()
            
            # 检查缓存
            current_time = time.time()
            if cache_key in cache:
                if current_time - cache_times[cache_key] < ttl:
                    return cache[cache_key]
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            cache[cache_key] = result
            cache_times[cache_key] = current_time
            
            return result
        
        return wrapper
    
    return decorator

# 全局实例
global_db_optimizer = None

def get_database_optimizer(db_path: str = None) -> AsyncDatabaseOptimizer:
    """获取全局数据库优化器实例"""
    global global_db_optimizer
    
    if global_db_optimizer is None and db_path:
        global_db_optimizer = AsyncDatabaseOptimizer(db_path)
    
    return global_db_optimizer

def optimize_database_connection(db_path: str) -> AsyncDatabaseOptimizer:
    """优化数据库连接"""
    optimizer = AsyncDatabaseOptimizer(db_path)
    logger.info(f"Database connection optimized for {db_path}")
    return optimizer