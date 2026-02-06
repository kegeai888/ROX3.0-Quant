/**
 * Feature UI Handlers - JavaScript module for new feature modals
 * Handles: Portfolio, Risk Dashboard, Auto Trade, Replay, Condition Orders, TDX Formula
 */

// ==================== PORTFOLIO ====================
export function openPortfolioModal() {
    const modal = document.getElementById('portfolio-modal');
    if (modal) {
        modal.classList.remove('hidden');
        loadPortfolioPositions();
        initPortfolioTabs();
    }
}

function initPortfolioTabs() {
    const tabs = document.querySelectorAll('.portfolio-tab-btn');
    tabs.forEach(tab => {
        tab.onclick = () => {
            // Reset all tabs
            tabs.forEach(t => {
                t.classList.remove('text-sky-400', 'border-b-2', 'border-sky-400');
                t.classList.add('text-slate-400');
            });
            // Activate clicked tab
            tab.classList.add('text-sky-400', 'border-b-2', 'border-sky-400');
            tab.classList.remove('text-slate-400');

            // Show/hide content
            document.querySelectorAll('.portfolio-tab-content').forEach(c => c.classList.add('hidden'));
            const target = tab.dataset.tab;
            const content = document.getElementById(`portfolio-${target}`);
            if (content) content.classList.remove('hidden');

            // Load data for the tab
            if (target === 'positions') loadPortfolioPositions();
            if (target === 'history') loadPortfolioHistory();
        };
    });
}

async function loadPortfolioPositions() {
    const container = document.getElementById('portfolio-positions-content');
    if (!container) return;

    try {
        const resp = await fetch('/api/portfolio/positions', { credentials: 'include' });
        const data = await resp.json();

        if (!resp.ok) {
            container.innerHTML = `<p class="text-rose-400">${data.error || '加载失败'}</p>`;
            return;
        }

        const positions = data.positions || [];
        if (positions.length === 0) {
            container.innerHTML = '<p class="text-slate-500">暂无持仓</p>';
            return;
        }

        let html = `
            <table class="w-full text-sm">
                <thead class="text-slate-500 text-xs border-b border-slate-700">
                    <tr>
                        <th class="text-left py-2">股票</th>
                        <th class="text-right py-2">持仓</th>
                        <th class="text-right py-2">成本</th>
                        <th class="text-right py-2">现价</th>
                        <th class="text-right py-2">盈亏</th>
                    </tr>
                </thead>
                <tbody>
        `;

        positions.forEach(p => {
            const pnlClass = p.pnl >= 0 ? 'text-up' : 'text-down';
            html += `
                <tr class="border-b border-slate-800 hover:bg-slate-800/50">
                    <td class="py-2">
                        <span class="font-bold text-slate-200">${p.stock_name || p.stock_code}</span>
                        <span class="text-xs text-slate-500 ml-1">${p.stock_code}</span>
                    </td>
                    <td class="text-right font-mono">${p.quantity}</td>
                    <td class="text-right font-mono">${p.avg_cost?.toFixed(2) || '--'}</td>
                    <td class="text-right font-mono">${p.current_price?.toFixed(2) || '--'}</td>
                    <td class="text-right font-mono ${pnlClass}">${p.pnl >= 0 ? '+' : ''}${p.pnl?.toFixed(2) || '--'}</td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (e) {
        console.error('Load portfolio failed:', e);
        container.innerHTML = '<p class="text-rose-400">加载失败</p>';
    }
}

async function loadPortfolioHistory() {
    const container = document.getElementById('portfolio-history-content');
    if (!container) return;

    try {
        const resp = await fetch('/api/portfolio/trades', { credentials: 'include' });
        const data = await resp.json();

        if (!resp.ok) {
            container.innerHTML = `<p class="text-rose-400">${data.error || '加载失败'}</p>`;
            return;
        }

        const trades = data.trades || [];
        if (trades.length === 0) {
            container.innerHTML = '<p class="text-slate-500">暂无交易记录</p>';
            return;
        }

        let html = `
            <table class="w-full text-sm">
                <thead class="text-slate-500 text-xs border-b border-slate-700">
                    <tr>
                        <th class="text-left py-2">时间</th>
                        <th class="text-left py-2">股票</th>
                        <th class="text-center py-2">方向</th>
                        <th class="text-right py-2">数量</th>
                        <th class="text-right py-2">价格</th>
                    </tr>
                </thead>
                <tbody>
        `;

        trades.forEach(t => {
            const dirClass = t.direction === 'buy' ? 'text-up bg-up-dim' : 'text-down bg-down-dim';
            html += `
                <tr class="border-b border-slate-800">
                    <td class="py-2 text-xs text-slate-400">${t.time || t.created_at}</td>
                    <td class="py-2">${t.stock_name || t.stock_code}</td>
                    <td class="py-2 text-center"><span class="px-2 py-0.5 rounded text-xs ${dirClass}">${t.direction === 'buy' ? '买入' : '卖出'}</span></td>
                    <td class="py-2 text-right font-mono">${t.quantity}</td>
                    <td class="py-2 text-right font-mono">${t.price?.toFixed(2)}</td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (e) {
        console.error('Load history failed:', e);
        container.innerHTML = '<p class="text-rose-400">加载失败</p>';
    }
}

export async function submitOrder() {
    const code = document.getElementById('order-stock-code')?.value?.trim();
    const direction = document.getElementById('order-direction')?.value;
    const quantity = parseInt(document.getElementById('order-quantity')?.value) || 1;
    const price = parseFloat(document.getElementById('order-price')?.value) || null;

    if (!code) {
        if (typeof showToast === 'function') showToast('错误', 'error', '请输入股票代码');
        return;
    }

    try {
        const resp = await fetch('/api/portfolio/order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ stock_code: code, direction, quantity, price })
        });

        const data = await resp.json();
        if (resp.ok) {
            if (typeof showToast === 'function') showToast('成功', 'success', '订单已提交');
            loadPortfolioPositions();
        } else {
            if (typeof showToast === 'function') showToast('失败', 'error', data.error || '下单失败');
        }
    } catch (e) {
        console.error('Submit order failed:', e);
        if (typeof showToast === 'function') showToast('失败', 'error', '网络错误');
    }
}

// ==================== RISK DASHBOARD ====================
export function openRiskDashboard() {
    const modal = document.getElementById('risk-dashboard-modal');
    if (modal) {
        modal.classList.remove('hidden');
        loadRiskData();
    }
}

async function loadRiskData() {
    try {
        const [varResp, exposureResp] = await Promise.all([
            fetch('/api/portfolio/risk/var', { credentials: 'include' }),
            fetch('/api/portfolio/risk/exposure', { credentials: 'include' })
        ]);

        const varData = await varResp.json().catch(() => ({}));
        const exposureData = await exposureResp.json().catch(() => ({}));

        // Update VaR
        const varEl = document.getElementById('risk-var');
        if (varEl) varEl.textContent = varData.var_95 ? `${(varData.var_95 * 100).toFixed(2)}%` : '--%';

        // Update Max Drawdown
        const ddEl = document.getElementById('risk-max-dd');
        if (ddEl) ddEl.textContent = varData.max_drawdown ? `${(varData.max_drawdown * 100).toFixed(2)}%` : '--%';

        // Update Sharpe
        const sharpeEl = document.getElementById('risk-sharpe');
        if (sharpeEl) sharpeEl.textContent = varData.sharpe_ratio?.toFixed(2) || '--';

        // Update Sector Exposure
        const sectorEl = document.getElementById('risk-sector-exposure');
        if (sectorEl && exposureData.sectors) {
            let html = '<div class="flex flex-wrap gap-2">';
            Object.entries(exposureData.sectors).forEach(([sector, pct]) => {
                html += `<span class="px-2 py-1 bg-slate-700 rounded text-xs">${sector}: <span class="text-amber-400 font-mono">${(pct * 100).toFixed(1)}%</span></span>`;
            });
            html += '</div>';
            sectorEl.innerHTML = html || '<p class="text-slate-500">无数据</p>';
        }

        // Update Concentration
        const concEl = document.getElementById('risk-concentration');
        if (concEl && exposureData.top_5_concentration) {
            concEl.innerHTML = `
                <div class="text-amber-400 font-mono text-lg">${(exposureData.top_5_concentration * 100).toFixed(1)}%</div>
                <div class="text-xs text-slate-500 mt-1">前5大持仓占比</div>
            `;
        }
    } catch (e) {
        console.error('Load risk data failed:', e);
    }
}

// ==================== AUTO TRADE ====================
export function openAutoTradePanel() {
    const modal = document.getElementById('auto-trade-modal');
    if (modal) modal.classList.remove('hidden');
}

export async function executeAutoTrade() {
    const amount = parseFloat(document.getElementById('auto-trade-amount')?.value) || 10000;
    const threshold = parseInt(document.getElementById('auto-trade-threshold')?.value) || 50;
    const resultEl = document.getElementById('auto-trade-result');

    if (resultEl) resultEl.innerHTML = '<i class="fas fa-circle-notch fa-spin text-cyan-400 mr-1"></i> 执行中...';

    try {
        const resp = await fetch('/api/portfolio/auto-trade', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ amount, signal_threshold: threshold })
        });

        const data = await resp.json();
        if (resp.ok) {
            resultEl.innerHTML = `<span class="text-emerald-400"><i class="fas fa-check mr-1"></i>${data.message || '执行成功'}</span>`;
        } else {
            resultEl.innerHTML = `<span class="text-rose-400"><i class="fas fa-times mr-1"></i>${data.error || '执行失败'}</span>`;
        }
    } catch (e) {
        console.error('Auto trade failed:', e);
        resultEl.innerHTML = '<span class="text-rose-400">网络错误</span>';
    }
}

// ==================== REPLAY ====================
export function openReplayChart() {
    const modal = document.getElementById('replay-modal');
    if (modal) modal.classList.remove('hidden');
}

export async function loadReplayChart() {
    const code = document.getElementById('replay-stock-code')?.value?.trim() || window.currentStockCode || '600519';
    const container = document.getElementById('replay-chart-container');
    if (!container) return;

    container.innerHTML = '<div class="flex items-center justify-center h-full text-slate-500"><i class="fas fa-circle-notch fa-spin mr-2"></i>加载中...</div>';

    try {
        const resp = await fetch(`/api/portfolio/replay/chart/${code}`, { credentials: 'include' });
        const data = await resp.json();

        if (!resp.ok || data.error) {
            container.innerHTML = `<div class="flex items-center justify-center h-full text-rose-400">${data.error || '加载失败'}</div>`;
            return;
        }

        // Initialize ECharts
        if (typeof echarts !== 'undefined') {
            let chart = echarts.init(container);

            const dates = data.dates || [];
            const ohlc = data.ohlc || [];
            const buyPoints = data.buy_points || [];
            const sellPoints = data.sell_points || [];

            // Create mark points for buy/sell
            const markData = [];
            buyPoints.forEach(p => markData.push({ name: '买入', coord: [p.date, p.price], value: 'B', itemStyle: { color: '#ff4d4f' } }));
            sellPoints.forEach(p => markData.push({ name: '卖出', coord: [p.date, p.price], value: 'S', itemStyle: { color: '#00b578' } }));

            chart.setOption({
                backgroundColor: 'transparent',
                tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
                xAxis: { type: 'category', data: dates, axisLabel: { color: '#94a3b8', fontSize: 10 } },
                yAxis: { type: 'value', scale: true, axisLabel: { color: '#94a3b8', fontSize: 10 } },
                series: [{
                    type: 'candlestick',
                    data: ohlc,
                    itemStyle: { color: '#ff4d4f', color0: '#00b578', borderColor: '#ff4d4f', borderColor0: '#00b578' },
                    markPoint: {
                        symbol: 'pin',
                        symbolSize: 30,
                        data: markData,
                        label: { show: true, formatter: '{b}', fontSize: 10 }
                    }
                }]
            });

            new ResizeObserver(() => chart.resize()).observe(container);
        } else {
            container.innerHTML = '<div class="flex items-center justify-center h-full text-rose-400">ECharts 未加载</div>';
        }
    } catch (e) {
        console.error('Load replay failed:', e);
        container.innerHTML = '<div class="flex items-center justify-center h-full text-rose-400">加载失败</div>';
    }
}

// ==================== CONDITION ORDERS ====================
export function openConditionOrders() {
    const modal = document.getElementById('condition-orders-modal');
    if (modal) {
        modal.classList.remove('hidden');
        loadConditionOrders();
    }
}

async function loadConditionOrders() {
    const container = document.getElementById('condition-orders-list');
    if (!container) return;

    try {
        const resp = await fetch('/api/trade/condition-orders', { credentials: 'include' });
        const data = await resp.json();

        if (!resp.ok) {
            container.innerHTML = `<p class="text-rose-400 text-center py-4">${data.error || '加载失败'}</p>`;
            return;
        }

        const orders = data.orders || [];
        if (orders.length === 0) {
            container.innerHTML = '<p class="text-slate-500 text-center py-4">暂无条件单</p>';
            return;
        }

        let html = '';
        orders.forEach(o => {
            const triggerText = {
                'price_above': `价格 > ${o.trigger_value}`,
                'price_below': `价格 < ${o.trigger_value}`,
                'pct_above': `涨幅 > ${o.trigger_value}%`,
                'pct_below': `跌幅 > ${o.trigger_value}%`
            }[o.trigger_type] || o.trigger_type;

            const actionText = { 'buy': '买入', 'sell': '卖出', 'alert': '提醒' }[o.action] || o.action;

            html += `
                <div class="flex items-center justify-between bg-slate-800/50 rounded-lg p-3">
                    <div>
                        <span class="font-bold text-slate-200">${o.stock_code}</span>
                        <span class="text-xs text-slate-500 ml-2">${triggerText}</span>
                        <span class="px-2 py-0.5 rounded text-xs bg-lime-900/50 text-lime-400 ml-2">${actionText}</span>
                    </div>
                    <button onclick="deleteConditionOrder('${o.id}')" class="text-rose-500 hover:text-rose-400 text-xs">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
        });

        container.innerHTML = html;
    } catch (e) {
        console.error('Load condition orders failed:', e);
        container.innerHTML = '<p class="text-rose-400 text-center py-4">加载失败</p>';
    }
}

export async function createConditionOrder() {
    const code = document.getElementById('cond-stock-code')?.value?.trim();
    const triggerType = document.getElementById('cond-trigger-type')?.value;
    const triggerValue = parseFloat(document.getElementById('cond-trigger-value')?.value);
    const action = document.getElementById('cond-action')?.value;

    if (!code || !triggerValue) {
        if (typeof showToast === 'function') showToast('错误', 'error', '请填写完整');
        return;
    }

    try {
        const resp = await fetch('/api/trade/condition-orders', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ stock_code: code, trigger_type: triggerType, trigger_value: triggerValue, action })
        });

        const data = await resp.json();
        if (resp.ok) {
            if (typeof showToast === 'function') showToast('成功', 'success', '条件单已创建');
            loadConditionOrders();
            // Clear inputs
            document.getElementById('cond-stock-code').value = '';
            document.getElementById('cond-trigger-value').value = '';
        } else {
            if (typeof showToast === 'function') showToast('失败', 'error', data.error || '创建失败');
        }
    } catch (e) {
        console.error('Create condition order failed:', e);
        if (typeof showToast === 'function') showToast('失败', 'error', '网络错误');
    }
}

export async function deleteConditionOrder(orderId) {
    if (!confirm('确定删除此条件单？')) return;

    try {
        const resp = await fetch(`/api/trade/condition-orders/${orderId}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (resp.ok) {
            if (typeof showToast === 'function') showToast('成功', 'success', '已删除');
            loadConditionOrders();
        }
    } catch (e) {
        console.error('Delete condition order failed:', e);
    }
}

// ==================== TDX FORMULA ====================
export function openTdxFormula() {
    const modal = document.getElementById('tdx-formula-modal');
    if (modal) modal.classList.remove('hidden');
}

export async function calculateTdxFormula() {
    const code = document.getElementById('tdx-stock-code')?.value?.trim() || window.currentStockCode || '600519';
    const period = document.getElementById('tdx-period')?.value || 'daily';
    const formula = document.getElementById('tdx-formula')?.value?.trim();
    const resultEl = document.getElementById('tdx-result');

    if (!formula) {
        if (resultEl) resultEl.textContent = '请输入公式';
        return;
    }

    if (resultEl) resultEl.innerHTML = '<i class="fas fa-circle-notch fa-spin text-violet-400 mr-1"></i> 计算中...';

    try {
        const resp = await fetch('/api/tdx/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ symbol: code, period, formula })
        });

        const data = await resp.json();
        if (resp.ok) {
            // Format result
            if (data.result) {
                resultEl.textContent = JSON.stringify(data.result, null, 2);
            } else if (data.signals) {
                resultEl.textContent = `信号: ${data.signals.length}个\n` + JSON.stringify(data.signals.slice(0, 10), null, 2);
            } else {
                resultEl.textContent = JSON.stringify(data, null, 2);
            }
        } else {
            resultEl.innerHTML = `<span class="text-rose-400">${data.error || '计算失败'}</span>`;
        }
    } catch (e) {
        console.error('TDX calculate failed:', e);
        resultEl.innerHTML = '<span class="text-rose-400">网络错误</span>';
    }
}

// ==================== MULTI-AGENT ANALYSIS ====================
export function openMultiAgentAnalysis() {
    const modal = document.getElementById('multi-agent-modal');
    if (modal) {
        modal.classList.remove('hidden');
        // Pre-fill with current stock if available
        updateMultiAgentStockName();
    }
}

function updateMultiAgentStockName() {
    const stockNameEl = document.getElementById('multi-agent-stock-name');
    if (stockNameEl && window.currentStockName) {
        stockNameEl.textContent = `${window.currentStockName} (${window.currentStockCode || ''})`;
    } else if (stockNameEl && window.currentStockCode) {
        stockNameEl.textContent = window.currentStockCode;
    }
}

export async function runMultiAgentAnalysis() {
    const code = window.currentStockCode || '600519';
    const name = window.currentStockName || code;

    const loadingEl = document.getElementById('multi-agent-loading');
    const scoreEl = document.getElementById('multi-agent-score');
    const signalEl = document.getElementById('multi-agent-signal');
    const stockNameEl = document.getElementById('multi-agent-stock-name');
    const actionEl = document.getElementById('multi-agent-action');

    // Show loading
    if (loadingEl) loadingEl.classList.remove('hidden');
    if (stockNameEl) stockNameEl.textContent = `${name} 分析中...`;
    if (scoreEl) scoreEl.textContent = '...';

    // Reset agent cards
    ['technical', 'market', 'fundamental', 'news', 'risk'].forEach(agent => {
        const scoreSpan = document.getElementById(`agent-${agent}-score`);
        const summaryP = document.getElementById(`agent-${agent}-summary`);
        if (scoreSpan) scoreSpan.textContent = '...';
        if (summaryP) summaryP.textContent = '分析中...';
    });

    try {
        const resp = await fetch(`/api/agents/analyze/${code}?stock_name=${encodeURIComponent(name)}`, {
            method: 'POST',
            credentials: 'include'
        });

        const data = await resp.json();

        // Hide loading
        if (loadingEl) loadingEl.classList.add('hidden');

        if (!resp.ok || !data.success) {
            if (stockNameEl) stockNameEl.textContent = `${name} - 分析失败`;
            if (scoreEl) scoreEl.textContent = '--';
            if (actionEl) actionEl.textContent = data.error || '分析失败，请重试';
            return;
        }

        // Update summary
        if (stockNameEl) stockNameEl.textContent = `${data.stock_name || name}`;
        if (scoreEl) scoreEl.textContent = Math.round(data.final_score || 0);

        // Signal with color
        const signalText = {
            'bullish': '看多 ↑',
            'bearish': '看空 ↓',
            'neutral': '中性 →'
        }[data.final_signal] || '中性';

        const signalColor = {
            'bullish': 'text-up',
            'bearish': 'text-down',
            'neutral': 'text-slate-400'
        }[data.final_signal] || '';

        if (signalEl) {
            signalEl.textContent = signalText;
            signalEl.className = `text-xs ${signalColor}`;
        }

        // Update action
        if (actionEl) {
            actionEl.textContent = data.action || '综合建议未知';
            actionEl.className = `text-sm font-bold ${data.final_signal === 'bullish' ? 'text-up' : (data.final_signal === 'bearish' ? 'text-down' : 'text-amber-400')}`;
        }

        // Update individual agent results
        const agentResults = data.agent_results || {};

        ['technical', 'market', 'fundamental', 'news', 'risk'].forEach(agent => {
            const result = agentResults[agent];
            const scoreSpan = document.getElementById(`agent-${agent}-score`);
            const summaryP = document.getElementById(`agent-${agent}-summary`);

            if (result) {
                const agentScore = Math.round(result.score || 0);
                if (scoreSpan) {
                    scoreSpan.textContent = `${agentScore}分`;
                    // Color based on score
                    if (agentScore >= 60) {
                        scoreSpan.className = 'ml-auto text-xs px-2 py-0.5 rounded bg-up-dim text-up';
                    } else if (agentScore <= 40) {
                        scoreSpan.className = 'ml-auto text-xs px-2 py-0.5 rounded bg-down-dim text-down';
                    } else {
                        scoreSpan.className = 'ml-auto text-xs px-2 py-0.5 rounded bg-slate-700';
                    }
                }
                if (summaryP) {
                    summaryP.textContent = result.summary || (result.success ? '分析完成' : result.error || '无数据');
                }
            } else {
                if (scoreSpan) scoreSpan.textContent = '--';
                if (summaryP) summaryP.textContent = '无数据';
            }
        });

    } catch (e) {
        console.error('Multi-agent analysis failed:', e);
        if (loadingEl) loadingEl.classList.add('hidden');
        if (stockNameEl) stockNameEl.textContent = `${name} - 网络错误`;
        if (scoreEl) scoreEl.textContent = '--';
        if (actionEl) actionEl.textContent = '网络错误，请检查连接后重试';
    }
}

// ==================== GLOBAL EXPORTS ====================
// Make functions available globally for onclick handlers
if (typeof window !== 'undefined') {
    window.openPortfolioModal = openPortfolioModal;
    window.submitOrder = submitOrder;
    window.openRiskDashboard = openRiskDashboard;
    window.openAutoTradePanel = openAutoTradePanel;
    window.executeAutoTrade = executeAutoTrade;
    window.openReplayChart = openReplayChart;
    window.loadReplayChart = loadReplayChart;
    window.openConditionOrders = openConditionOrders;
    window.createConditionOrder = createConditionOrder;
    window.deleteConditionOrder = deleteConditionOrder;
    window.openTdxFormula = openTdxFormula;
    window.calculateTdxFormula = calculateTdxFormula;
    window.openMultiAgentAnalysis = openMultiAgentAnalysis;
    window.runMultiAgentAnalysis = runMultiAgentAnalysis;
}
