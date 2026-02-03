
// Professional Quantitative System Module

// Global state
let currentChart = null;
let currentStockCode = '';

export function initProfessionalSystem() {
    console.log("[ProfSystem] Initializing...");
    
    // Auto-fill stock code if available globally
    const globalCode = window.currentStockCode || ''; // Assuming exposed by main.js
    if(globalCode) {
        const input = document.getElementById('prof-signal-symbol');
        if(input && !input.value) input.value = globalCode;
    }

    // Default to signal tab
    switchProfessionalTab('signal');
}

export function switchProfessionalTab(tab) {
    // UI Toggles
    const signalBtn = document.getElementById('prof-tab-signal');
    const riskBtn = document.getElementById('prof-tab-risk');
    const signalView = document.getElementById('prof-view-signal');
    const riskView = document.getElementById('prof-view-risk');

    if(tab === 'signal') {
        signalBtn.classList.remove('text-[#a8b5c8]');
        signalBtn.classList.add('text-[#06b6d4]', 'border-b-2', 'border-[#06b6d4]');
        riskBtn.classList.remove('text-[#06b6d4]', 'border-b-2', 'border-[#06b6d4]');
        riskBtn.classList.add('text-[#a8b5c8]');
        
        signalView.classList.remove('hidden');
        riskView.classList.add('hidden');
    } else {
        riskBtn.classList.remove('text-[#a8b5c8]');
        riskBtn.classList.add('text-[#06b6d4]', 'border-b-2', 'border-[#06b6d4]');
        signalBtn.classList.remove('text-[#a8b5c8]');
        signalBtn.classList.add('text-[#a8b5c8]'); // Reset signal btn style
        // Actually the logic above is slightly repetitive, let's simplify next time.
        // For now, ensure clean class swap.
        signalBtn.classList.remove('text-[#06b6d4]', 'border-b-2', 'border-[#06b6d4]');
        
        signalView.classList.add('hidden');
        riskView.classList.remove('hidden');
    }
}

export async function fetchProfessionalSignal() {
    const symbol = document.getElementById('prof-signal-symbol').value;
    const template = document.getElementById('prof-signal-template').value;
    const period = document.getElementById('prof-signal-period').value;

    if(!symbol) {
        showToast('请输入股票代码', 'error');
        return;
    }

    // UI Loading State
    document.getElementById('prof-signal-loading').classList.remove('hidden');
    document.getElementById('prof-signal-content').classList.add('hidden');
    document.getElementById('prof-signal-empty').classList.add('hidden');
    document.getElementById('prof-signal-result-card').classList.add('hidden');

    try {
        // 1. Fetch OHLC data first (simulated via market API or specialized endpoint)
        // Since the backend professional endpoint expects OHLC data, we might need to fetch it first 
        // OR the backend might support fetching it internally.
        // Let's assume we post the request and let backend handle data fetching if we don't provide OHLC,
        // BUT looking at the guide, the request body HAS 'ohlc'.
        // So we need to fetch KLines first.
        
        // Fetch KLine data from our own API
        const klineRes = await fetch(`/api/market/kline?code=${symbol}&period=${period === 'daily' ? 'day' : period}`);
        const klineData = await klineRes.json();
        
        if(!klineData || klineData.length === 0) {
            throw new Error('无法获取K线数据');
        }

        // 2. Call Professional Analysis API
        const response = await fetch('/api/professional/signal-analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: symbol,
                ohlc: klineData, // Pass the array of {open, high, low, close, volume}
                period: 20 // Default period for now, or derive from UI
            })
        });

        const result = await response.json();
        
        if(result.error) throw new Error(result.error);

        renderSignalResults(result);

    } catch(e) {
        console.error("Signal Analysis Failed:", e);
        showToast('分析失败: ' + e.message, 'error');
        document.getElementById('prof-signal-loading').classList.add('hidden');
        document.getElementById('prof-signal-empty').classList.remove('hidden');
    }
}

function renderSignalResults(data) {
    // Hide loading
    document.getElementById('prof-signal-loading').classList.add('hidden');
    document.getElementById('prof-signal-content').classList.remove('hidden');
    document.getElementById('prof-signal-result-card').classList.remove('hidden');

    // 1. Render Summary Card
    const recEl = document.getElementById('prof-signal-recommendation');
    recEl.innerText = data.recommendation;
    recEl.className = `text-2xl font-black ${getRecColor(data.recommendation)}`;
    
    document.getElementById('prof-signal-confidence').innerText = data.confidence + '%';
    
    // Animate Score Bar
    const scoreBar = document.getElementById('prof-signal-score-bar');
    setTimeout(() => {
        scoreBar.style.width = data.signal_score + '%';
    }, 100);

    // 2. Render Signal List
    const container = document.getElementById('prof-signal-content');
    container.innerHTML = '';

    const signals = data.signals;
    
    // Helper to render individual signal card
    const createCard = (title, signalObj, icon) => {
        if(!signalObj) return '';
        const isBuy = signalObj.signal === 'BUY';
        const isSell = signalObj.signal === 'SELL';
        
        // Use consistent colors: Red for Buy (Up), Green for Sell (Down) in CN context
        // or just stick to Red/Green. 
        // Here we map BUY -> Red (Rose), SELL -> Green (Emerald)
        const statusColor = isBuy ? 'text-rose-500' : (isSell ? 'text-emerald-500' : 'text-slate-400');
        const borderColor = isBuy ? 'border-rose-500' : (isSell ? 'border-emerald-500' : 'border-slate-500');
        const bgGradient = isBuy ? 'from-rose-500/10 to-transparent' : (isSell ? 'from-emerald-500/10 to-transparent' : 'from-slate-500/10 to-transparent');
        
        return `
        <div class="glass p-4 rounded-lg bg-gradient-to-r ${bgGradient} border-l-4 ${borderColor}">
            <div class="flex justify-between items-start mb-2">
                <h4 class="font-bold text-white flex items-center">
                    <i class="fas ${icon} w-6 text-center mr-2 text-cyan-400"></i>
                    ${title}
                </h4>
                <span class="text-xs font-bold px-2 py-1 rounded bg-[#0a0f23] ${statusColor}">${signalObj.signal}</span>
            </div>
            <p class="text-xs text-[#a8b5c8] mb-2">${signalObj.description || '无详细描述'}</p>
            ${renderSignalValues(signalObj.values)}
        </div>
        `;
    };

    container.innerHTML += createCard('亢龙有悔', signals.kang_long_you_hui, 'fa-dragon');
    container.innerHTML += createCard('游资暗盘', signals.hot_money_dark_pool, 'fa-user-secret');
    container.innerHTML += createCard('暗盘资金', signals.dark_pool_fund, 'fa-money-bill-wave');
    container.innerHTML += createCard('精准买卖点', signals.precise_trading, 'fa-crosshairs');
    container.innerHTML += createCard('三色共振', signals.three_color_resonance, 'fa-traffic-light');
    container.innerHTML += createCard('Zigzag高低点', signals.zigzag, 'fa-wave-square');
    container.innerHTML += createCard('综合技术指标', signals.technical_indicators, 'fa-chart-bar');
}

function renderSignalValues(values) {
    if(!values) return '';
    let html = '<div class="grid grid-cols-2 gap-2 text-[10px] text-[#6b7a96]">';
    for(const [k, v] of Object.entries(values)) {
        let valStr = v;
        if (typeof v === 'number') {
             // Use global FormatUtils if available
             if (window.FormatUtils) {
                 if (Math.abs(v) > 10000) {
                     valStr = window.FormatUtils.formatBigNumber(v);
                 } else {
                     valStr = window.FormatUtils.formatPrice(v);
                 }
             } else {
                 valStr = v.toFixed(2);
             }
        }
        html += `<div><span class="mr-1">${k}:</span><span class="text-[#c5ccd8]">${valStr}</span></div>`;
    }
    html += '</div>';
    return html;
}

function getRecColor(rec) {
    if(rec === 'BUY' || rec === 'STRONG BUY') return 'text-rose-500';
    if(rec === 'SELL' || rec === 'STRONG SELL') return 'text-emerald-500';
    return 'text-slate-400';
}

export async function calculateRisk() {
    const entry = parseFloat(document.getElementById('risk-entry-price').value);
    const current = parseFloat(document.getElementById('risk-current-price').value);
    const size = parseFloat(document.getElementById('risk-position-size').value);
    const capital = parseFloat(document.getElementById('risk-capital').value);
    const atr = parseFloat(document.getElementById('risk-atr').value) || 0;

    if(!entry || !current || !size || !capital) {
        showToast('请填写所有必要参数', 'error');
        return;
    }

    try {
        const response = await fetch('/api/professional/risk-analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                entry_price: entry,
                current_price: current,
                position_size: size,
                capital: capital,
                atr: atr
            })
        });

        const result = await response.json();
        
        // Render Risk Results
        updateEl('risk-stop-loss', window.FormatUtils ? window.FormatUtils.formatPrice(result.stop_loss) : result.stop_loss.toFixed(2));
        updateEl('risk-take-profit', window.FormatUtils ? window.FormatUtils.formatPrice(result.take_profit) : result.take_profit.toFixed(2));
        updateEl('risk-kelly', result.kelly_optimal.toFixed(2));
        // Risk Reward Ratio = (TakeProfit - Entry) / (Entry - StopLoss)
        const rr = Math.abs((result.take_profit - entry) / (entry - result.stop_loss));
        updateEl('risk-rr-ratio', '1:' + rr.toFixed(2));

        if(result.risk_metrics) {
            updateEl('risk-var', (result.risk_metrics.var_95 * 100).toFixed(2) + '%');
            updateEl('risk-cvar', (result.risk_metrics.cvar_95 * 100).toFixed(2) + '%');
            updateEl('risk-sortino', result.risk_metrics.sortino_ratio.toFixed(2));
            updateEl('risk-calmar', result.risk_metrics.calmar_ratio.toFixed(2));
        }

        updateEl('risk-drawdown-current', result.current_drawdown.toFixed(2) + '%');

        // Draw Chart (Placeholder for now, or simple line chart)
        renderRiskChart();

        showToast('风险计算完成', 'success');

    } catch(e) {
        console.error(e);
        showToast('计算失败', 'error');
    }
}

function updateEl(id, val) {
    const el = document.getElementById(id);
    if(el) el.innerText = val;
}

function renderRiskChart() {
    // Basic ECharts for Drawdown simulation
    const dom = document.getElementById('risk-drawdown-chart');
    if(!dom) return;
    
    // Clean up
    const existing = echarts.getInstanceByDom(dom);
    if(existing) existing.dispose();

    const chart = echarts.init(dom);
    
    // Simulate a random drawdown curve for demo (since we don't have real historical pnl here)
    const data = [];
    let val = 0;
    for(let i=0; i<100; i++) {
        val += (Math.random() - 0.5);
        if(val > 0) val = 0; // Drawdown is usually negative
        data.push(val);
    }

    chart.setOption({
        grid: { top: 10, bottom: 20, left: 30, right: 10 },
        xAxis: { type: 'category', show: false },
        yAxis: { type: 'value', splitLine: { lineStyle: { color: '#2a3f5f' } } },
        series: [{
            type: 'line',
            data: data,
            areaStyle: { color: 'rgba(239, 68, 68, 0.2)' },
            lineStyle: { color: '#ef4444' },
            showSymbol: false
        }]
    });
    
    window.addEventListener('resize', () => chart.resize());
}
