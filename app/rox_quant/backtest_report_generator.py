"""
P3.5 Day 4: 报告生成器 - BacktestReportGenerator
作用：生成专业的HTML/JSON回测报告，包含所有图表和数据
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import json
from datetime import datetime


class BacktestReportGenerator:
    """回测报告生成器"""
    
    def __init__(self):
        self.title = "回测分析报告"
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def generate_html_report(self,
                            performance_report,
                            portfolio_values: List[float],
                            portfolio_dates: List,
                            trades: List,
                            factor_analysis: Optional[Dict] = None,
                            overfitting_report: Optional[Dict] = None,
                            filename: str = 'backtest_report.html') -> str:
        """
        生成完整的HTML报告
        
        Args:
            performance_report: 性能报告对象
            portfolio_values: 账户净值序列
            portfolio_dates: 日期序列
            trades: 交易记录列表
            factor_analysis: 因子分析结果（可选）
            overfitting_report: 过拟合检测结果（可选）
            filename: 输出文件名
        
        Returns:
            HTML字符串
        """
        html = self._create_html_header()
        html += self._create_summary_section(performance_report)
        html += self._create_charts_section(portfolio_values, trades)
        html += self._create_trades_section(trades)
        
        if factor_analysis:
            html += self._create_factor_section(factor_analysis)
        
        if overfitting_report:
            html += self._create_overfitting_section(overfitting_report)
        
        html += self._create_html_footer()
        
        return html
    
    def _create_html_header(self) -> str:
        """创建HTML头部"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        header h1 {{
            margin-bottom: 10px;
            font-size: 2.5em;
        }}
        header p {{
            opacity: 0.9;
            font-size: 14px;
        }}
        .content {{
            padding: 30px 20px;
        }}
        section {{
            margin-bottom: 40px;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .metric-card {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}
        .metric-card h3 {{
            color: #667eea;
            font-size: 12px;
            margin-bottom: 10px;
            text-transform: uppercase;
        }}
        .metric-card .value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .metric-card .unit {{
            color: #999;
            font-size: 12px;
        }}
        .chart-container {{
            position: relative;
            height: 400px;
            margin: 30px 0;
            background: white;
            padding: 15px;
            border-radius: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        table th {{
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #ddd;
        }}
        table tr:hover {{
            background: #f0f0f0;
        }}
        .positive {{
            color: #28a745;
        }}
        .negative {{
            color: #dc3545;
        }}
        footer {{
            background: #f0f0f0;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 12px;
            border-top: 1px solid #ddd;
        }}
        .warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            border-radius: 4px;
            margin: 15px 0;
        }}
        .success {{
            background: #d4edda;
            border-left: 4px solid #28a745;
            padding: 15px;
            border-radius: 4px;
            margin: 15px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 {self.title}</h1>
            <p>生成时间: {self.timestamp}</p>
        </header>
        <div class="content">
"""
    
    def _create_summary_section(self, report) -> str:
        """创建摘要部分"""
        profit_class = 'positive' if report.net_profit > 0 else 'negative'
        overfitting_msg = '<div class="warning">⚠️ 注意: 该报告显示过拟合风险</div>'
        
        return f"""
            <section>
                <h2>📈 回测摘要</h2>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <h3>初始资金</h3>
                        <div class="value">¥{report.initial_capital:,.0f}</div>
                    </div>
                    <div class="metric-card">
                        <h3>最终资金</h3>
                        <div class="value">¥{report.final_capital:,.0f}</div>
                    </div>
                    <div class="metric-card">
                        <h3 class="{profit_class}">净利润</h3>
                        <div class="value {profit_class}">¥{report.net_profit:,.0f}</div>
                    </div>
                    <div class="metric-card">
                        <h3>总收益率</h3>
                        <div class="value {profit_class}">{report.total_return:.2f}%</div>
                    </div>
                    <div class="metric-card">
                        <h3>胜率</h3>
                        <div class="value">{report.win_rate:.2f}%</div>
                    </div>
                    <div class="metric-card">
                        <h3>盈亏比</h3>
                        <div class="value">{report.profit_factor:.2f}</div>
                    </div>
                    <div class="metric-card">
                        <h3>最大回撤</h3>
                        <div class="value">{report.max_drawdown:.2f}%</div>
                    </div>
                    <div class="metric-card">
                        <h3>夏普比</h3>
                        <div class="value">{report.sharpe_ratio:.2f}</div>
                    </div>
                </div>
            </section>
"""
    
    def _create_charts_section(self, portfolio_values: List[float], trades: List) -> str:
        """创建图表部分"""
        # 准备数据用于Chart.js
        labels = list(range(len(portfolio_values)))
        data_str = json.dumps(portfolio_values)
        trades_data = json.dumps([(t.entry_price, t.exit_price) for t in trades if t.is_closed])
        
        return f"""
            <section>
                <h2>📊 净值曲线</h2>
                <div class="chart-container">
                    <canvas id="equityChart"></canvas>
                </div>
                <script>
                    const ctx = document.getElementById('equityChart').getContext('2d');
                    const data = {data_str};
                    const labels = Array.from({{length: data.length}}, (_, i) => i);
                    
                    new Chart(ctx, {{
                        type: 'line',
                        data: {{
                            labels: labels,
                            datasets: [{{
                                label: '账户净值',
                                data: data,
                                borderColor: '#667eea',
                                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                                borderWidth: 2,
                                fill: true,
                                tension: 0.1
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{
                                    display: true,
                                    position: 'top'
                                }}
                            }},
                            scales: {{
                                y: {{
                                    beginAtZero: false
                                }}
                            }}
                        }}
                    }});
                </script>
            </section>
"""
    
    def _create_trades_section(self, trades: List) -> str:
        """创建交易记录部分"""
        trade_rows = ""
        for i, trade in enumerate(trades[:20], 1):  # 显示前20笔
            if trade.is_closed:
                profit_class = 'positive' if trade.profit > 0 else 'negative'
                trade_rows += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{trade.entry_time}</td>
                        <td>¥{trade.entry_price:.2f}</td>
                        <td>{trade.entry_qty}</td>
                        <td>{trade.exit_time}</td>
                        <td>¥{trade.exit_price:.2f}</td>
                        <td class="{profit_class}">¥{trade.profit:.2f}</td>
                        <td class="{profit_class}">{trade.profit_pct:.2f}%</td>
                    </tr>
                """
        
        return f"""
            <section>
                <h2>📝 交易记录</h2>
                <table>
                    <thead>
                        <tr>
                            <th>序号</th>
                            <th>进场时间</th>
                            <th>进场价</th>
                            <th>数量</th>
                            <th>离场时间</th>
                            <th>离场价</th>
                            <th>利润</th>
                            <th>收益率</th>
                        </tr>
                    </thead>
                    <tbody>
                        {trade_rows}
                    </tbody>
                </table>
            </section>
"""
    
    def _create_factor_section(self, factor_analysis: Dict) -> str:
        """创建因子分析部分"""
        factor_rows = ""
        for factor in factor_analysis.get('ranking', [])[:10]:
            factor_rows += f"""
                <tr>
                    <td>{factor['factor_name']}</td>
                    <td>{factor['win_rate']:.2f}%</td>
                    <td>{factor['contribution_pct']:.2f}%</td>
                    <td>{factor['effectiveness_score']:.1f}/100</td>
                </tr>
            """
        
        return f"""
            <section>
                <h2>🎯 因子分析</h2>
                <table>
                    <thead>
                        <tr>
                            <th>因子名称</th>
                            <th>胜率</th>
                            <th>贡献度</th>
                            <th>有效性评分</th>
                        </tr>
                    </thead>
                    <tbody>
                        {factor_rows}
                    </tbody>
                </table>
            </section>
"""
    
    def _create_overfitting_section(self, overfitting_report: Dict) -> str:
        """创建过拟合检测部分"""
        is_overfitted = overfitting_report.get('is_overfitted', False)
        alert = f"<div class=\"warning\">⚠️ 警告: 策略存在过拟合风险!</div>" if is_overfitted else ""
        
        window_rows = ""
        for w in overfitting_report.get('windows', [])[:5]:
            window_rows += f"""
                <tr>
                    <td>{w['window_name']}</td>
                    <td>{w['total_trades']}</td>
                    <td>{w['win_rate']:.2f}%</td>
                    <td>¥{w['net_profit']:,.0f}</td>
                </tr>
            """
        
        return f"""
            <section>
                <h2>⚠️ 过拟合检测</h2>
                {alert}
                <div class="metrics-grid">
                    <div class="metric-card">
                        <h3>过拟合指数</h3>
                        <div class="value">{overfitting_report.get('overfitting_score', 0):.1f}/100</div>
                    </div>
                    <div class="metric-card">
                        <h3>稳定性指数</h3>
                        <div class="value">{overfitting_report.get('stability_index', 0):.1f}/100</div>
                    </div>
                    <div class="metric-card">
                        <h3>鲁棒性评分</h3>
                        <div class="value">{overfitting_report.get('robustness_score', 0):.1f}/100</div>
                    </div>
                </div>
                <h3>时间窗口结果</h3>
                <table>
                    <thead>
                        <tr>
                            <th>窗口</th>
                            <th>交易数</th>
                            <th>胜率</th>
                            <th>净利润</th>
                        </tr>
                    </thead>
                    <tbody>
                        {window_rows}
                    </tbody>
                </table>
            </section>
"""
    
    def _create_html_footer(self) -> str:
        """创建HTML脚部"""
        return """
        </div>
        <footer>
            <p>本报告由 Rox Quant 回测系统自动生成</p>
            <p>仅供学习研究使用，不构成投资建议</p>
        </footer>
    </div>
</body>
</html>
"""
    
    def generate_json_report(self,
                            performance_report,
                            factor_analysis: Optional[Dict] = None,
                            overfitting_report: Optional[Dict] = None) -> str:
        """生成JSON格式报告"""
        report = {
            'timestamp': self.timestamp,
            'performance': {
                'total_trades': performance_report.total_trades,
                'winning_trades': performance_report.winning_trades,
                'losing_trades': performance_report.losing_trades,
                'win_rate': round(performance_report.win_rate, 2),
                'total_profit': round(performance_report.total_profit, 2),
                'total_loss': round(performance_report.total_loss, 2),
                'net_profit': round(performance_report.net_profit, 2),
                'profit_factor': round(performance_report.profit_factor, 2),
                'max_drawdown': round(performance_report.max_drawdown, 2),
                'total_return': round(performance_report.total_return, 2),
                'annual_return': round(performance_report.annual_return, 2),
                'annual_volatility': round(performance_report.annual_volatility, 2),
                'sharpe_ratio': round(performance_report.sharpe_ratio, 2),
            }
        }
        
        if factor_analysis:
            report['factor_analysis'] = factor_analysis
        
        if overfitting_report:
            report['overfitting_analysis'] = overfitting_report
        
        return json.dumps(report, ensure_ascii=False, indent=2)
