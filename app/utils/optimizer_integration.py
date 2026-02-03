"""
Rox3.0 优化集成模块
整合所有优化组件，提供统一的优化接口
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from app.utils.optimized_cache import global_cache, optimized_cache
from app.utils.optimized_dataframe import global_processor, optimize_dataframe_memory
from app.utils.optimized_async import global_task_manager, global_batch_processor, run_async
from app.utils.optimized_database import get_database_optimizer
from app.rox_quant.optimized_data_provider import OptimizedDataProvider

logger = logging.getLogger(__name__)

class RoxOptimizer:
    """Rox3.0 综合优化器"""
    
    def __init__(self, 
                 enable_cache: bool = True,
                 enable_memory_optimization: bool = True,
                 enable_async_optimization: bool = True,
                 enable_db_optimization: bool = True):
        
        self.enable_cache = enable_cache
        self.enable_memory_optimization = enable_memory_optimization
        self.enable_async_optimization = enable_async_optimization
        self.enable_db_optimization = enable_db_optimization
        
        self.data_provider = None
        self.db_optimizer = None
        
        logger.info("RoxOptimizer initialized")
    
    async def initialize(self, db_path: Optional[str] = None):
        """初始化优化器"""
        logger.info("Initializing RoxOptimizer components...")
        
        # 初始化数据提供器
        self.data_provider = OptimizedDataProvider(
            cache_ttl=300,
            max_workers=4,
            enable_bulk_fetch=True
        )
        
        # 初始化数据库优化器
        if self.enable_db_optimization and db_path:
            self.db_optimizer = get_database_optimizer(db_path)
            # 异步创建常用索引
            await self._create_default_indexes()
        
        logger.info("RoxOptimizer initialization completed")
    
    async def _create_default_indexes(self):
        """创建默认索引"""
        if not self.db_optimizer:
            return
            
        try:
            # 为文档表创建索引
            await self.db_optimizer.create_optimized_indexes_async(
                "documents", ["title", "created_at"]
            )
            # 为交易记录表创建索引（如果存在）
            await self.db_optimizer.create_optimized_indexes_async(
                "trades", ["symbol", "entry_time", "status"]
            )
        except Exception as e:
            logger.warning(f"Failed to create default indexes: {e}")
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """获取系统性能统计"""
        stats = {
            "cache": await global_cache.size(),
            "memory": global_processor.memory_monitor.get_memory_stats(),
            "async_tasks": len(global_task_manager.active_tasks),
        }
        
        if self.db_optimizer:
            stats["database"] = await self.db_optimizer.get_performance_stats_async()
        
        return stats
    
    async def cleanup(self):
        """清理所有资源"""
        logger.info("Cleaning up RoxOptimizer resources...")
        
        # 清理缓存
        await global_cache.clear()
        
        # 清理数据提供器
        if self.data_provider:
            await self.data_provider.cleanup_cache()
        
        # 清理内存监控
        global_processor.cleanup()
        
        # 关闭异步任务管理器
        global_task_manager.shutdown()
        global_batch_processor.shutdown()
        
        logger.info("RoxOptimizer cleanup completed")

# 全局优化器实例
global_optimizer = RoxOptimizer()

@asynccontextmanager
async def optimized_context(db_path: Optional[str] = None):
    """优化上下文管理器"""
    await global_optimizer.initialize(db_path)
    try:
        yield global_optimizer
    finally:
        await global_optimizer.cleanup()

def get_optimized_data_provider() -> OptimizedDataProvider:
    """获取优化的数据提供器"""
    if not global_optimizer.data_provider:
        global_optimizer.data_provider = OptimizedDataProvider()
    return global_optimizer.data_provider
