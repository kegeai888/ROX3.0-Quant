// Local state for quick lookup
let _watchlistSet = new Set();
// Callback for state changes (to update other UI like the header button)
let _onWatchlistChange = null;

export function setWatchlistChangeCallback(cb) {
    _onWatchlistChange = cb;
}

export function isStockInWatchlist(code) {
    return _watchlistSet.has(code);
}

export async function toggleWatchlist(code, name) {
    if (!code) return false;

    if (_watchlistSet.has(code)) {
        // Remove
        await removeStockFromWatchlist(code, true); // true = skip confirm if called from toggle
        return false;
    } else {
        // Add
        await addToWatchlistInternal(code, name || code);
        return true;
    }
}

async function addToWatchlistInternal(code, name) {
    try {
        const response = await fetch('/api/market/watchlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ stock_name: name, stock_code: code, sector: '' }),
            credentials: 'include'
        });

        if (!response.ok) {
            if (response.status === 401) {
                if (typeof showAuthModal === 'function') showAuthModal();
                else if (typeof window.showAuthModal === 'function') window.showAuthModal();
                return;
            }
            throw new Error('添加失败');
        }

        if (typeof showToast === 'function') showToast('成功', 'success', `已添加 ${name} 到自选股`);
        else if (typeof window.showToast === 'function') window.showToast('成功', 'success', `已添加 ${name} 到自选股`);

        await loadWatchlist(); // Refresh and update state
    } catch (error) {
        console.error('Error adding to watchlist:', error);
        const msg = error.message || '添加失败';
        if (typeof showToast === 'function') showToast('错误', 'error', msg);
    }
}

export async function loadWatchlist() {
    try {
        const response = await fetch('/api/market/watchlist', { credentials: 'include' });
        const container = document.getElementById('watchlist-container');

        // Always try to update local state even if container is hidden/missing
        if (response.ok) {
            const data = await response.json();
            const items = data.items || [];

            // Update local Set
            _watchlistSet.clear();
            items.forEach(item => _watchlistSet.add(item.stock_code));

            // Notify listener (e.g. main.js to update the star icon)
            if (_onWatchlistChange) _onWatchlistChange();

            // If container exists, render list
            if (container) {
                renderWatchlistUI(container, items);
            }
        } else {
            if (response.status === 401 && container) {
                container.innerHTML = '<p class="text-center text-slate-500 text-sm p-4">请先登录</p>';
            }
        }
    } catch (error) {
        console.error('Error loading watchlist:', error);
    }
}

async function renderWatchlistUI(container, items) {
    container.innerHTML = '';
    if (items.length > 0) {
        // 1. Collect codes to fetch real-time quotes
        const codes = items.map(item => item.stock_code).join(',');
        let quotes = {};

        try {
            const qRes = await fetch(`/api/market/quotes?codes=${encodeURIComponent(codes)}`);
            if (qRes.ok) {
                quotes = await qRes.json();
            }
        } catch (e) {
            console.warn("Failed to fetch watchlist quotes", e);
        }

        // 2. Render List
        items.forEach(item => {
            const quote = quotes[item.stock_code];
            let priceHtml = '';

            if (quote && window.FormatUtils) {
                const priceStr = FormatUtils.formatPrice(quote.price);
                const pctStr = FormatUtils.formatPct(quote.change_pct);
                const colorClass = FormatUtils.getColorClass(quote.change_pct);

                priceHtml = `
                    <div class="text-right">
                        <div class="font-mono font-bold ${colorClass}">${priceStr}</div>
                        <div class="text-xs ${colorClass}">${pctStr}</div>
                    </div>
                `;
            } else {
                priceHtml = `<div class="text-xs text-slate-500">--</div>`;
            }

            const div = document.createElement('div');
            div.className = 'p-2 rounded bg-slate-800/50 hover:bg-slate-700/50 cursor-pointer flex justify-between items-center border-b border-slate-700/30 last:border-0 transition-colors';
            div.innerHTML = `
                <div class="flex-1">
                    <span class="font-bold text-slate-200 block">${item.stock_name}</span>
                    <span class="text-xs text-slate-400 font-mono">${item.stock_code}</span>
                </div>
                ${priceHtml}
                <button onclick="removeStockFromWatchlist('${item.stock_code}')" class="ml-3 text-slate-600 hover:text-rose-500 text-xs p-2 transition-colors"><i class="fas fa-trash"></i></button>
            `;
            div.onclick = (e) => {
                // Prevent click when clicking delete button
                if (e.target.closest('button')) return;
                selectStock(item.stock_code, item.stock_name);
            };
            container.appendChild(div);
        });
    } else {
        container.innerHTML = '<p class="text-center text-slate-500 text-sm p-4">自选股列表为空</p>';
    }
}

export async function manualAddToWatchlist() {
    const nameInput = document.getElementById('wl_stock_name');
    const codeInput = document.getElementById('wl_stock_code');
    const stockName = nameInput.value.trim();
    const stockCode = codeInput.value.trim();

    if (!stockName || !stockCode) {
        if (typeof showToast === 'function') showToast('错误', 'error', '请输入股票名称和代码');
        return;
    }

    await addToWatchlistInternal(stockCode, stockName);

    nameInput.value = '';
    codeInput.value = '';
}

export async function removeStockFromWatchlist(stockCode, skipConfirm = false) {
    if (!skipConfirm && !confirm(`确定要从自选股中移除 ${stockCode} 吗？`)) return;

    try {
        const response = await fetch(`/api/market/watchlist?stock_code=${stockCode}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (!response.ok) {
            if (response.status === 401) {
                if (typeof showAuthModal === 'function') showAuthModal();
                else if (typeof window.showAuthModal === 'function') window.showAuthModal();
                return;
            }
            throw new Error('移除失败');
        }

        if (typeof showToast === 'function') showToast('成功', 'success', `已从自选股中移除 ${stockCode}`);
        else if (typeof window.showToast === 'function') window.showToast('成功', 'success', `已从自选股中移除 ${stockCode}`);

        await loadWatchlist(); // Refresh the list
    } catch (error) {
        console.error('Error removing from watchlist:', error);
        if (typeof showToast === 'function') showToast('移除失败', 'error', error.message);
    }
}

