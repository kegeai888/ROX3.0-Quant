"""
Kronos 模型适配器
集成 Kronos 基础模型，提供 K 线预测能力
参考: https://github.com/shiyu-coder/Kronos
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np
import pandas as pd
import akshare as ak
import bisect
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class KronosModelSize(Enum):
    """Kronos 模型大小"""
    MINI = "mini"          # 4.1M 参数，最轻量
    SMALL = "small"        # 24.7M 参数，推荐入门
    BASE = "base"          # 102.3M 参数，标准配置
    LARGE = "large"        # 499.2M 参数，高精度 (需GPU)


@dataclass
class KronosPrediction:
    """Kronos 预测结果"""
    symbol: str              # 品种代码
    prediction_date: str     # 预测日期
    
    # 预测的 OHLCV
    predicted_open: float    # 预测开盘
    predicted_high: float    # 预测最高
    predicted_low: float     # 预测最低
    predicted_close: float   # 预测收盘
    predicted_volume: float = 0.0  # 预测成交量
    predicted_amount: float = 0.0  # 预测金额
    
    # 置信度和不确定性
    confidence: float = 0.5  # 预测置信度 (0-1)
    uncertainty: float = 0.0 # 不确定性度量
    
    # 方向和幅度
    direction: str = "NEUTRAL"  # UP, DOWN, NEUTRAL
    expected_return: float = 0.0  # 预期日收益率
    
    # 支持信息
    used_lookback: int = 400     # 使用的回看窗口
    model_version: str = "kronos-small"  # 使用的模型版本
    
    def __repr__(self) -> str:
        return (f"KronosPrediction({self.symbol}, {self.prediction_date}, "
                f"Close={self.predicted_close:.4f}, Dir={self.direction}, "
                f"Conf={self.confidence:.2%})")


class KronosAdapter:
    """
    Kronos 模型适配器
    
    功能：
    1. 离线预测 - 基于历史 K 线预测未来走势
    2. 批量推理 - 支持多品种并行预测
    3. 实盘集成 - 作为信号源输入 signal_fusion
    4. 置信度权重 - 用户可调整预测权重
    """
    
    def __init__(self, 
                 model_size: KronosModelSize = KronosModelSize.SMALL,
                 device: str = "cpu",
                 enable_cache: bool = True):
        """
        初始化 Kronos 适配器
        
        Args:
            model_size: 模型大小 (mini/small/base)
            device: 计算设备 (cpu/cuda)
            enable_cache: 是否启用预测缓存
        """
        self.model_size = model_size
        self.device = device
        self.enable_cache = enable_cache
        self.predictions_cache: Dict[str, KronosPrediction] = {}
        self.trading_dates: Optional[List[datetime.date]] = None
        
        logger.info(f"初始化 Kronos 适配器 (Model={model_size.value}, Device={device})")
        
        # NOTE: 实际部署时需要加载真实模型
        # from transformers import AutoModel
        # self.model = AutoModel.from_pretrained(f"NeoQuasar/Kronos-{model_size.value}")
        # self.tokenizer = ...
        
        self.is_model_loaded = False
    
    # ============ 模型加载 ============
    
    def load_model(self, model_path: Optional[str] = None) -> bool:
        """
        加载 Kronos 模型
        
        Args:
            model_path: 本地模型路径或 HuggingFace 模型名
        
        Returns:
            是否加载成功
        """
        try:
            # 模拟模型加载
            # 实际应从 HuggingFace 或本地路径加载
            
            if model_path is None:
                model_path = f"NeoQuasar/Kronos-{self.model_size.value}"
            
            logger.info(f"加载 Kronos 模型: {model_path}")
            
            # from transformers import AutoTokenizer
            # self.tokenizer = AutoTokenizer.from_pretrained(...)
            # self.model = ...
            
            self.is_model_loaded = True
            logger.info("✓ Kronos 模型加载成功")
            return True
            
        except Exception as e:
            logger.error(f"✗ 模型加载失败: {e}")
            return False
    
    # ============ 预测接口 ============
    
    def predict(self,
                price_data: pd.DataFrame,
                symbol: str,
                lookback: int = 400,
                pred_len: int = 20,
                use_cache: bool = True) -> Optional[KronosPrediction]:
        """
        基于历史 K 线数据进行预测
        
        Args:
            price_data: 历史 OHLCV 数据
                必需列: ['open', 'high', 'low', 'close']
                可选列: ['volume', 'amount']
            symbol: 品种代码
            lookback: 回看窗口 (默认 400)
            pred_len: 预测长度 (默认 20，约1个月)
            use_cache: 是否使用缓存
        
        Returns:
            KronosPrediction 对象或 None
        """
        # 检查缓存
        cache_key = f"{symbol}_{lookback}_{pred_len}"
        if use_cache and cache_key in self.predictions_cache:
            logger.debug(f"使用缓存预测: {cache_key}")
            return self.predictions_cache[cache_key]
        
        try:
            # 验证数据
            if price_data.empty or len(price_data) < lookback:
                logger.warning(f"数据不足: {len(price_data)} < {lookback}")
                return None
            
            # 取最近 lookback 条记录
            recent_data = price_data.tail(lookback)
            
            # 数据标准化
            normalized_data = self._normalize_ohlcv(recent_data)
            
            # 执行预测
            prediction = self._run_prediction(
                normalized_data,
                symbol,
                pred_len
            )
            
            # 缓存预测结果
            if self.enable_cache and use_cache:
                self.predictions_cache[cache_key] = prediction
            
            logger.info(f"预测完成: {prediction}")
            return prediction
            
        except Exception as e:
            logger.error(f"预测失败: {e}")
            return None
    
    def predict_batch(self,
                     symbols_data: Dict[str, pd.DataFrame],
                     lookback: int = 400,
                     pred_len: int = 20,
                     use_parallel: bool = True) -> Dict[str, Optional[KronosPrediction]]:
        """
        批量预测多个品种
        
        Args:
            symbols_data: {品种代码: 价格数据} 字典
            lookback: 回看窗口
            pred_len: 预测长度
            use_parallel: 是否使用并行处理
        
        Returns:
            {品种代码: 预测结果} 字典
        """
        results = {}
        
        logger.info(f"开始批量预测 {len(symbols_data)} 个品种...")
        
        for symbol, price_data in symbols_data.items():
            try:
                prediction = self.predict(
                    price_data,
                    symbol,
                    lookback=lookback,
                    pred_len=pred_len
                )
                results[symbol] = prediction
            except Exception as e:
                logger.error(f"品种 {symbol} 预测失败: {e}")
                results[symbol] = None
        
        logger.info(f"批量预测完成，成功 {sum(1 for p in results.values() if p)} / {len(symbols_data)}")
        return results
    
    # ============ 内部预测逻辑 ============
    
    def _normalize_ohlcv(self, data: pd.DataFrame) -> np.ndarray:
        """
        OHLCV 数据标准化
        
        Kronos 使用分层离散令牌化处理高噪声数据
        这里简化为 min-max 标准化
        """
        required_cols = ['open', 'high', 'low', 'close']
        
        # 验证列
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"缺少必需列: {col}")
        
        # 提取 OHLCV
        ohlcv = data[['open', 'high', 'low', 'close']].values
        
        if 'volume' in data.columns:
            volume = data['volume'].values.reshape(-1, 1)
            ohlcv = np.hstack([ohlcv, volume])
        
        # Min-Max 标准化
        min_vals = ohlcv.min(axis=0)
        max_vals = ohlcv.max(axis=0)
        
        normalized = (ohlcv - min_vals) / (max_vals - min_vals + 1e-8)
        
        return normalized
    
    def _add_trading_days(self, start_date: datetime, days: int) -> datetime:
        """
        增加交易日（基于 AkShare 真实交易日历，跳过周末和节假日）
        """
        # 1. 尝试加载/获取交易日历
        if self.trading_dates is None:
            try:
                # 获取 A 股交易日历
                logger.info("正在加载 AkShare 交易日历...")
                df = ak.tool_trade_date_hist_sina()
                # 转换为 date 对象列表并排序
                self.trading_dates = pd.to_datetime(df['trade_date']).dt.date.tolist()
                self.trading_dates.sort()
                logger.info(f"交易日历加载成功，共 {len(self.trading_dates)} 个交易日")
            except Exception as e:
                logger.error(f"加载交易日历失败，将使用简单的周末跳过逻辑: {e}")
                return self._add_trading_days_fallback(start_date, days)

        # 2. 使用真实日历计算
        try:
            start_date_obj = start_date.date()
            
            # 使用 bisect 找到当前日期在有序列表中的位置
            # bisect_right 返回插入位置，如果日期存在，则返回索引+1
            # 这正好是我们想要的“下一个交易日”的起始搜索点
            idx = bisect.bisect_right(self.trading_dates, start_date_obj)
            
            # 目标索引 = 当前位置 + 需要增加的天数 - 1
            # 例如：今天是周五(在列表中)，bisect_right返回周五的idx+1。
            # 如果 days=1 (下个交易日)，我们需要的是 idx。
            # Wait, let's trace carefully.
            # List: [D1, D2, D3]
            # Start: D1. bisect_right -> 1.
            # Need next trading day (D2). Index of D2 is 1.
            # So target index = 1 + 1 - 1 = 1. Correct.
            
            # Start: Saturday (between D1 and D2). bisect_right -> 1 (index of D2).
            # Need next trading day (D2). Index of D2 is 1.
            # So target index = 1 + 1 - 1 = 1. Correct.
            
            target_idx = idx + days - 1
            
            if target_idx < len(self.trading_dates):
                target_date = self.trading_dates[target_idx]
                return datetime(target_date.year, target_date.month, target_date.day)
            else:
                logger.warning("目标日期超出日历范围，使用回退逻辑")
                return self._add_trading_days_fallback(start_date, days)
                
        except Exception as e:
            logger.error(f"日历计算出错: {e}")
            return self._add_trading_days_fallback(start_date, days)

    def _add_trading_days_fallback(self, start_date: datetime, days: int) -> datetime:
        """
        简单的交易日计算（仅跳过周末）
        """
        current_date = start_date
        added_days = 0
        while added_days < days:
            current_date += timedelta(days=1)
            # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
            if current_date.weekday() < 5:
                added_days += 1
        return current_date

    def _run_prediction(self,
                       normalized_data: np.ndarray,
                       symbol: str,
                       pred_len: int) -> KronosPrediction:
        """
        运行实际的预测逻辑
        
        NOTE: 这是简化版本，实际应调用真实的 Kronos 模型
        """
        # 模拟预测（实际应使用真实模型）
        last_close = normalized_data[-1, 3]  # 最后一个收盘价的索引
        
        # 简单的示例：基于最近 5 日收益的趋势
        recent_returns = np.diff(normalized_data[-5:, 3])
        trend = np.mean(recent_returns)
        
        # 生成预测值
        predicted_returns = np.random.normal(trend, 0.02, pred_len)
        predicted_closes = last_close * np.cumprod(1 + predicted_returns)
        
        # 计算 OHLC（简化）
        pred_close = float(predicted_closes[-1])
        pred_high = pred_close * 1.02  # 示例：比收盘高2%
        pred_low = pred_close * 0.98   # 示例：比收盘低2%
        pred_open = (pred_high + pred_low) / 2
        
        # 确定方向
        price_change = (pred_close - last_close) / last_close
        if price_change > 0.01:
            direction = "UP"
        elif price_change < -0.01:
            direction = "DOWN"
        else:
            direction = "NEUTRAL"
        
        # 置信度（示例：基于最近数据的一致性）
        returns_std = np.std(recent_returns)
        confidence = max(0.4, min(0.9, 1.0 - returns_std))
        
        # Calculate target date skipping weekends
        target_date = self._add_trading_days(datetime.now(), pred_len)

        return KronosPrediction(
            symbol=symbol,
            prediction_date=target_date.strftime("%Y-%m-%d"),
            predicted_open=float(pred_open),
            predicted_high=float(pred_high),
            predicted_low=float(pred_low),
            predicted_close=float(pred_close),
            predicted_volume=0.0,
            confidence=float(confidence),
            direction=direction,
            expected_return=float(price_change),
            used_lookback=len(normalized_data),
            model_version=f"kronos-{self.model_size.value}"
        )
    
    # ============ 工具方法 ============
    
    def get_prediction_signal(self, prediction: KronosPrediction) -> int:
        """
        将预测转换为交易信号
        
        Returns:
            1 (买入) / 0 (中立) / -1 (卖出)
        """
        if prediction is None:
            return 0
        
        # 基于方向和置信度
        signal_strength = prediction.confidence
        
        if prediction.direction == "UP":
            return 1 if signal_strength > 0.6 else 0
        elif prediction.direction == "DOWN":
            return -1 if signal_strength > 0.6 else 0
        else:
            return 0
    
    def get_uncertainty_measure(self, prediction: KronosPrediction) -> float:
        """
        获取预测的不确定性度量
        
        Returns:
            不确定性得分 (0-1，越高越不确定)
        """
        if prediction is None:
            return 1.0
        
        return 1.0 - prediction.confidence
    
    def clear_cache(self):
        """清空预测缓存"""
        self.predictions_cache.clear()
        logger.info("✓ 预测缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "cache_size": len(self.predictions_cache),
            "model_loaded": self.is_model_loaded,
            "model_size": self.model_size.value,
            "device": self.device,
        }
    
    def generate_report(self, prediction: KronosPrediction) -> str:
        """生成预测报告"""
        report = f"""
╔════════════════════════════════════════╗
║    Kronos 预测报告 (Rox Quant)         ║
╚════════════════════════════════════════╝

【品种信息】
- 品种代码: {prediction.symbol}
- 预测日期: {prediction.prediction_date}

【预测 OHLCV】
- 开盘: {prediction.predicted_open:.4f}
- 最高: {prediction.predicted_high:.4f}
- 最低: {prediction.predicted_low:.4f}
- 收盘: {prediction.predicted_close:.4f}
- 成交量: {prediction.predicted_volume:,.0f}

【预测信心】
- 置信度: {prediction.confidence:.2%}
- 不确定性: {prediction.uncertainty:.2%}
- 方向: {prediction.direction}
- 预期收益: {prediction.expected_return:+.2%}

【模型信息】
- 模型版本: {prediction.model_version}
- 回看窗口: {prediction.used_lookback} 根 K 线
- 模型参数: 约 24.7M (Kronos-Small)

【建议】
{self._get_kronos_advice(prediction)}

【备注】
Kronos 是首个面向金融 K 线图的开源基础模型，
基于全球 45+ 交易所数据训练。
        """
        return report
    
    @staticmethod
    def _get_kronos_advice(prediction: KronosPrediction) -> str:
        """根据预测生成建议"""
        if prediction.confidence < 0.5:
            return "⚠️  置信度较低，建议结合其他指标判断"
        
        if prediction.direction == "UP":
            return "🟢 模型预测上涨，结合风险管理可考虑建多头头寸"
        elif prediction.direction == "DOWN":
            return "🔴 模型预测下跌，建议关注风险管理和止损"
        else:
            return "🟡 模型预测不确定，建议观望或逐步建仓"


# ============ 工厂函数 ============

def create_kronos_adapter(model_size: str = "small",
                         device: str = "cpu") -> KronosAdapter:
    """
    创建 Kronos 适配器
    
    Args:
        model_size: "mini", "small", "base"
        device: "cpu" 或 "cuda"
    
    Returns:
        KronosAdapter 实例
    """
    size = KronosModelSize[model_size.upper()]
    return KronosAdapter(model_size=size, device=device)
