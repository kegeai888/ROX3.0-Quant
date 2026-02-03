"""
内存优化的DataFrame处理工具
提供高效的DataFrame操作，减少内存占用
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Union
import gc
import logging
from datetime import datetime
import psutil
import os

logger = logging.getLogger(__name__)

class MemoryOptimizedDataFrame:
    """内存优化的DataFrame包装器"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = self._optimize_memory_usage(df)
        self.original_shape = df.shape
        self.optimized_shape = self.df.shape
        self.memory_saved = self._calculate_memory_saved(df, self.df)
        
        logger.info(f"DataFrame optimized: {self.original_shape} -> {self.optimized_shape}, "
                   f"Memory saved: {self.memory_saved:.2f} MB")
    
    def _optimize_memory_usage(self, df: pd.DataFrame) -> pd.DataFrame:
        """优化DataFrame内存使用"""
        df_optimized = df.copy()
        
        # 优化数值列
        for col in df_optimized.select_dtypes(include=['int64', 'float64']).columns:
            col_type = df_optimized[col].dtype
            
            if col_type == 'int64':
                # 尝试转换为更小的整数类型
                c_min = df_optimized[col].min()
                c_max = df_optimized[col].max()
                
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df_optimized[col] = df_optimized[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df_optimized[col] = df_optimized[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df_optimized[col] = df_optimized[col].astype(np.int32)
            
            elif col_type == 'float64':
                # 尝试转换为float32
                df_optimized[col] = df_optimized[col].astype(np.float32)
        
        # 优化对象类型列
        for col in df_optimized.select_dtypes(include=['object']).columns:
            num_unique_values = len(df_optimized[col].unique())
            num_total_values = len(df_optimized[col])
            
            # 如果唯一值比例小于50%，考虑转换为类别类型
            if num_unique_values / num_total_values < 0.5:
                df_optimized[col] = df_optimized[col].astype('category')
        
        # 优化日期时间列
        for col in df_optimized.select_dtypes(include=['datetime64[ns]']).columns:
            # 如果不需要纳秒精度，转换为日期类型
            df_optimized[col] = df_optimized[col].dt.date
        
        return df_optimized
    
    def _calculate_memory_saved(self, original_df: pd.DataFrame, optimized_df: pd.DataFrame) -> float:
        """计算节省的内存"""
        original_memory = original_df.memory_usage(deep=True).sum()
        optimized_memory = optimized_df.memory_usage(deep=True).sum()
        saved_bytes = original_memory - optimized_memory
        return saved_bytes / (1024 * 1024)  # 转换为MB
    
    def get_optimized_df(self) -> pd.DataFrame:
        """获取优化后的DataFrame"""
        return self.df.copy() if not self.df.empty else pd.DataFrame()
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取内存使用统计"""
        current_memory = self.df.memory_usage(deep=True).sum() / (1024 * 1024)
        return {
            'original_shape': self.original_shape,
            'optimized_shape': self.optimized_shape,
            'current_memory_mb': current_memory,
            'memory_saved_mb': self.memory_saved,
            'memory_reduction_pct': (self.memory_saved / (current_memory + self.memory_saved)) * 100
        }

class DataFrameChunkProcessor:
    """分块处理大型DataFrame"""
    
    def __init__(self, chunk_size: int = 10000):
        self.chunk_size = chunk_size
        logger.info(f"DataFrameChunkProcessor initialized with chunk_size={chunk_size}")
    
    def process_large_dataframe(self, df: pd.DataFrame, processing_func, *args, **kwargs) -> pd.DataFrame:
        """分块处理大型DataFrame"""
        if len(df) <= self.chunk_size:
            return processing_func(df, *args, **kwargs)
        
        logger.info(f"Processing large DataFrame in chunks: {len(df)} rows, chunk_size={self.chunk_size}")
        
        results = []
        total_chunks = (len(df) - 1) // self.chunk_size + 1
        
        for i in range(0, len(df), self.chunk_size):
            chunk = df.iloc[i:i + self.chunk_size].copy()
            chunk_num = i // self.chunk_size + 1
            
            logger.debug(f"Processing chunk {chunk_num}/{total_chunks}")
            
            try:
                processed_chunk = processing_func(chunk, *args, **kwargs)
                results.append(processed_chunk)
                
                # 强制垃圾回收
                del chunk
                gc.collect()
                
            except Exception as e:
                logger.error(f"Error processing chunk {chunk_num}: {e}")
                raise
        
        # 合并结果
        final_result = pd.concat(results, ignore_index=True)
        
        # 清理内存
        del results
        gc.collect()
        
        logger.info(f"Large DataFrame processing completed: {len(final_result)} rows")
        return final_result
    
    def apply_memory_efficient_operation(self, df: pd.DataFrame, operation: str, **kwargs) -> pd.DataFrame:
        """应用内存高效的操作"""
        logger.info(f"Applying memory efficient operation: {operation}")
        
        if operation == "rolling_mean":
            return self._rolling_mean_chunked(df, **kwargs)
        elif operation == "rolling_std":
            return self._rolling_std_chunked(df, **kwargs)
        elif operation == "pct_change":
            return self._pct_change_chunked(df, **kwargs)
        else:
            raise ValueError(f"Unsupported operation: {operation}")
    
    def _rolling_mean_chunked(self, df: pd.DataFrame, window: int = 20, column: str = 'close') -> pd.DataFrame:
        """分块计算滚动均值"""
        result_df = df.copy()
        
        if column not in df.columns:
            logger.warning(f"Column {column} not found in DataFrame")
            return result_df
        
        # 使用更内存高效的实现
        result_df[f'{column}_ma_{window}'] = result_df[column].rolling(window=window, min_periods=1).mean()
        
        return result_df
    
    def _rolling_std_chunked(self, df: pd.DataFrame, window: int = 20, column: str = 'close') -> pd.DataFrame:
        """分块计算滚动标准差"""
        result_df = df.copy()
        
        if column not in df.columns:
            logger.warning(f"Column {column} not found in DataFrame")
            return result_df
        
        result_df[f'{column}_std_{window}'] = result_df[column].rolling(window=window, min_periods=1).std()
        
        return result_df
    
    def _pct_change_chunked(self, df: pd.DataFrame, column: str = 'close') -> pd.DataFrame:
        """分块计算百分比变化"""
        result_df = df.copy()
        
        if column not in df.columns:
            logger.warning(f"Column {column} not found in DataFrame")
            return result_df
        
        result_df[f'{column}_pct_change'] = result_df[column].pct_change()
        
        return result_df

class MemoryMonitor:
    """内存监控器"""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.initial_memory = self.get_current_memory()
        logger.info(f"MemoryMonitor initialized, initial memory: {self.initial_memory:.2f} MB")
    
    def get_current_memory(self) -> float:
        """获取当前内存使用（MB）"""
        return self.process.memory_info().rss / (1024 * 1024)
    
    def get_memory_stats(self) -> Dict[str, float]:
        """获取内存统计"""
        current_memory = self.get_current_memory()
        memory_increase = current_memory - self.initial_memory
        
        return {
            'initial_memory_mb': self.initial_memory,
            'current_memory_mb': current_memory,
            'memory_increase_mb': memory_increase,
            'memory_increase_pct': (memory_increase / self.initial_memory) * 100 if self.initial_memory > 0 else 0
        }
    
    def log_memory_usage(self, context: str = ""):
        """记录内存使用情况"""
        stats = self.get_memory_stats()
        logger.info(f"Memory usage {context}: {stats['current_memory_mb']:.2f} MB "
                   f"(increase: {stats['memory_increase_mb']:.2f} MB, "
                   f"{stats['memory_increase_pct']:.1f}%)")
    
    def force_garbage_collection(self):
        """强制垃圾回收"""
        before_gc = self.get_current_memory()
        gc.collect()
        after_gc = self.get_current_memory()
        
        freed_memory = before_gc - after_gc
        logger.info(f"Garbage collection freed {freed_memory:.2f} MB")

class OptimizedDataProcessor:
    """优化的数据处理器"""
    
    def __init__(self, chunk_size: int = 10000):
        self.chunk_processor = DataFrameChunkProcessor(chunk_size)
        self.memory_monitor = MemoryMonitor()
    
    def process_stock_data(self, df: pd.DataFrame, 
                          calculate_indicators: bool = True,
                          optimize_memory: bool = True) -> pd.DataFrame:
        """处理股票数据"""
        logger.info(f"Processing stock data: {len(df)} rows, {len(df.columns)} columns")
        self.memory_monitor.log_memory_usage("before processing")
        
        # 内存优化
        if optimize_memory:
            optimizer = MemoryOptimizedDataFrame(df)
            df = optimizer.get_optimized_df()
            logger.info(f"Memory optimization saved {optimizer.memory_saved:.2f} MB")
        
        # 计算技术指标
        if calculate_indicators:
            df = self._calculate_technical_indicators(df)
        
        self.memory_monitor.log_memory_usage("after processing")
        
        return df
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        logger.info("Calculating technical indicators")
        
        if 'close' not in df.columns:
            logger.warning("No 'close' column found, skipping indicators")
            return df
        
        # 使用分块处理计算指标
        df = self.chunk_processor.apply_memory_efficient_operation(df, "rolling_mean", window=5, column='close')
        df = self.chunk_processor.apply_memory_efficient_operation(df, "rolling_mean", window=20, column='close')
        df = self.chunk_processor.apply_memory_efficient_operation(df, "rolling_std", window=20, column='close')
        df = self.chunk_processor.apply_memory_efficient_operation(df, "pct_change", column='close')
        
        return df
    
    def cleanup(self):
        """清理资源"""
        self.memory_monitor.force_garbage_collection()
        logger.info("OptimizedDataProcessor cleanup completed")

# 全局实例
global_processor = OptimizedDataProcessor()

def optimize_dataframe_memory(df: pd.DataFrame) -> pd.DataFrame:
    """优化DataFrame内存使用的快捷函数"""
    optimizer = MemoryOptimizedDataFrame(df)
    return optimizer.get_optimized_df()

def process_large_dataframe(df: pd.DataFrame, processing_func, *args, **kwargs) -> pd.DataFrame:
    """分块处理大型DataFrame的快捷函数"""
    return global_processor.chunk_processor.process_large_dataframe(df, processing_func, *args, **kwargs)

def get_memory_usage_stats() -> Dict[str, float]:
    """获取内存使用统计的快捷函数"""
    return global_processor.memory_monitor.get_memory_stats()

def log_memory_usage(context: str = ""):
    """记录内存使用情况的快捷函数"""
    global_processor.memory_monitor.log_memory_usage(context)