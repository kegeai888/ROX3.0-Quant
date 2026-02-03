/**
 * SimBroker - 本地模拟交易核心引擎
 * 特性：
 * 1. 自动持久化 (LocalStorage)，刷新网页资金不丢
 * 2. 模拟真实手续费 (默认万分之2.5)
 * 3. 严格的资金风控 (余额不足无法开仓)
 */
class SimBroker {
    constructor(initialCapital = 1000000) {
        this.storageKey = 'rox_sim_account_v1';
        this.account = this._load() || this._init(initialCapital);
        this.commissionRate = 0.00025;
        this.stampDutyRate = 0.001;   // 卖出印花税 0.1%
        this.transferFeeRate = 0.00002; // 过户费 0.002%
    }

    _init(capital) {
        return {
            cash: capital,           // 可用资金
            totalAsset: capital,     // 总资产
            initCapital: capital,    // 初始本金 (用于算总盈亏)
            positions: {},           // 持仓字典: { "600519": { qty: 100, cost: 1800.0, price: 1800.0 } }
            history: [],             // 交易流水
            ts: Date.now(),          // 账户时间戳
            currency: 'CNY'          // 币种
        };
    }

    _load() {
        try {
            const data = localStorage.getItem(this.storageKey);
            if (!data) return null;
            const obj = JSON.parse(data);
            if (!obj || !obj.ts) return obj;
            const sevenDays = 7 * 24 * 3600 * 1000;
            if (Date.now() - obj.ts > sevenDays) {
                return null;
            }
            return obj;
        } catch {
            return null;
        }
    }

    _save() {
        // 每次变动都保存到浏览器
        this.account.ts = Date.now();
        localStorage.setItem(this.storageKey, JSON.stringify(this.account));
        // 触发全局事件通知 UI 更新
        window.dispatchEvent(new Event('broker-update'));
    }

    // 重置账户
    reset(capital = 1000000, currency = 'CNY') {
        this.account = this._init(capital);
        this.account.currency = currency;
        this._save();
        return this.account;
    }

    /**
     * 执行下单
     * @param {string} symbol 代码
     * @param {string} side 'buy' | 'sell'
     * @param {number} price 价格
     * @param {number} qty 数量
     */
    executeOrder(symbol, side, price, qty) {
        const amount = price * qty;
        const commission = Math.max(5, amount * this.commissionRate);
        const transferFee = amount * this.transferFeeRate;
        const stampDuty = side === 'sell' ? amount * this.stampDutyRate : 0;
        const totalFee = commission + transferFee + stampDuty;

        if (side === 'buy') {
            // 买入检查：资金是否足够
            const totalCost = amount + totalFee;
            if (this.account.cash < totalCost) {
                return { success: false, msg: `资金不足！需 ${FormatUtils.formatBigNumber(totalCost)}，持有 ${FormatUtils.formatBigNumber(this.account.cash)}` };
            }

            // 扣款
            this.account.cash -= totalCost;

            // 更新/新建持仓
            if (!this.account.positions[symbol]) {
                this.account.positions[symbol] = { qty: 0, cost: 0, lastPrice: price, name: symbol };
            }
            const pos = this.account.positions[symbol];
            
            // 计算移动平均成本
            const oldAmt = pos.qty * pos.cost;
            const newAmt = oldAmt + amount + totalFee; // 买入包含手续费与过户费
            pos.qty += qty;
            pos.cost = newAmt / pos.qty;
            pos.lastPrice = price;

        } else if (side === 'sell') {
            // 卖出检查：持仓是否足够
            const pos = this.account.positions[symbol];
            if (!pos || pos.qty < qty) {
                return { success: false, msg: `持仓不足！可用 ${pos ? pos.qty : 0}` };
            }

            // 卖出逻辑
            const revenue = amount - totalFee;
            this.account.cash += revenue;
            
            // 更新持仓
            pos.qty -= qty;
            pos.lastPrice = price;
            
            // 如果卖空了，删除持仓记录
            if (pos.qty === 0) {
                delete this.account.positions[symbol];
            }
        }

        // 记录流水
        this.account.history.unshift({
            time: new Date().toLocaleString(),
            symbol: symbol,
            side: side === 'buy' ? '买入' : '卖出',
            price: price,
            qty: qty,
            fee: totalFee.toFixed(2)
        });

        this._updateTotalAssets(); // 重新计算总资产
        this._save();
        return { success: true, msg: `${side === 'buy' ? '买入' : '卖出'} ${symbol} ${qty}股 成功` };
    }

    // 根据最新市价更新总资产 (Mark-to-Market)
    // 在行情推送时调用此方法
    updateMarketPrice(symbol, currentPrice) {
        if (this.account.positions[symbol]) {
            this.account.positions[symbol].lastPrice = currentPrice;
            this._updateTotalAssets();
            this._save();
        }
    }

    _updateTotalAssets() {
        let marketValue = 0;
        for (let key in this.account.positions) {
            const p = this.account.positions[key];
            marketValue += p.qty * p.lastPrice;
        }
        this.account.totalAsset = this.account.cash + marketValue;
    }

    // 获取当前状态供 UI 渲染
    getDashboardData() {
        const init = this.account.initCapital;
        const current = this.account.totalAsset;
        const pnl = current - init;
        const pnlRatio = (pnl / init) * 100;

        return {
            cash: FormatUtils.formatBigNumber(this.account.cash),
            asset: FormatUtils.formatBigNumber(this.account.totalAsset),
            pnl: FormatUtils.formatBigNumber(pnl),
            pnlRatio: FormatUtils.formatPct(pnlRatio),
            isProfit: pnl >= 0,
            positions: this.account.positions,
            history: this.account.history,
            currency: this.account.currency
        };
    }

    // 删除某个持仓（右键菜单）
    deletePosition(symbol) {
        if (this.account.positions[symbol]) {
            delete this.account.positions[symbol];
            this._updateTotalAssets();
            this._save();
        }
    }
    // 批量清除零持仓
    purgeZeroPositions() {
        Object.keys(this.account.positions).forEach(k => {
            const p = this.account.positions[k];
            if (!p || p.qty === 0) delete this.account.positions[k];
        });
        this._updateTotalAssets();
        this._save();
    }
}

export default SimBroker;
