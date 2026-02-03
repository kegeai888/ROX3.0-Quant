/**
 * Enhanced WebSocket Client for Rox Quant
 * Handles real-time data streaming, automatic reconnection, and subscription management
 */

class RoxWSClient {
    constructor() {
        this.ws = null;
        this.url = ((window.location.protocol === 'https:') ? 'wss://' : 'ws://') + window.location.host + '/ws/enhanced';
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 2000;
        this.subscriptions = new Set();
        this.messageHandlers = new Map();
        this.isConnected = false;
        
        // Default handlers
        this.registerHandler('market_indices', this.handleMarketIndices.bind(this));
        this.registerHandler('stock_updates', this.handleStockUpdates.bind(this));
        this.registerHandler('sector_rotation', this.handleSectorRotation.bind(this));
        this.registerHandler('trading_alerts', this.handleTradingAlerts.bind(this));
        this.registerHandler('connection', this.handleConnection.bind(this));
        this.registerHandler('market_data', this.handleMarketData.bind(this));
        this.registerHandler('hsgt_data', this.handleHSGTData.bind(this));
        this.registerHandler('sentiment_data', this.handleSentimentData.bind(this));
        this.registerHandler('prediction_data', this.handlePredictionData.bind(this));
    }

    /**
     * Initialize connection
     */
    connect() {
        if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
            return;
        }

        console.log(`Connecting to WS: ${this.url}`);
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            console.log('WS Connected');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.updateConnectionStatus(true);
            
            // Resubscribe to channels
            if (this.subscriptions.size > 0) {
                this.subscribe(Array.from(this.subscriptions));
            }
        };

        this.ws.onclose = (event) => {
            console.log(`WS Closed: ${event.code} ${event.reason}`);
            this.isConnected = false;
            this.updateConnectionStatus(false);
            this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WS Error:', error);
            this.ws.close();
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.dispatchMessage(message);
            } catch (e) {
                console.error('Failed to parse WS message:', e);
            }
        };
    }

    /**
     * Attempt to reconnect with exponential backoff
     */
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnect attempts reached');
            return;
        }

        const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts);
        this.reconnectAttempts++;
        
        console.log(`Reconnecting in ${delay}ms (Attempt ${this.reconnectAttempts})`);
        setTimeout(() => this.connect(), delay);
    }

    /**
     * Subscribe to specific data channels
     * @param {string|string[]} channels 
     */
    subscribe(channels) {
        if (!Array.isArray(channels)) {
            channels = [channels];
        }

        channels.forEach(ch => this.subscriptions.add(ch));

        if (this.isConnected) {
            this.send({
                type: 'subscribe',
                channels: channels
            });
        }
    }

    /**
     * Unsubscribe from channels
     * @param {string|string[]} channels 
     */
    unsubscribe(channels) {
        if (!Array.isArray(channels)) {
            channels = [channels];
        }

        channels.forEach(ch => this.subscriptions.delete(ch));

        if (this.isConnected) {
            this.send({
                type: 'unsubscribe',
                channels: channels
            });
        }
    }

    /**
     * Send message to server
     * @param {object} data 
     */
    send(data) {
        if (this.isConnected) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.warn('Cannot send message: WS not connected');
        }
    }

    /**
     * Register a message handler for a specific type
     * @param {string} type 
     * @param {function} handler 
     */
    registerHandler(type, handler) {
        this.messageHandlers.set(type, handler);
    }

    /**
     * Dispatch incoming message to registered handlers
     * @param {object} message 
     */
    dispatchMessage(message) {
        const handler = this.messageHandlers.get(message.type);
        if (handler) {
            handler(message);
        } else {
            // console.debug('Unhandled message type:', message.type);
        }
    }

    /**
     * Update UI connection status
     */
    updateConnectionStatus(connected) {
        const statusEl = document.querySelector('.fa-wifi');
        const textEl = document.getElementById('ws-status-text');
        
        if (statusEl && textEl) {
            if (connected) {
                statusEl.classList.remove('text-slate-500', 'text-red-500');
                statusEl.classList.add('text-emerald-500');
                textEl.textContent = '在线';
            } else {
                statusEl.classList.remove('text-emerald-500');
                statusEl.classList.add('text-red-500');
                textEl.textContent = '离线';
            }
        }
    }

    // --- Message Handlers ---

    handleConnection(msg) {
        console.log('WS Handshake:', msg.status);
    }

    handleMarketIndices(msg) {
        const data = msg.data;
        
        // Update indices UI
        this.updateIndex('sh', data.sh000001);
        this.updateIndex('sz', data.sz399001);
        this.updateIndex('cy', data.sz399006);
    }

    updateIndex(prefix, data) {
        if (!data) return;
        
        const priceEl = document.getElementById(`idx-${prefix}-price`);
        const changeEl = document.getElementById(`idx-${prefix}-change`);
        
        if (priceEl && changeEl) {
            priceEl.textContent = FormatUtils.formatPrice(data.price);
            
            const changeVal = data.change;
            const pctVal = data.change_percent;
            const colorClass = FormatUtils.getColorClass(changeVal);
            
            changeEl.textContent = `${changeVal > 0 ? '+' : ''}${FormatUtils.formatPrice(changeVal)} (${FormatUtils.formatPct(pctVal)})`;
            
            // Remove old color classes
            changeEl.classList.remove('text-emerald-400', 'text-rose-400', 'text-slate-400', 'text-rose-500', 'text-emerald-500', 'text-slate-200');
            changeEl.classList.add(colorClass);
            
            // Price flash effect
            priceEl.classList.add('text-white');
            setTimeout(() => priceEl.classList.remove('text-white'), 300);
        }
    }

    handleStockUpdates(msg) {
        // Handle individual stock updates (e.g. for watchlist)
        // console.log('Stock updates:', msg.data);
    }

    handleSectorRotation(msg) {
        // Handle sector data
        // console.log('Sector rotation:', msg.data);
    }

    handleTradingAlerts(msg) {
        if (msg.alerts && msg.alerts.length > 0) {
            msg.alerts.forEach(alert => {
                this.showToast(alert.title, alert.message, alert.severity);
            });
        }
    }

    handleMarketData(msg) {
        // Handle comprehensive market data updates
        if (msg.data) {
            this.updateMarketStats(msg.data);
            this.updateRankings(msg.data);
        }
    }

    handleHSGTData(msg) {
        // Handle HSGT (Stock Connect) data
        if (msg.data) {
            this.updateHSGTCharts(msg.data);
        }
    }

    handleSentimentData(msg) {
        // Handle sentiment and retail distribution data
        if (msg.data) {
            if (msg.data.retail_dist) {
                this.updateRetailRadar(msg.data.retail_dist);
            }
            if (typeof msg.data.bull_bear !== 'undefined') {
                this.updateBullBearGauge(msg.data.bull_bear);
            }
        }
    }

    handlePredictionData(msg) {
        // Handle prediction and analysis data
        if (msg.data) {
            this.updatePredictionDisplay(msg.data);
        }
    }

    // --- UI Update Methods ---

    updateMarketStats(data) {
        if (data.north_money) {
            this.updateElement('north-money', data.north_money);
        }
        if (data.main_money) {
            this.updateElement('main-money', data.main_money);
        }
    }

    updateRankings(data) {
        if (data.sectors && data.sectors.length) {
            const container = document.getElementById('rank-sector');
            if (container) {
                container.innerHTML = data.sectors.map((s, i) => `
                    <div class="flex justify-between text-xs border-b border-slate-800 pb-2">
                        <span class="w-4">${i+1}</span>
                        <span class="flex-1">${s.name}</span>
                        <span class="${s.pct >= 0 ? 'text-red-400' : 'text-emerald-400'}">${s.pct}%</span>
                    </div>
                `).join('');
            }
        }
        
        if (data.stocks && data.stocks.length) {
            const container = document.getElementById('rank-stock');
            if (container) {
                container.innerHTML = data.stocks.map((s, i) => `
                    <div class="flex justify-between text-xs border-b border-slate-800 pb-2 cursor-pointer hover:bg-slate-800" 
                         onclick="loadStock('${s.name}')">
                        <span class="w-4">${i+1}</span>
                        <span class="flex-1">${s.name}</span>
                        <span class="${s.pct >= 0 ? 'text-red-400' : 'text-emerald-400'}">${s.pct}%</span>
                    </div>
                `).join('');
            }
        }
    }

    updateHSGTCharts(data) {
        if (data.north && data.north.length) {
            this.renderHSGTChart('hsgt-chart-north', data.north, '北向净买额', '#ef4444');
        }
        if (data.south && data.south.length) {
            this.renderHSGTChart('hsgt-chart-south', data.south, '南向净买额', '#22c55e');
        }
        
        // Update live text values
        if (data.north && data.north.length) {
            const last = data.north[data.north.length-1].value;
            // Assuming last is in Wan, convert to raw for formatBigNumber
            const rawVal = last * 10000; 
            this.updateElement('north-live', FormatUtils.formatBigNumber(rawVal), 
                `text-xl font-bold ${FormatUtils.getColorClass(last)}`);
        }
        if (data.south && data.south.length) {
            const last = data.south[data.south.length-1].value;
            const rawVal = last * 10000;
            this.updateElement('south-live', FormatUtils.formatBigNumber(rawVal), 
                `text-xl font-bold ${FormatUtils.getColorClass(last)}`);
        }
    }

    renderHSGTChart(domId, seriesData, name, color) {
        const dom = document.getElementById(domId);
        if (!dom) return;
        
        const myChart = echarts.getInstanceByDom(dom) || echarts.init(dom);
        const xData = seriesData.map(i => i.time.split(' ')[1] || i.time);
        const yData = seriesData.map(i => i.value);
        
        myChart.setOption({
            backgroundColor: 'transparent',
            tooltip: { trigger: 'axis' },
            grid: { top: 10, bottom: 25, left: 10, right: 10, containLabel: true },
            xAxis: { type: 'category', data: xData },
            yAxis: { type: 'value', splitLine: { show: false } },
            series: [{ 
                name: name, type: 'line', data: yData, showSymbol: false,
                itemStyle: { color: color },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        {offset: 0, color: color + '80'},
                        {offset: 1, color: color + '03'}
                    ])
                }
            }]
        });
        myChart.resize();
    }

    updateRetailRadar(distData) {
        if (typeof window.renderRetailRadar === 'function') {
            window.renderRetailRadar(distData);
        }
    }

    updateBullBearGauge(bb) {
        if (typeof window.renderBullBearGauge === 'function') {
            window.renderBullBearGauge(bb);
        }
    }

    updatePredictionDisplay(data) {
        if (data.confidence) {
            this.updateElement('pred-confidence', data.confidence + '%');
        }
        if (data.logic) {
            this.updateElement('pred-logic', data.logic);
        }
        if (data.support) {
            this.updateElement('pred-support', data.support);
        }
        if (data.pressure) {
            this.updateElement('pred-pressure', data.pressure);
        }
        
        // Update prediction chart if available
        if (data.history && data.prediction && document.getElementById('pred-chart')) {
            if (typeof window.loadPrediction === 'function') {
                // Reuse existing prediction chart logic
                window.loadPrediction();
            }
        }
    }

    updateElement(id, value, className) {
        const el = document.getElementById(id);
        if (el) {
            if (value !== undefined) el.textContent = value;
            if (className) el.className = className;
        }
    }

    showToast(title, message, severity = 'info') {
        // Use existing toast function if available, or create minimal one
        if (typeof window.showToast === 'function') {
            window.showToast(title, severity === 'high' ? 'error' : 'success', message);
        } else {
            console.log(`[${severity.toUpperCase()}] ${title}: ${message}`);
        }
    }
}

// Initialize and export
window.roxWS = new RoxWSClient();

// Auto-connect when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit for other scripts to load
    setTimeout(() => {
        window.roxWS.connect();
        
        // Subscribe to default channels
        window.roxWS.subscribe(['market_data', 'alerts']);
    }, 1000);
});