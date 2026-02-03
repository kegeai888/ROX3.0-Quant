
import pandas as pd
import numpy as np

def calculate_dark_pool_fund(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算暗盘资金指标

    :param df: 包含 OHLC 和资金流数据的合并 DataFrame
    :return: 包含暗盘资金指标的 DataFrame
    """
    df = df.sort_values('日期').reset_index(drop=True)

    # 计算调整幅度所需的各个分量
    prev_close = df['收盘'].shift(1)
    df['高低开'] = (df['开盘'] - prev_close) / prev_close
    df['实体涨跌幅'] = (df['收盘'] - df['开盘']) / df['开盘']
    df['冲高'] = (df['最高'] - df['开盘']) / df['开盘']
    df['回落'] = (df['收盘'] - df['最高']) / df['最高']
    df['杀跌'] = (df['最低'] - df['开盘']) / df['开盘']
    df['V反'] = (df['收盘'] - df['最低']) / df['最低']

    # 计算总的调整幅度
    adjustment_factor1 = (df['高低开'] + df['实体涨跌幅'] + df['冲高'] + df['回落'] + df['杀跌'] + df['V反']).fillna(0)
    df['调整幅度'] = np.where(adjustment_factor1 >= 1, 0.8, adjustment_factor1)

    # 使用 akshare 提供的净流入数据
    # '中单净流入-净额', '小单净流入-净额'
    medium_net_inflow = df.get('中单净流入-净额', 0)
    small_net_inflow = df.get('小单净流入-净额', 0)

    # 将“调整幅度”应用于中小单的净流入，以估算暗盘资金
    # 这是对原始公式在数据限制下的一个合理近似
    dark_pool_fund = (medium_net_inflow + small_net_inflow) * df['调整幅度']
    df['暗盘资金'] = dark_pool_fund.fillna(0)

    # 为了清晰，只返回必要列和结果
    result_df = df[['日期', '收盘', '暗盘资金']].copy()
    
    return result_df
