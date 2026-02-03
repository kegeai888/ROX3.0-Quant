class AShareMarket {
    constructor(brokerInstance, config = {}) {
        this.broker = brokerInstance;
        this.config = {
            refreshInterval: Number(config.refreshInterval) || 3000,
            flowInterval: Number(config.flowInterval) || 15000,
            maxRetry: Number(config.maxRetry) || 3,
            autoConnect: config.autoConnect !== false
        };
        this.interval = null;
        this.flowInterval = null;
        this.watchList = new Set(['sh000001', 'sz399001', 'sz399006']);
        this.nameCache = {};
    }
    start() {
        const wifiIcon = document.querySelector('.fa-wifi');
        if (wifiIcon) {
            wifiIcon.classList.remove('text-slate-500');
            wifiIcon.classList.add('text-rose-500');
            if (wifiIcon.nextElementSibling) wifiIcon.nextElementSibling.innerText = 'A股实盘 (Sina/EM)';
        }
        this._syncPositions();
        this._fetchData();
        this.interval = setInterval(() => this._fetchData(), this.config.refreshInterval);
        this._fetchFundFlow();
        this.flowInterval = setInterval(() => this._fetchFundFlow(), this.config.flowInterval);
        window.addEventListener('broker-update', () => this._syncPositions());
    }
    stop() {
        if (this.interval) { clearInterval(this.interval); this.interval = null; }
        if (this.flowInterval) { clearInterval(this.flowInterval); this.flowInterval = null; }
    }
    _formatSymbol(code) {
        const s = String(code).trim();
        if (s.startsWith('sh') || s.startsWith('sz')) return s;
        if (/^\d{6}$/.test(s)) return (s.startsWith('6') ? 'sh' : 'sz') + s;
        return s;
    }
    _syncPositions() {
        const positions = (this.broker && this.broker.account && this.broker.account.positions) || {};
        Object.keys(positions).forEach(symbol => {
            const fullCode = this._formatSymbol(symbol);
            if (fullCode.length > 2) this.watchList.add(fullCode);
        });
    }
    async _fetchData() {
        if (this.watchList.size === 0) return;
        const codes = Array.from(this.watchList).join(',');
        
        try {
            // Use backend proxy for Real-time Data (AllTick + Fallback)
            const resp = await fetch(`/api/market/quotes?codes=${encodeURIComponent(codes)}`);
            const data = await resp.json();
            this._processDataV2(data);
        } catch (e) {
            console.error("Market data fetch failed", e);
            // Fallback to legacy method if backend fails completely
            // this._fetchDataLegacy(codes); 
        }
    }

    _processDataV2(data) {
        if (!data) return;
        Object.keys(data).forEach(code => {
            const item = data[code];
            if (!item || item.price <= 0) return;

            const price = item.price;
            const pct = item.change_pct;
            
            if (item.name) {
                this.nameCache[code] = item.name;
                if (code.length > 2) this.nameCache[code.substring(2)] = item.name;
            }

            this._updateIndexUI_V2(code, price, pct);
            
            if (this.broker && typeof this.broker.updateMarketPrice === 'function') {
                this.broker.updateMarketPrice(code, price);
            }
        });
    }

    _updateIndexUI_V2(code, price, pct) {
        const map = { 'sh000001': 'idx-sh', 'sz399001': 'idx-sz', 'sz399006': 'idx-cy' };
        const idPrefix = map[code];
        if (!idPrefix) return;
        
        const elPrice = document.getElementById(`${idPrefix}-price`);
        const elChange = document.getElementById(`${idPrefix}-change`);
        if (!elPrice || !elChange) return;

        elPrice.innerText = FormatUtils.formatPrice(price);
        
        const pctStr = FormatUtils.formatPct(pct);
        const color = FormatUtils.getColorClass(pct);
        
        elChange.innerText = pctStr;
        elChange.className = `change text-sm font-medium mt-1 ${color}`;
        elPrice.className = `price text-3xl font-bold ${color}`;
    }

    _fetchDataLegacy(codes) {
        const script = document.createElement('script');
        script.src = `http://hq.sinajs.cn/list=${codes}`;
        script.charset = 'gb2312';
        script.onload = () => {
            this._processData();
            try { document.body.removeChild(script); } catch {}
        };
        script.onerror = () => {
            try { document.body.removeChild(script); } catch {}
        };
        document.body.appendChild(script);
    }

    _processData() {
        this.watchList.forEach(code => {
            const varName = 'hq_str_' + code;
            const dataStr = window[varName];
            if (!dataStr) return;
            const elements = dataStr.split(',');
            if (elements.length < 4) return;
            const name = elements[0];
            const preClose = parseFloat(elements[2]);
            const price = parseFloat(elements[3]);
            this.nameCache[code] = name;
            this.nameCache[code.substring(2)] = name;
            this._updateIndexUI(code, price, preClose);
            if (this.broker && typeof this.broker.updateMarketPrice === 'function') {
                this.broker.updateMarketPrice(code, price);
            }
        });
    }
    _updateIndexUI(code, price, preClose) {
        const map = { 'sh000001': 'idx-sh', 'sz399001': 'idx-sz', 'sz399006': 'idx-cy' };
        const idPrefix = map[code];
        if (!idPrefix) return;
        const elPrice = document.getElementById(`${idPrefix}-price`);
        const elChange = document.getElementById(`${idPrefix}-change`);
        if (!elPrice || !elChange || !isFinite(preClose) || !isFinite(price)) return;
        
        elPrice.innerText = FormatUtils.formatPrice(price);
        const changeRatio = ((price - preClose) / preClose) * 100;
        
        const pctStr = FormatUtils.formatPct(changeRatio);
        const color = FormatUtils.getColorClass(changeRatio);
        
        elChange.innerText = pctStr;
        elChange.className = `change text-sm font-medium mt-1 ${color}`;
        elPrice.className = `price text-3xl font-bold ${color}`;
    }
    _fetchFundFlow() {
        const callbackName = 'cb_fund_flow_' + Date.now();
        window[callbackName] = (res) => {
            this._processFundFlow(res);
            try {
                delete window[callbackName];
                const s = document.getElementById(callbackName);
                if (s) document.body.removeChild(s);
            } catch {}
        };
        const script = document.createElement('script');
        script.id = callbackName;
        script.src = `https://push2.eastmoney.com/api/qt/kamt/get?fields1=f1,f2,f3,f4&fields2=f51,f52,f53,f54&ut=b2884a393a59ad64002292a3e90d46a5&cb=${callbackName}`;
        script.onerror = () => {
            try {
                delete window[callbackName];
                const s = document.getElementById(callbackName);
                if (s) document.body.removeChild(s);
            } catch {}
        };
        document.body.appendChild(script);
    }
    _processFundFlow(res) {
        console.log('Fund Flow Data:', res);
        if (!res || !res.data) return;
        const d = res.data;
        const parseVal = (v) => (v === '-' || v === null || v === undefined) ? 0 : parseFloat(v);
        // EastMoney returns units in "Wan" (10,000). Convert to raw value.
        const northValRaw = (parseVal(d.hk2sh) + parseVal(d.hk2sz)) * 10000;
        const southValRaw = (parseVal(d.s2hk) + parseVal(d.z2hk)) * 10000;
        this._updateFlowUI('north', northValRaw);
        this._updateFlowUI('south', southValRaw);
    }
    _updateFlowUI(type, valueRaw) {
        const text = FormatUtils.formatBigNumber(valueRaw);
        const colorClass = FormatUtils.getColorClass(valueRaw);
        
        let cardId = `${type}-money`;
        if (type === 'south' && !document.getElementById('south-money')) {
            cardId = 'main-money';
        }
        const cardEl = document.getElementById(cardId);
        if (cardEl) {
            cardEl.innerText = text;
            cardEl.className = `text-lg font-bold ${colorClass}`;
        }
        const liveEl = document.getElementById(`${type}-live`);
        if (liveEl) {
            liveEl.innerText = text;
            liveEl.className = `text-xl font-bold ${colorClass}`;
            const alertEl = document.getElementById(`${type}-alert`);
            if (alertEl) {
                // Threshold: 20 Yi = 2,000,000,000
                alertEl.innerText = Math.abs(valueRaw) > 2000000000 ? '大幅流动 🔥' : '资金平稳';
            }
        }
        const timeEl = document.getElementById('hsgt-updated');
        if (timeEl) {
            const now = new Date();
            const timeStr = `${now.getHours()}:${String(now.getMinutes()).padStart(2, '0')}`;
            timeEl.innerText = timeStr;
        }
    }
}

export default AShareMarket;
