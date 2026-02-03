"""
Rox3.0 优化集成示例
展示如何将优化组件集成到现有代码中
"""

import asyncio
import pandas as pd
from typing import List, Dict, Any
import logging

# 导入优化组件
from app.utils.optimizer_integration import optimized_context, get_optimized_data_provider
from app.utils.optimized_cache import optimized_cache
from app.utils.optimized_dataframe import optimize_dataframe_memory, process_large_dataframe
from app.utils.optimized_async import run_batch, process_batch, async_rate_limit
from app.utils.optimized_database import database_query_cache

logger = logging.getLogger(__name__)

# 示例1: 优化数据获取
async def optimized_stock_analysis(symbol: str, days: int = 120):
    """优化的股票分析函数"""
    
    async with optimized_context("data/docs.db") as optimizer:
        # 使用优化的数据提供器
        data_provider = optimizer.data_provider
        
        # 获取股票数据（自动缓存）
        price_data = await data_provider.get_history(symbol, days)
        
        # 获取实时价格（自动缓存30秒）
        spot_price = await data_provider.get_spot_price(symbol)
        
        # 批量获取多个股票数据
        symbols = ["000001", "000002", "000003"]
        batch_prices = await data_provider.get_batch_prices(symbols)
        
        return {
            "symbol": symbol,
            "price_data": price_data,
            "spot_price": spot_price,
            "batch_prices": batch_prices
        }

# 示例2: 优化缓存使用
@optimized_cache(ttl=3600, max_size=1000, key_prefix="stock_analysis")
async def cached_stock_analysis(symbol: str, analysis_type: str = "technical"):
    """带缓存的股票分析"""
    
    # 这个函数的结果会被缓存1小时
    # 相同参数的请求会直接返回缓存结果
    
    logger.info(f"Performing {analysis_type} analysis for {symbol}")
    
    # 模拟复杂的分析过程
    await asyncio.sleep(0.1)  # 模拟耗时操作
    
    return {
        "symbol": symbol,
        "analysis_type": analysis_type,
        "result": f"Analysis completed for {symbol}",
        "timestamp": pd.Timestamp.now()
    }

# 示例3: 优化DataFrame处理
def optimized_dataframe_processing(df: pd.DataFrame):
    """优化的DataFrame处理"""
    
    # 内存优化
    optimized_df = optimize_dataframe_memory(df)
    
    # 分块处理大型DataFrame
    def process_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
        # 处理数据块
        chunk['returns'] = chunk['close'].pct_change()
        chunk['ma_20'] = chunk['close'].rolling(window=20).mean()
        return chunk
    
    # 分块处理
    if len(df) > 10000:
        result_df = process_large_dataframe(optimized_df, process_chunk)
    else:
        result_df = process_chunk(optimized_df)
    
    return result_df

# 示例4: 优化异步批量处理
async def optimized_batch_processing(symbols: List[str]):
    """优化的批量处理"""
    
    # 创建批量任务
    tasks = [
        {
            'func': cached_stock_analysis,
            'args': (symbol, "technical"),
            'task_id': f"analysis_{symbol}"
        }
        for symbol in symbols
    ]
    
    # 批量执行
    results = await run_batch(tasks, max_concurrent=5)
    
    # 处理结果
    successful_results = []
    for result in results:
        if hasattr(result, 'error') and result.error is None:
            successful_results.append(result.result)
        elif not hasattr(result, 'error'):
            successful_results.append(result)
    
    return successful_results

# 示例5: 优化数据库查询
@database_query_cache(ttl=300)
async def optimized_db_query(query: str, params: tuple = None):
    """优化的数据库查询"""
    
    from app.utils.optimized_database import get_database_optimizer
    
    db_optimizer = get_database_optimizer("data/docs.db")
    
    # 执行优化的查询
    results = await db_optimizer.execute_optimized_query_async(query, params)
    
    return results

# 示例6: 速率限制的API调用
@async_rate_limit(rate_limit=10, time_window=1.0)
async def rate_limited_api_call(symbol: str):
    """速率限制的API调用"""
    
    # 这个函数每秒最多调用10次
    # 超出限制时会自动等待
    
    logger.info(f"Making API call for {symbol}")
    
    # 模拟API调用
    await asyncio.sleep(0.01)
    
    return {"symbol": symbol, "data": "API response"}

# 示例7: 综合优化示例
async def comprehensive_optimization_example():
    """综合优化示例"""
    
    logger.info("Starting comprehensive optimization example...")
    
    async with optimized_context("data/docs.db") as optimizer:
        
        # 获取系统状态
        stats = await optimizer.get_system_stats()
        logger.info(f"System stats: {stats}")
        
        # 1. 优化的数据获取
        symbols = ["000001", "000002", "000003", "000004", "000005"]
        
        # 批量获取股票数据
        data_tasks = [
            (symbol, optimizer.data_provider.get_history(symbol, 60))
            for symbol in symbols
        ]
        
        # 并发执行
        stock_data = await asyncio.gather(
            *[task for _, task in data_tasks],
            return_exceptions=True
        )
        
        # 2. 优化的数据处理
        for symbol, data in zip(symbols, stock_data):
            if not isinstance(data, Exception) and data:
                logger.info(f"Processing data for {symbol}: {len(data)} records")
                
                # 转换为DataFrame进行处理
                df = pd.DataFrame([
                    {"date": p.date, "close": p.close, "volume": p.volume}
                    for p in data
                ])
                
                # 内存优化
                optimized_df = optimize_dataframe_memory(df)
                
                # 计算技术指标
                optimized_df['ma_10'] = optimized_df['close'].rolling(window=10).mean()
                optimized_df['returns'] = optimized_df['close'].pct_change()
                
                logger.info(f"Processed {symbol}: memory optimized, indicators calculated")
        
        # 3. 优化的缓存使用
        analysis_results = await optimized_batch_processing(symbols)
        
        logger.info(f"Analysis completed for {len(analysis_results)} symbols")
        
        # 4. 数据库查询优化
        recent_trades = await optimized_db_query(
            "SELECT * FROM trades WHERE entry_time > ? ORDER BY entry_time DESC",
            (pd.Timestamp.now() - pd.Timedelta(days=7),)
        )
        
        logger.info(f"Retrieved {len(recent_trades)} recent trades from database")
        
        # 5. 速率限制的API调用
        api_results = await asyncio.gather(
            *[rate_limited_api_call(symbol) for symbol in symbols[:3]],
            return_exceptions=True
        )
        
        successful_api_calls = [r for r in api_results if not isinstance(r, Exception)]
        logger.info(f"Completed {len(successful_api_calls)} API calls")
        
        # 获取最终系统状态
        final_stats = await optimizer.get_system_stats()
        logger.info(f"Final system stats: {final_stats}")
        
        return {
            "processed_symbols": len(symbols),
            "analysis_results": len(analysis_results),
            "recent_trades": len(recent_trades),
            "api_calls": len(successful_api_calls),
            "system_stats": final_stats
        }

# 主函数
async def main():
    """主函数"""
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting Rox3.0 optimization examples...")
    
    try:
        # 运行综合优化示例
        result = await comprehensive_optimization_example()
        
        logger.info(f"Optimization example completed successfully: {result}")
        
    except Exception as e:
        logger.error(f"Optimization example failed: {e}")
        raise
    
    finally:
        # 清理资源
        from app.utils.optimized_async import shutdown_async_optimizers
        shutdown_async_optimizers()
        
        logger.info("All optimization resources cleaned up")

if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())