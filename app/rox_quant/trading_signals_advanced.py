"""
高级交易信号系统 - 基于《量化交易从入门到精通》
实现7个核心信号系统及其参数化
"""

import logging
from typing import Dict, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class AdvancedTradingSignals:
    """
    高级交易信号系统
    包含：趋势突破、MA系统、自适应均线、ATR通道、RSI成本线、MACD背离、ADX趋势识别
    """
    
    # ============ 信号1：趋势突破（海龟/唐奇安） ============
    
    @staticmethod
    def donchian_breakout(high: pd.Series, low: pd.Series, 
                         period: int = 20,
                         filter_ma: pd.Series = None) -> Dict[str, pd.Series]:
        """
        唐奇安通道突破信号
        
        Args:
            high: 最高价序列
            low: 最低价序列
            period: 周期（默认20，书中有20/55/88等选项）
            filter_ma: 均线过滤条件（可选）
        
        Returns:
            包含上轨、下轨、买入信号、卖出信号
        """
        # 计算N周期最高价和最低价
        upper = high.rolling(window=period).max()
        lower = low.rolling(window=period).min()
        middle = (upper + lower) / 2
        
        # 突破信号：收盘价突破上轨→买入，跌破下轨→卖出
        buy_signal = (high > upper.shift(1)).astype(int)
        sell_signal = (low < lower.shift(1)).astype(int)
        
        # 如果提供均线过滤，则只在价格在均线上方时才生成买入信号
        if filter_ma is not None:
            close = (high + low) / 2
            buy_signal = buy_signal & (close > filter_ma).astype(int)
        
        return {
            'upper': upper,
            'lower': lower,
            'middle': middle,
            'buy_signal': buy_signal,
            'sell_signal': sell_signal,
            'period': period
        }
    
    # ============ 信号2：MA系统 & 专业线系统 ============
    
    @staticmethod
    def professional_ma_system(close: pd.Series, 
                              short_periods: list = None,
                              medium_periods: list = None,
                              long_periods: list = None) -> Dict[str, pd.Series]:
        """
        专业均线系统
        
        书中参数示例：
        - 黄金日线：3,5,12,21,25,43,64,86,99,120,840,888
        - 短期：2-49，中期：50-99，长期：>=100
        
        Args:
            close: 收盘价序列
            short_periods: 短期均线周期 (默认: [2, 5, 10, 13])
            medium_periods: 中期均线周期 (默认: [50, 60, 70])
            long_periods: 长期均线周期 (默认: [120, 200, 250])
        
        Returns:
            各期间均线数据
        """
        if short_periods is None:
            short_periods = [2, 5, 10, 13]
        if medium_periods is None:
            medium_periods = [50, 60, 70]
        if long_periods is None:
            long_periods = [120, 200, 250]
        
        result = {}
        
        # 计算所有均线
        for period in short_periods:
            result[f'ma_{period}_short'] = close.rolling(window=period).mean()
        
        for period in medium_periods:
            result[f'ma_{period}_medium'] = close.rolling(window=period).mean()
        
        for period in long_periods:
            result[f'ma_{period}_long'] = close.rolling(window=period).mean()
        
        # 判断多头排列：短 > 中 > 长
        short_ma = close.rolling(window=short_periods[0]).mean()
        medium_ma = close.rolling(window=medium_periods[0]).mean()
        long_ma = close.rolling(window=long_periods[0]).mean()
        
        bullish_alignment = (short_ma > medium_ma) & (medium_ma > long_ma)
        bearish_alignment = (short_ma < medium_ma) & (medium_ma < long_ma)
        
        result['bullish_alignment'] = bullish_alignment
        result['bearish_alignment'] = bearish_alignment
        result['ma_short'] = short_ma
        result['ma_medium'] = medium_ma
        result['ma_long'] = long_ma
        
        return result
    
    @staticmethod
    def double_ma_system(close: pd.Series, 
                        fast_ma: int = 28,
                        slow_ma: int = 48) -> Dict[str, pd.Series]:
        """
        双子线战法：MA28 进场 + MA48 防守
        """
        ma_fast = close.rolling(window=fast_ma).mean()
        ma_slow = close.rolling(window=slow_ma).mean()
        
        # 金叉信号
        golden_cross = (ma_fast > ma_slow) & (ma_fast.shift(1) <= ma_slow.shift(1))
        # 死叉信号
        death_cross = (ma_fast < ma_slow) & (ma_fast.shift(1) >= ma_slow.shift(1))
        
        return {
            'ma_fast': ma_fast,
            'ma_slow': ma_slow,
            'golden_cross': golden_cross,
            'death_cross': death_cross
        }
    
    # ============ 信号3：自适应均线 AMA ============
    
    @staticmethod
    def kaufman_adaptive_ma(close: pd.Series,
                           efficiency_period: int = 10,
                           fast_sc: int = 2,
                           slow_sc: int = 30) -> Dict[str, pd.Series]:
        """
        Kaufman 自适应均线 (Adaptive Moving Average)
        
        思想：价格效率高（趋势明显）→ 短周期；效率低（震荡）→ 长周期
        
        Args:
            close: 收盘价
            efficiency_period: 计算效率比的周期
            fast_sc: 最快平滑常数对应周期
            slow_sc: 最慢平滑常数对应周期
        
        Returns:
            AMA及相关指标
        """
        # 计算方向性移动 (Directional Movement)
        change = close.diff().abs()
        direction = close.diff().abs()
        
        # 计算波动 (Volatility)
        volatility = direction.rolling(window=efficiency_period).sum()
        
        # 效率比 (Efficiency Ratio)
        er = np.where(
            volatility != 0,
            change.rolling(window=efficiency_period).sum() / volatility,
            0
        )
        er = pd.Series(er, index=close.index)
        
        # 平滑常数
        fastest = 2.0 / (fast_sc + 1)
        slowest = 2.0 / (slow_sc + 1)
        
        sc = (er * (fastest - slowest) + slowest) ** 2
        
        # 计算 AMA
        ama = pd.Series(index=close.index, dtype=float)
        ama.iloc[0] = close.iloc[0]
        
        for i in range(1, len(close)):
            ama.iloc[i] = ama.iloc[i-1] + sc.iloc[i] * (close.iloc[i] - ama.iloc[i-1])
        
        return {
            'ama': ama,
            'efficiency_ratio': er,
            'smoothing_constant': sc
        }
    
    # ============ 信号4：ATR通道 & 金肯特纳通道 ============
    
    @staticmethod
    def atr_keltner_channel(high: pd.Series, low: pd.Series, close: pd.Series,
                           ma_period: int = 56,
                           atr_period: int = 3,
                           atr_multiple: float = 1.0) -> Dict[str, pd.Series]:
        """
        金肯特纳通道：基于 ATR 的自适应通道
        
        Args:
            high, low, close: OHLC数据
            ma_period: 均线周期 (默认56)
            atr_period: ATR周期 (默认3)
            atr_multiple: ATR放大倍数 (默认1.0)
        
        Returns:
            中轨、上轨、下轨及突破信号
        """
        # 计算三价均线 (HL2/HL3)
        middle = ((high + low + close) / 3).rolling(window=ma_period).mean()
        
        # 计算 ATR
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=atr_period).mean()
        
        upper = middle + atr_multiple * atr
        lower = middle - atr_multiple * atr
        
        # 突破信号
        breakout_up = close > upper.shift(1)
        breakout_down = close < lower.shift(1)
        
        return {
            'middle': middle,
            'upper': upper,
            'lower': lower,
            'atr': atr,
            'breakout_up': breakout_up,
            'breakout_down': breakout_down
        }
    
    @staticmethod
    def bollinger_bands_advanced(close: pd.Series,
                                period: int = 48,
                                std_dev: float = 1.8,
                                use_width_filter: bool = True,
                                width_threshold: float = 1.01) -> Dict[str, pd.Series]:
        """
        强盗布林带：收窄后突破策略
        
        Args:
            close: 收盘价
            period: 周期 (默认48)
            std_dev: 标准差倍数 (默认1.8)
            use_width_filter: 是否使用宽度过滤
            width_threshold: 宽度阈值 (默认1.01，表示1%窄化)
        
        Returns:
            布林带及交易信号
        """
        ma = close.rolling(window=period).mean()
        std = close.rolling(window=std_dev).std()
        
        upper = ma + std_dev * std
        lower = ma - std_dev * std
        
        # 通道宽度
        width = (upper - lower) / ma
        
        # 超窄条件（预示大行情）
        is_narrow = width < width.rolling(window=period).mean() * width_threshold
        
        # 突破信号：仅在窄化后突破才有效
        breakout_up = close > upper.shift(1)
        breakout_down = close < lower.shift(1)
        
        valid_breakout_up = breakout_up & is_narrow.shift(1) if use_width_filter else breakout_up
        valid_breakout_down = breakout_down & is_narrow.shift(1) if use_width_filter else breakout_down
        
        return {
            'middle': ma,
            'upper': upper,
            'lower': lower,
            'width': width,
            'is_narrow': is_narrow,
            'breakout_up': valid_breakout_up,
            'breakout_down': valid_breakout_down
        }
    
    # ============ 信号5：RSI + 成本线 ============
    
    @staticmethod
    def rsi_cost_line(close: pd.Series,
                     rsi_period: int = 5,
                     cost_ma_period: int = 33,
                     cost_percentage: float = 0.019,  # 1.9% for A股日线
                     fat1: float = 0.009,  # 偏离阈值
                     fat2: float = 0.0024) -> Dict[str, pd.Series]:  # 动能减弱阈值
        """
        RSI + 成本线回归策略
        
        特点：重点在低位低速买入（高胜率低盈亏比模式）
        
        Args:
            close: 收盘价
            rsi_period: RSI周期
            cost_ma_period: 成本线均线周期
            cost_percentage: 成本线宽度百分比
            fat1: 偏离阈值（0.9%）
            fat2: 动能减弱阈值（0.24%）
        
        Returns:
            RSI、成本线、买卖信号
        """
        # 计算RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        # 成本线
        cost_ma = close.rolling(window=cost_ma_period).mean()
        cost_upper = cost_ma * (1 + cost_percentage)
        cost_lower = cost_ma * (1 - cost_percentage)
        
        # 买入条件：RSI<20 + 价格跌破下轨一定百分比 + 跌幅开始缩小
        price_below_lower = close < cost_lower * (1 - fat1)
        momentum_weakening = close.pct_change().abs() < close.pct_change().abs().shift(1) * (1 - fat2)
        
        buy_signal = (rsi < 20) & price_below_lower & momentum_weakening
        
        # 卖出条件：RSI>70
        sell_signal = rsi > 70
        
        return {
            'rsi': rsi,
            'cost_ma': cost_ma,
            'cost_upper': cost_upper,
            'cost_lower': cost_lower,
            'buy_signal': buy_signal,
            'sell_signal': sell_signal
        }
    
    # ============ 信号6：MACD背离 + 动态区间 ============
    
    @staticmethod
    def macd_divergence(close: pd.Series,
                       fast_period: int = 12,
                       slow_period: int = 26,
                       signal_period: int = 9,
                       lookback: int = 10) -> Dict[str, pd.Series]:
        """
        MACD 背离检测
        
        Args:
            close: 收盘价
            lookback: 向后查看的bar数（用于比较）
        
        Returns:
            MACD、背离信号等
        """
        # 计算MACD
        ema_fast = close.ewm(span=fast_period).mean()
        ema_slow = close.ewm(span=slow_period).mean()
        
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal_period).mean()
        histogram = macd - signal_line
        
        # 检测顶背离：价格新高，MACD不新高
        close_max_lookback = close.rolling(window=lookback).max()
        macd_max_lookback = macd.rolling(window=lookback).max()
        
        price_is_new_high = close == close_max_lookback
        macd_is_not_new_high = macd < macd_max_lookback.shift(1)
        top_divergence = price_is_new_high & macd_is_not_new_high
        
        # 检测底背离：价格新低，MACD不新低
        close_min_lookback = close.rolling(window=lookback).min()
        macd_min_lookback = macd.rolling(window=lookback).min()
        
        price_is_new_low = close == close_min_lookback
        macd_is_not_new_low = macd > macd_min_lookback.shift(1)
        bottom_divergence = price_is_new_low & macd_is_not_new_low
        
        return {
            'macd': macd,
            'signal': signal_line,
            'histogram': histogram,
            'top_divergence': top_divergence,
            'bottom_divergence': bottom_divergence
        }
    
    # ============ 信号7：ADX / Aroon 趋势识别 ============
    
    @staticmethod
    def adx_trend_identifier(high: pd.Series, low: pd.Series,
                            period: int = 14) -> Dict[str, pd.Series]:
        """
        ADX 趋势识别
        
        Returns:
            +DI, -DI, ADX 及趋势判断
        """
        # 计算方向性移动
        up_move = high.diff()
        down_move = -low.diff()
        
        # 初始化方向性移动（只取正值）
        plus_dm = pd.Series(0.0, index=high.index)
        minus_dm = pd.Series(0.0, index=high.index)
        
        for i in range(1, len(high)):
            if up_move.iloc[i] > down_move.iloc[i] and up_move.iloc[i] > 0:
                plus_dm.iloc[i] = up_move.iloc[i]
            if down_move.iloc[i] > up_move.iloc[i] and down_move.iloc[i] > 0:
                minus_dm.iloc[i] = down_move.iloc[i]
        
        # 计算真实波幅
        tr1 = high - low
        tr2 = abs(high - high.shift(1))
        tr3 = abs(low - low.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 平滑（14周期）
        plus_di = 100 * plus_dm.rolling(window=period).mean() / tr.rolling(window=period).mean()
        minus_di = 100 * minus_dm.rolling(window=period).mean() / tr.rolling(window=period).mean()
        
        # 计算ADX
        di_diff = abs(plus_di - minus_di)
        di_sum = plus_di + minus_di + 1e-10
        dx = 100 * di_diff / di_sum
        adx = dx.rolling(window=period).mean()
        
        # 趋势判断：ADX<20 且连续抬升 → 弱趋势向趋势过渡
        adx_rising = adx > adx.shift(1)
        weak_to_strong = (adx < 20) & adx_rising
        
        return {
            'plus_di': plus_di,
            'minus_di': minus_di,
            'adx': adx,
            'adx_rising': adx_rising,
            'weak_to_strong': weak_to_strong
        }
    
    @staticmethod
    def aroon_oscillator(high: pd.Series, low: pd.Series,
                        period: int = 25,
                        threshold: float = 45.0) -> Dict[str, pd.Series]:
        """
        Aroon 指标 - 距最近最高/最低价的相对位置
        
        Args:
            period: 回看周期（默认25）
            threshold: 判断阈值（默认45）
        
        Returns:
            Aroon Up, Aroon Down, 信号
        """
        # 计算距最近最高价的周期数
        highest_idx = high.rolling(window=period).apply(lambda x: np.argmax(x), raw=True)
        aroon_up = ((period - highest_idx) / period) * 100
        
        # 计算距最近最低价的周期数
        lowest_idx = low.rolling(window=period).apply(lambda x: np.argmin(x), raw=True)
        aroon_down = ((period - lowest_idx) / period) * 100
        
        aroon_osc = aroon_up - aroon_down
        
        # 交叉信号
        bullish_cross = (aroon_up > aroon_down) & (aroon_osc < threshold) & (aroon_osc.shift(1) < 0)
        bearish_cross = (aroon_up < aroon_down) & (aroon_osc > -threshold) & (aroon_osc.shift(1) > 0)
        
        return {
            'aroon_up': aroon_up,
            'aroon_down': aroon_down,
            'aroon_osc': aroon_osc,
            'bullish_cross': bullish_cross,
            'bearish_cross': bearish_cross
        }


class SignalStrengthCalculator:
    """信号强度评估器"""
    
    @staticmethod
    def calculate_confluence(buy_signals: Dict[str, pd.Series]) -> pd.Series:
        """
        计算信号共鸣度（多个信号同时出现）
        
        Args:
            buy_signals: 各个信号的布尔Series字典
        
        Returns:
            共鸣度（0-1，值越高表示同时出现的信号越多）
        """
        if not buy_signals:
            return pd.Series(0.0)
        
        signals_df = pd.concat(buy_signals.values(), axis=1).fillna(0)
        signal_count = signals_df.sum(axis=1)
        confluence = signal_count / len(buy_signals)
        
        return confluence
    
    @staticmethod
    def calculate_signal_score(ohlc: pd.DataFrame,
                             signals_instance: AdvancedTradingSignals) -> pd.Series:
        """
        计算综合信号评分（0-100）
        
        整合所有7个信号的权重评分
        """
        close = ohlc['close']
        high = ohlc['high']
        low = ohlc['low']
        
        # 各信号的权重
        weights = {
            'donchian': 0.15,
            'ma_system': 0.15,
            'ama': 0.10,
            'keltner': 0.15,
            'rsi_cost': 0.15,
            'macd': 0.15,
            'adx': 0.15
        }
        
        scores = {}
        
        # 1. 唐奇安突破
        donchian = AdvancedTradingSignals.donchian_breakout(high, low)
        scores['donchian'] = donchian['buy_signal'].astype(float) * 100
        
        # 2. MA系统
        ma_sys = AdvancedTradingSignals.professional_ma_system(close)
        scores['ma_system'] = (ma_sys['bullish_alignment'].astype(float) * 100)
        
        # 3. AMA
        ama = AdvancedTradingSignals.kaufman_adaptive_ma(close)
        ama_signal = (close > ama['ama']).astype(float) * 100
        scores['ama'] = ama_signal
        
        # 4. Keltner
        kelt = AdvancedTradingSignals.atr_keltner_channel(high, low, close)
        scores['keltner'] = kelt['breakout_up'].astype(float) * 100
        
        # 5. RSI成本线
        rsi_cost = AdvancedTradingSignals.rsi_cost_line(close)
        scores['rsi_cost'] = rsi_cost['buy_signal'].astype(float) * 100
        
        # 6. MACD背离
        macd_div = AdvancedTradingSignals.macd_divergence(close)
        scores['macd'] = macd_div['bottom_divergence'].astype(float) * 100
        
        # 7. ADX
        adx = AdvancedTradingSignals.adx_trend_identifier(high, low)
        scores['adx'] = adx['weak_to_strong'].astype(float) * 100
        
        # 加权融合
        total_score = pd.Series(0.0, index=close.index)
        for signal_name, weight in weights.items():
            total_score += scores[signal_name] * weight
        
        return total_score.fillna(0)
