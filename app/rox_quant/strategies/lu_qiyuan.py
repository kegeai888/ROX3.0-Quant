import pandas as pd
import numpy as np
import datetime

class LuQiyuanStrategy:
    """
    卢麒元“中庸之道”投资策略实现
    
    核心哲学：
    1. 中 (Equilibrium): 寻找价值与价格的背离。
    2. 庸 (Rhythm): 通过律动（波段操作）降低持仓成本。
    3. 334法则: 30%底仓 + 30%律动 + 40%预备队。
    """
    
    def __init__(self, initial_capital=1000000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = 0
        self.cost_basis = 0.0 # 持仓成本
        self.history = []
        
        # 334 Config
        self.pct_base = 0.3
        self.pct_swing = 0.3
        self.pct_reserve = 0.4
        
        # Swing State
        self.swing_active = False # 是否持有律动仓位
        
    def run_backtest(self, df: pd.DataFrame):
        """
        运行回测
        :param df: 包含 date, open, high, low, close, volume 的 DataFrame
        """
        if df.empty: return {}
        
        # 1. 计算指标 (一板斧: MACD)
        # EMA12, EMA26, DIF, DEA, MACD
        df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['dif'] = df['ema12'] - df['ema26']
        df['dea'] = df['dif'].ewm(span=9, adjust=False).mean()
        df['macd'] = 2 * (df['dif'] - df['dea'])
        
        logs = []
        equity_curve = []
        cost_curve = []
        
        # 2. 模拟逐日交易
        # 假设第一天建底仓 (30%)
        first_price = df.iloc[0]['close']
        base_shares = int((self.initial_capital * self.pct_base) / first_price / 100) * 100
        self.cash -= base_shares * first_price
        self.positions += base_shares
        self.cost_basis = first_price # 初始成本
        
        logs.append({
            "date": str(df.iloc[0]['date']),
            "action": "建底仓",
            "price": first_price,
            "shares": base_shares,
            "cost": self.cost_basis,
            "reason": "策略启动，建立30%底仓"
        })
        
        for i in range(1, len(df)):
            curr = df.iloc[i]
            prev = df.iloc[i-1]
            date_str = str(curr['date'])
            price = curr['close']
            
            # --- 信号判断 (The Yong / Rhythm) ---
            
            # 金叉: DIF 上穿 DEA
            gold_cross = (prev['dif'] < prev['dea']) and (curr['dif'] > curr['dea'])
            # 死叉: DIF 下穿 DEA
            dead_cross = (prev['dif'] > prev['dea']) and (curr['dif'] < curr['dea'])
            
            # 律动买入逻辑:
            # 1. 没有律动仓位
            # 2. 出现金叉 OR 价格急跌 (这里简化为金叉)
            # 3. 使用预备队资金的一半进行买入 (避免一次用光)
            if not self.swing_active and gold_cross:
                # 能够使用的最大律动资金 (30% + 40%预备队的一部分)
                # 这里严格按照30%律动仓位配置
                swing_capital = self.initial_capital * self.pct_swing
                if self.cash >= swing_capital:
                    shares_to_buy = int(swing_capital / price / 100) * 100
                    if shares_to_buy > 0:
                        cost_of_buy = shares_to_buy * price
                        self.cash -= cost_of_buy
                        self.positions += shares_to_buy
                        self.swing_active = True
                        
                        # 重新计算成本 (加权平均)
                        # 但卢老师的逻辑是：律动是为了降成本，通常律动部分的盈亏单独结算来冲抵成本
                        # 这里我们采用“加权平均”展示综合成本
                        # self.cost_basis = ((self.positions - shares_to_buy) * self.cost_basis + cost_of_buy) / self.positions
                        
                        logs.append({
                            "date": date_str,
                            "action": "律动买入",
                            "price": price,
                            "shares": shares_to_buy,
                            "cost": self.cost_basis,
                            "reason": "MACD金叉，启动律动仓位"
                        })

            # 律动卖出逻辑:
            # 1. 持有律动仓位
            # 2. 出现死叉 OR 达到止盈目标
            elif self.swing_active and dead_cross:
                # 卖出律动部分 (30%)
                # 实际上是卖出刚才买入的数量
                shares_to_sell = int(self.initial_capital * self.pct_swing / first_price / 100) * 100 # 近似
                # 为了简化，卖出当前持仓 - 底仓
                current_swing_shares = self.positions - base_shares
                
                if current_swing_shares > 0:
                    revenue = current_swing_shares * price
                    profit = revenue - (current_swing_shares * self.cost_basis) # 这里的算法可以优化
                    
                    self.cash += revenue
                    self.positions -= current_swing_shares
                    self.swing_active = False
                    
                    # 核心逻辑：用盈利冲抵底仓成本
                    # 新持仓成本 = (旧总市值 - 卖出盈利) / 剩余股数  <-- 这种算法能体现成本下降
                    # 实际上：Total Cost Basis = Total Invested - Realized Profit
                    # 简化计算：
                    # Realized Profit from this swing
                    # profit = (price - buy_price_of_swing) * shares
                    # 这里我们用一种直观的方式：
                    # 每次卖出赚的钱，直接从剩余持仓的总成本里扣除
                    
                    # 简单的“摊薄成本”算法：
                    # 剩余持仓的总买入成本
                    remaining_cost = (base_shares * self.cost_basis) 
                    # 律动产生的利润（假设买入价就是上次记录的成本，虽然不完全准确，但在加权平均下近似）
                    # 更精确的做法是记录每一笔 Trade。
                    # 这里模拟：假设本次律动获利 X 元，这 X 元视为底仓的成本返还
                    
                    # 重新修正逻辑：
                    # 成本 = (初始投入 - 累计落袋现金) / 当前持仓
                    # 这会导致成本变成负数，符合卢老师目标
                    
                    logs.append({
                        "date": date_str,
                        "action": "律动卖出",
                        "price": price,
                        "shares": current_swing_shares,
                        "cost": self.cost_basis, # 稍后统一计算曲线
                        "reason": "MACD死叉，获利了结"
                    })
            
            # 每日结算
            total_assets = self.cash + (self.positions * price)
            
            # 计算动态持仓成本 (Cost Basis)
            # 卢氏成本 = (总投入本金 - 当前现金) / 当前持仓数量
            # 如果现金 > 初始本金，说明已经回本且赚钱，成本为负
            if self.positions > 0:
                dynamic_cost = (self.initial_capital - self.cash) / self.positions
            else:
                dynamic_cost = 0
                
            equity_curve.append({"time": date_str, "value": total_assets})
            cost_curve.append({"time": date_str, "value": dynamic_cost})
            self.cost_basis = dynamic_cost

        # Calculate metrics
        metrics = {}
        if equity_curve:
            df_eq = pd.DataFrame(equity_curve)
            df_eq["returns"] = df_eq["value"].pct_change().fillna(0)
            
            total_return = (df_eq["value"].iloc[-1] / df_eq["value"].iloc[0]) - 1
            days = len(df_eq)
            annual_return = 0.0
            if days > 1:
                annual_return = (1 + total_return) ** (252 / days) - 1
            
            volatility = df_eq["returns"].std() * np.sqrt(252)
            risk_free_rate = 0.03
            sharpe = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
            
            df_eq["cum_max"] = df_eq["value"].cummax()
            df_eq["drawdown"] = (df_eq["value"] - df_eq["cum_max"]) / df_eq["cum_max"]
            max_drawdown = df_eq["drawdown"].min()
            
            metrics = {
                "annualized_return": round(annual_return * 100, 2),
                "volatility": round(volatility * 100, 2),
                "sharpe_ratio": round(sharpe, 2),
                "max_drawdown": round(max_drawdown * 100, 2)
            }

        return {
            "logs": logs,
            "equity": equity_curve,
            "cost": cost_curve,
            "metrics": metrics,
            "summary": {
                "initial": self.initial_capital,
                "final": equity_curve[-1]['value'] if equity_curve else 0,
                "return": f"{((equity_curve[-1]['value']/self.initial_capital)-1)*100:.2f}%" if equity_curve else "0%",
                "final_cost": f"{cost_curve[-1]['value']:.2f}" if cost_curve else "0"
            }
        }
