"""
并发优化工具 - 改进异步处理性能
"""

import asyncio
import concurrent.futures
from typing import List, Callable, Any, Optional, Dict, Union
import logging
import time
from functools import wraps
import threading
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp

logger = logging.getLogger(__name__)

@dataclass
class AsyncTaskResult:
    """异步任务结果"""
    task_id: str
    result: Any
    error: Optional[Exception] = None
    execution_time: float = 0.0
    retry_count: int = 0

class AsyncTaskManager:
    """异步任务管理器"""
    
    def __init__(self, 
                 max_workers: int = 8,
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 timeout: float = 30.0):
        
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        # 线程池执行器
        self.thread_executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 进程池执行器（用于CPU密集型任务）
        self.process_executor = ProcessPoolExecutor(max_workers=mp.cpu_count())
        
        # 任务跟踪
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.task_stats: Dict[str, Dict] = {}
        
        # 信号量控制并发
        self.semaphore = asyncio.Semaphore(max_workers)
        
        logger.info(f"AsyncTaskManager initialized with max_workers={max_workers}")
    
    async def execute_async(self, 
                           func: Callable, 
                           *args, 
                           task_id: Optional[str] = None,
                           use_process_pool: bool = False,
                           **kwargs) -> AsyncTaskResult:
        """执行异步任务"""
        
        task_id = task_id or f"task_{int(time.time() * 1000)}"
        start_time = time.time()
        
        async with self.semaphore:
            for attempt in range(self.max_retries + 1):
                try:
                    logger.debug(f"Executing task {task_id}, attempt {attempt + 1}")
                    
                    # 选择执行器
                    if use_process_pool:
                        loop = asyncio.get_event_loop()
                        result = await loop.run_in_executor(
                            self.process_executor, 
                            func, 
                            *args, 
                            **kwargs
                        )
                    else:
                        result = await asyncio.wait_for(
                            asyncio.to_thread(func, *args, **kwargs),
                            timeout=self.timeout
                        )
                    
                    execution_time = time.time() - start_time
                    
                    task_result = AsyncTaskResult(
                        task_id=task_id,
                        result=result,
                        execution_time=execution_time,
                        retry_count=attempt
                    )
                    
                    logger.debug(f"Task {task_id} completed in {execution_time:.2f}s")
                    return task_result
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Task {task_id} timeout on attempt {attempt + 1}")
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    else:
                        execution_time = time.time() - start_time
                        return AsyncTaskResult(
                            task_id=task_id,
                            error=asyncio.TimeoutError(f"Task timeout after {self.timeout}s"),
                            execution_time=execution_time,
                            retry_count=attempt
                        )
                        
                except Exception as e:
                    logger.error(f"Task {task_id} error on attempt {attempt + 1}: {e}")
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    else:
                        execution_time = time.time() - start_time
                        return AsyncTaskResult(
                            task_id=task_id,
                            error=e,
                            execution_time=execution_time,
                            retry_count=attempt
                        )
    
    async def execute_batch(self, 
                           tasks: List[Dict[str, Any]], 
                           max_concurrent: Optional[int] = None) -> List[AsyncTaskResult]:
        """批量执行异步任务"""
        
        if not tasks:
            return []
        
        max_concurrent = max_concurrent or self.max_workers
        logger.info(f"Executing batch of {len(tasks)} tasks with max_concurrent={max_concurrent}")
        
        # 限制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_semaphore(task_info: Dict[str, Any]) -> AsyncTaskResult:
            async with semaphore:
                func = task_info['func']
                args = task_info.get('args', ())
                kwargs = task_info.get('kwargs', {})
                task_id = task_info.get('task_id')
                use_process_pool = task_info.get('use_process_pool', False)
                
                return await self.execute_async(
                    func, *args, 
                    task_id=task_id,
                    use_process_pool=use_process_pool,
                    **kwargs
                )
        
        # 执行所有任务
        batch_start_time = time.time()
        results = await asyncio.gather(
            *[execute_with_semaphore(task) for task in tasks],
            return_exceptions=True
        )
        
        batch_execution_time = time.time() - batch_start_time
        logger.info(f"Batch execution completed in {batch_execution_time:.2f}s")
        
        return results
    
    async def execute_with_retry(self, 
                                func: Callable, 
                                *args, 
                                max_retries: Optional[int] = None,
                                retry_delay: Optional[float] = None,
                                **kwargs) -> Any:
        """带重试机制的任务执行"""
        
        max_retries = max_retries or self.max_retries
        retry_delay = retry_delay or self.retry_delay
        
        for attempt in range(max_retries + 1):
            try:
                return await asyncio.to_thread(func, *args, **kwargs)
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                else:
                    logger.error(f"All {max_retries} attempts failed")
                    raise
    
    def shutdown(self):
        """关闭执行器"""
        self.thread_executor.shutdown(wait=True)
        self.process_executor.shutdown(wait=True)
        logger.info("AsyncTaskManager shutdown completed")

class AsyncRateLimiter:
    """异步速率限制器"""
    
    def __init__(self, rate_limit: int = 10, time_window: float = 1.0):
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.requests = []
        self._lock = asyncio.Lock()
        
        logger.info(f"AsyncRateLimiter initialized: {rate_limit} requests per {time_window}s")
    
    async def acquire(self) -> None:
        """获取执行权限"""
        async with self._lock:
            now = time.time()
            
            # 移除过期的请求记录
            self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
            
            # 如果达到速率限制，等待
            if len(self.requests) >= self.rate_limit:
                sleep_time = self.requests[0] + self.time_window - now
                if sleep_time > 0:
                    logger.debug(f"Rate limit reached, waiting {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
                    return await self.acquire()
            
            # 记录当前请求
            self.requests.append(now)
    
    async def __aenter__(self):
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

def async_rate_limit(rate_limit: int = 10, time_window: float = 1.0):
    """异步速率限制装饰器"""
    rate_limiter = AsyncRateLimiter(rate_limit, time_window)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with rate_limiter:
                return await func(*args, **kwargs)
        return wrapper
    
    return decorator

def async_timeout(timeout_seconds: float = 30.0):
    """异步超时装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                logger.error(f"Function {func.__name__} timed out after {timeout_seconds}s")
                raise
        return wrapper
    
    return decorator

class AsyncBatchProcessor:
    """异步批处理器"""
    
    def __init__(self, batch_size: int = 100, max_workers: int = 4):
        self.batch_size = batch_size
        self.task_manager = AsyncTaskManager(max_workers=max_workers)
        logger.info(f"AsyncBatchProcessor initialized with batch_size={batch_size}")
    
    async def process_in_batches(self, 
                                items: List[Any], 
                                processing_func: Callable,
                                *args, **kwargs) -> List[Any]:
        """分批处理项目"""
        
        if not items:
            return []
        
        total_items = len(items)
        logger.info(f"Processing {total_items} items in batches of {self.batch_size}")
        
        results = []
        
        for i in range(0, total_items, self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (total_items - 1) // self.batch_size + 1
            
            logger.debug(f"Processing batch {batch_num}/{total_batches}: {len(batch)} items")
            
            # 创建批处理任务
            tasks = [
                {
                    'func': processing_func,
                    'args': (item,) + args,
                    'kwargs': kwargs,
                    'task_id': f"batch_{batch_num}_item_{idx}"
                }
                for idx, item in enumerate(batch)
            ]
            
            # 执行批处理
            batch_results = await self.task_manager.execute_batch(tasks)
            
            # 收集结果
            for result in batch_results:
                if isinstance(result, AsyncTaskResult) and result.error is None:
                    results.append(result.result)
                elif isinstance(result, Exception):
                    logger.error(f"Batch processing error: {result}")
                else:
                    results.append(result)
            
            logger.debug(f"Batch {batch_num}/{total_batches} completed")
        
        logger.info(f"Batch processing completed: {len(results)} results")
        return results
    
    def shutdown(self):
        """关闭处理器"""
        self.task_manager.shutdown()

# 全局实例
global_task_manager = AsyncTaskManager()
global_batch_processor = AsyncBatchProcessor()

# 快捷函数
async def run_async(func: Callable, *args, **kwargs) -> Any:
    """运行异步任务"""
    result = await global_task_manager.execute_async(func, *args, **kwargs)
    return result.result if result.error is None else result.error

async def run_batch(tasks: List[Dict[str, Any]], **kwargs) -> List[AsyncTaskResult]:
    """运行批处理任务"""
    return await global_task_manager.execute_batch(tasks, **kwargs)

async def process_batch(items: List[Any], processing_func: Callable, *args, **kwargs) -> List[Any]:
    """分批处理项目"""
    return await global_batch_processor.process_in_batches(items, processing_func, *args, **kwargs)

# 清理函数
def shutdown_async_optimizers():
    """关闭所有异步优化器"""
    global_task_manager.shutdown()
    global_batch_processor.shutdown()
    logger.info("All async optimizers shutdown")