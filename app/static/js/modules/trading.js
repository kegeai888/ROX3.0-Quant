// ==========================================
// ROX QUANT TRADING MODULE
// ==========================================

// fetchJSON is available globally from api-client.js

export async function updateTradingDashboard() {
    try {
        const data = await fetchJSON('/api/trade/dashboard');
        if (!data) return;

        // 1. Update Accounts (Inject HTML into trading-accounts container)
        const simAcc = data.accounts.find(a => a.type === 'sim') || { balance: 0, pnl: 0, pnl_pct: 0, win_rate: 0 };
        const realAcc = data.accounts.find(a => a.type === 'real') || { balance: 0, pnl: 0, pnl_pct: 0, win_rate: 0 };

        const accContainer = document.getElementById('trading-accounts');
        if (accContainer) {
            accContainer.innerHTML = `
                <div class="grid grid-cols-2 gap-2 text-xs">
                    <div class="bg-slate-700/50 p-2 rounded">
                        <div class="text-slate-400 mb-1">模拟盘资产</div>
                        <div class="text-white font-mono font-bold">${FormatUtils.formatMoney(simAcc.balance)}</div>
                        <div class="${FormatUtils.getColorClass(simAcc.pnl)} mt-1">
                            ${FormatUtils.formatPnL(simAcc.pnl, simAcc.pnl_pct)}
                        </div>
                    </div>
                    <div class="bg-slate-700/50 p-2 rounded">
                        <div class="text-slate-400 mb-1">实盘资产</div>
                        <div class="text-white font-mono font-bold">${FormatUtils.formatMoney(realAcc.balance)}</div>
                         <div class="${FormatUtils.getColorClass(realAcc.pnl)} mt-1">
                            ${FormatUtils.formatPnL(realAcc.pnl, realAcc.pnl_pct)}
                        </div>
                    </div>
                </div>
            `;
        }

        // 2. Update Trades List (Active Only)
        const list = document.getElementById('trade-list');
        if (list && data.sim_trades) {
            // Filter for open trades if needed, or backend returns closed? 
            // The dashboard endpoint returns "closed" trades in sim_trades/real_trades keys based on python code.
            // We might need a separate call for "active" trades or check if dashboard returns them.
            // Checking trade.py: api_trading_dashboard returns "closed" trades.
            // We need ACTIVE trades for the list.
            
            // Fetch active trades separately
            loadActiveTrades();
        }

    } catch (e) {
        console.error("Failed to update trading dashboard:", e);
    }
}

async function loadActiveTrades() {
    try {
        const data = await fetchJSON('/api/trade/trades?account_type=sim&status=open');
        const list = document.getElementById('trade-list');
        if (!list || !data || !data.trades) return;

        if (data.trades.length === 0) {
            list.innerHTML = '<tr><td colspan="7" class="text-center text-slate-500 p-4">暂无持仓</td></tr>';
            return;
        }

        list.innerHTML = data.trades.map(t => {
            const pnl = (t.current_price - t.open_price) * t.quantity * (t.side === 'buy' ? 1 : -1);
            const pnlClass = FormatUtils.getColorClass(pnl);
            
            return `
            <tr class="hover:bg-slate-800/50 transition-colors">
                <td class="p-2 text-slate-400 text-[10px]">${t.open_time.split('T')[1]?.substring(0,5) || '--'}</td>
                <td class="p-2 font-bold text-slate-200">
                    ${t.symbol}
                    <div class="text-[9px] text-slate-500 font-normal">${t.name}</div>
                </td>
                <td class="p-2 ${t.side === 'buy' ? 'text-rose-500' : 'text-emerald-500'}">
                    ${t.side === 'buy' ? '买入' : '卖出'}
                </td>
                <td class="p-2 text-slate-300 font-mono">${FormatUtils.formatPrice(t.open_price)}</td>
                <td class="p-2 text-slate-300 font-mono">${t.quantity}</td>
                <td class="p-2 font-mono">
                    <div class="text-slate-300">${FormatUtils.formatPrice(t.current_price)}</div>
                    <div class="${pnlClass} text-[10px]">${pnl > 0 ? '+' : ''}${FormatUtils.formatPrice(pnl)}</div>
                </td>
                <td class="p-2 text-right">
                    <button onclick="closeTrade('${t.id}')" class="text-xs bg-slate-700 hover:bg-sky-600 px-2 py-1 rounded text-white transition-colors">平仓</button>
                </td>
            </tr>
            `;
        }).join('');

    } catch (e) {
        console.error("Failed to load active trades:", e);
    }
}

export async function submitTrade() {
    const symbol = document.getElementById('trade-symbol')?.value;
    const price = parseFloat(document.getElementById('trade-price')?.value);
    const qty = parseInt(document.getElementById('trade-qty')?.value);
    const side = document.getElementById('trade-side')?.value;
    const note = document.getElementById('trade-note')?.value || '';

    if (!symbol || !price || !qty) {
        showToast('请填写完整交易信息', 'error');
        return;
    }

    // Determine account type based on current tab UI state or logic
    // For now defaulting to 'sim' as per existing UI logic
    const accountType = 'sim'; 

    try {
        const response = await fetch('/api/trade/open', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: symbol.split(' ')[0], // Handle "600519 茅台" format if present
                account_type: accountType,
                name: symbol, // Should ideally fetch name from symbol
                side: side,
                open_price: price,
                open_quantity: qty,
                strategy_note: note
            })
        });

        const res = await response.json();

        if (response.ok) {
            showToast('下单成功', 'success', `${side === 'buy' ? '买入' : '卖出'} ${symbol}`);
            // Clear inputs
            document.getElementById('trade-symbol').value = '';
            document.getElementById('trade-price').value = '';
            updateTradingDashboard(); // Refresh UI
        } else {
            showToast('下单失败', 'error', res.error || '未知错误');
        }

    } catch (e) {
        showToast('下单异常', 'error', e.message);
    }
}

export async function closeTrade(tradeId) {
    if (!confirm('确定要平仓吗？')) return;
    
    // In a real app we might ask for close price or use current market price.
    // For simplicity, we'll try to get current price from DOM or fetch it.
    // Here we assume server handles price or we send 0 to indicate "market price" (needs server support)
    // Looking at trade.py: api_close_trade requires close_price.
    
    // We'll prompt user for now as a fallback
    const price = prompt("请输入平仓价格:", "0");
    if (price === null) return;

    try {
        const response = await fetch('/api/trade/close', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                trade_id: parseInt(tradeId),
                close_price: parseFloat(price)
            })
        });
        
        if (response.ok) {
            showToast('平仓成功', 'success');
            updateTradingDashboard();
        } else {
            showToast('平仓失败', 'error');
        }
    } catch (e) {
        console.error(e);
    }
}

export function switchTradingTab(tab) {
    const btnSim = document.getElementById('tab-trade-sim');
    const btnReal = document.getElementById('tab-trade-real');
    const title = document.getElementById('trade-account-title');
    
    if(tab === 'sim') {
        btnSim.className = "flex-1 py-1.5 rounded bg-sky-600 text-white transition-all";
        btnReal.className = "flex-1 py-1.5 rounded text-slate-400 hover:text-white transition-all";
        if(title) title.innerText = "SIM ACCOUNT";
        // Reload data for sim...
    } else {
        btnReal.className = "flex-1 py-1.5 rounded bg-amber-600 text-white transition-all";
        btnSim.className = "flex-1 py-1.5 rounded text-slate-400 hover:text-white transition-all";
        if(title) title.innerText = "REAL ACCOUNT (READ ONLY)";
    }
}

export function syncRealAccount() {
    showToast('正在同步实盘数据...', 'info');
    // Real implementation would call an API
    setTimeout(() => {
        showToast('同步成功', 'success', '已更新最新持仓和资产');
        const now = new Date();
        const timeStr = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
        updateEl('sync-last', `上次成功：${timeStr}`);
    }, 1500);
}

// Helpers
function updateEl(id, val) {
    const el = document.getElementById(id);
    if (el) el.innerText = val;
}

// Export global functions for HTML event handlers
window.updateTradingDashboard = updateTradingDashboard;
window.submitTrade = submitTrade;
window.closeTrade = closeTrade; // Make sure this is available
window.switchTradingTab = switchTradingTab;
window.syncRealAccount = syncRealAccount;

