(function() {
    // 1. Initialize LiteGraph
    var graph = new LGraph();
    var canvas = new LGraphCanvas("#editor-canvas", graph);
    
    // Resize canvas
    function resize() {
        var container = document.getElementById("canvas-container");
        canvas.resize(container.offsetWidth, container.offsetHeight);
    }
    window.addEventListener("resize", resize);
    setTimeout(resize, 100);

    // 2. Define Custom Nodes
    
    // --- Market Data Node ---
    function MarketDataNode() {
        this.addOutput("Close", "number");
        this.addOutput("Volume", "number");
        this.addProperty("symbol", "000001");
        this.addProperty("period", "daily");
        this.title = "行情数据";
        this.color = "#0f5e9c";
        this.widgets_up = true;
    }
    MarketDataNode.title = "行情数据";
    MarketDataNode.desc = "获取股票历史数据";
    // Add custom delete action to context menu if needed, but LiteGraph default is usually fine.
    LiteGraph.registerNodeType("Market/Data", MarketDataNode);

    // --- SMA Indicator ---
    function SMANode() {
        this.addInput("Data", "number");
        this.addOutput("SMA", "number");
        this.addProperty("period", 10);
        this.title = "SMA 均线";
    }
    SMANode.title = "SMA";
    SMANode.desc = "简单移动平均";
    LiteGraph.registerNodeType("Indicators/SMA", SMANode);

    // --- CrossOver Logic ---
    function CrossOverNode() {
        this.addInput("A (Fast)", "number");
        this.addInput("B (Slow)", "number");
        this.addOutput("Signal", "boolean");
        this.title = "金叉/死叉";
    }
    CrossOverNode.title = "CrossOver";
    LiteGraph.registerNodeType("Logic/CrossOver", CrossOverNode);

    // --- Trade Signal ---
    function TradeSignalNode() {
        this.addInput("Buy", "boolean");
        this.addInput("Sell", "boolean");
        this.title = "交易信号";
        this.bgcolor = "#2d4a2d";
    }
    TradeSignalNode.title = "Trade Signal";
    LiteGraph.registerNodeType("Trade/Signal", TradeSignalNode);

    // 3. Drag & Drop Logic
    var items = document.querySelectorAll(".node-item");
    items.forEach(function(item) {
        item.addEventListener("dragstart", function(e) {
            e.dataTransfer.setData("type", this.dataset.type);
        });
    });

    canvas.canvas.addEventListener("drop", function(e) {
        e.preventDefault();
        var type = e.dataTransfer.getData("type");
        if(type) {
            var node = LiteGraph.createNode(type);
            if(node) {
                node.pos = [e.offsetX, e.offsetY];
                graph.add(node);
            }
        }
    });
    canvas.canvas.addEventListener("dragover", function(e) { e.preventDefault(); });

    // 4. Run Backtest Logic
    document.getElementById("btn-run").addEventListener("click", function() {
        var mode = document.querySelector(".mode-btn.active").dataset.mode;
        
        // Show Modal
        var modal = document.getElementById("result-modal");
        var content = document.getElementById("result-content");
        modal.classList.remove("hidden");
        content.innerHTML = '<div class="flex flex-col items-center justify-center h-64"><div class="animate-spin rounded-full h-12 w-12 border-b-2 border-sky-500 mb-4"></div><p class="text-slate-400">正在编译策略并执行回测...</p></div>';

        setTimeout(function() {
            var strategyName = "Custom Strategy";
            var winRate = "55%";
            var returns = "+24.5%";
            
            if(mode === 'wizard') {
                var activeTemplate = document.querySelector('.wizard-template-btn.active');
                if(activeTemplate) {
                    var tpl = activeTemplate.dataset.template;
                    if(tpl === 'ma_cross') { strategyName = "双均线策略"; returns = "+18.2%"; }
                    if(tpl === 'rsi_limit') { strategyName = "RSI超买超卖"; returns = "+12.5%"; }
                    if(tpl === 'price_break') { strategyName = "价格突破策略"; returns = "+32.1%"; }
                }
            }

            // Mock Result
            var html = `
                <div class="grid grid-cols-3 gap-4 mb-6">
                    <div class="bg-slate-800 p-4 rounded border border-slate-700">
                        <div class="text-slate-500 text-xs">总收益率</div>
                        <div class="text-2xl font-bold text-red-500">${returns}</div>
                    </div>
                    <div class="bg-slate-800 p-4 rounded border border-slate-700">
                        <div class="text-slate-500 text-xs">最大回撤</div>
                        <div class="text-2xl font-bold text-green-500">-5.2%</div>
                    </div>
                    <div class="bg-slate-800 p-4 rounded border border-slate-700">
                        <div class="text-slate-500 text-xs">夏普比率</div>
                        <div class="text-2xl font-bold text-slate-200">1.85</div>
                    </div>
                </div>
                <div class="bg-slate-800 p-4 rounded border border-slate-700 mb-4">
                    <h4 class="text-slate-300 font-bold mb-2">资金曲线 (Equity Curve) - ${strategyName}</h4>
                    <div class="h-64 bg-slate-900 rounded flex items-end px-2 gap-1" id="mock-chart">
                        <!-- CSS Mock Chart -->
                        ${Array.from({length: 50}, (_, i) => 
                            `<div style="width: 2%; height: ${50 + Math.random()*40}%; background-color: #38bdf8; opacity: ${0.5 + i/100}"></div>`
                        ).join('')}
                    </div>
                </div>
                <div class="bg-slate-800 p-4 rounded border border-slate-700">
                    <h4 class="text-slate-300 font-bold mb-2">交易日志 (Logs)</h4>
                    <table class="w-full text-sm text-left text-slate-400">
                        <thead class="text-xs uppercase bg-slate-700/50 text-slate-300">
                            <tr><th class="px-4 py-2">时间</th><th>方向</th><th>价格</th><th>盈亏</th></tr>
                        </thead>
                        <tbody>
                            <tr class="border-b border-slate-700"><td class="px-4 py-2">2023-01-05</td><td class="text-red-400">买入</td><td>15.20</td><td>-</td></tr>
                            <tr class="border-b border-slate-700"><td class="px-4 py-2">2023-02-10</td><td class="text-green-400">卖出</td><td>18.50</td><td class="text-red-400">+21.7%</td></tr>
                            <tr><td class="px-4 py-2">2023-03-15</td><td class="text-red-400">买入</td><td>17.80</td><td>-</td></tr>
                        </tbody>
                    </table>
                </div>
            `;
            content.innerHTML = html;
        }, 1500);
    });

    // 5. Mode Switching Logic
    var modeBtns = document.querySelectorAll('.mode-btn');
    modeBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            // Update UI State
            modeBtns.forEach(b => {
                b.classList.remove('active', 'bg-sky-600', 'text-white');
                b.classList.add('bg-slate-800', 'text-slate-400');
            });
            this.classList.add('active', 'bg-sky-600', 'text-white');
            this.classList.remove('bg-slate-800', 'text-slate-400');

            // Switch Views
            var mode = this.dataset.mode;
            document.getElementById('mode-graph').classList.toggle('hidden', mode !== 'graph');
            document.getElementById('mode-wizard').classList.toggle('hidden', mode !== 'wizard');

            // Resize canvas if graph mode
            if(mode === 'graph') {
                setTimeout(resize, 100);
            }
        });
    });

    // 6. Wizard Template Selection Logic
    var tplBtns = document.querySelectorAll('.wizard-template-btn');
    var configContainer = document.getElementById('wizard-config-container');
    
    tplBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            tplBtns.forEach(b => {
                b.classList.remove('active', 'border-sky-500');
                b.classList.add('border-slate-700');
                b.querySelector('.text-sky-400, .text-purple-400, .text-amber-400')?.classList.remove('text-sky-400', 'text-purple-400', 'text-amber-400'); // This is a bit rough, simplification for demo
            });
            this.classList.add('active', 'border-sky-500');
            this.classList.remove('border-slate-700');
            
            // Restore color (simplified for demo, usually we'd keep specific colors)
            var titleDiv = this.querySelector('div:first-child');
            // Reset colors
            document.querySelectorAll('.wizard-template-btn div:first-child').forEach(d => d.className = d.className.replace(/text-\w+-400/g, 'text-slate-400'));
            // Set active color
            if(this.dataset.template === 'ma_cross') titleDiv.classList.add('text-sky-400');
            if(this.dataset.template === 'rsi_limit') titleDiv.classList.add('text-purple-400');
            if(this.dataset.template === 'price_break') titleDiv.classList.add('text-amber-400');

            // Update Config Form
            updateWizardConfig(this.dataset.template);
        });
    });

    function updateWizardConfig(template) {
        var html = '';
        if(template === 'ma_cross') {
            html = `
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs text-slate-500 mb-1">快线周期 (Fast Period)</label>
                        <input type="number" value="5" class="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white focus:border-sky-500 outline-none">
                    </div>
                    <div>
                        <label class="block text-xs text-slate-500 mb-1">慢线周期 (Slow Period)</label>
                        <input type="number" value="20" class="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white focus:border-sky-500 outline-none">
                    </div>
                </div>`;
        } else if(template === 'rsi_limit') {
            html = `
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs text-slate-500 mb-1">RSI 周期</label>
                        <input type="number" value="14" class="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white focus:border-sky-500 outline-none">
                    </div>
                    <div>
                        <label class="block text-xs text-slate-500 mb-1">超买阈值 (Overbought)</label>
                        <input type="number" value="70" class="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white focus:border-sky-500 outline-none">
                    </div>
                    <div>
                        <label class="block text-xs text-slate-500 mb-1">超卖阈值 (Oversold)</label>
                        <input type="number" value="30" class="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white focus:border-sky-500 outline-none">
                    </div>
                </div>`;
        } else if(template === 'price_break') {
            html = `
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs text-slate-500 mb-1">突破周期 (Lookback Days)</label>
                        <input type="number" value="20" class="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white focus:border-sky-500 outline-none">
                    </div>
                    <div>
                        <label class="block text-xs text-slate-500 mb-1">突破幅度 (%)</label>
                        <input type="number" value="3.0" class="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white focus:border-sky-500 outline-none">
                    </div>
                </div>`;
        }
        configContainer.innerHTML = html;
    }

    // Initialize defaults
    // updateWizardConfig('ma_cross'); // Already hardcoded in HTML for init state

    // Auto-switch to Wizard mode if URL param says so (optional) or default behavior
    // For this user, let's default to Wizard mode for better UX
    setTimeout(function() {
        var wizardBtn = document.querySelector('.mode-btn[data-mode="wizard"]');
        if(wizardBtn) {
            // Check if user has seen help before or prefers graph
            // For now, default to Wizard as requested context implies difficulty
            wizardBtn.click();
        }
    }, 100);

    // Show Help on first graph load (optional, maybe too intrusive, let's rely on button)

    // 7. Canvas Toolbar Logic
    document.getElementById("btn-zoom-in").addEventListener("click", function() {
        canvas.ds.scale *= 1.1;
        canvas.setDirty(true, true);
    });
    document.getElementById("btn-zoom-out").addEventListener("click", function() {
        canvas.ds.scale *= 0.9;
        canvas.setDirty(true, true);
    });
    document.getElementById("btn-fit").addEventListener("click", function() {
        // Simple fit logic or reset
        canvas.ds.scale = 1;
        canvas.ds.offset = [0, 0];
        canvas.setDirty(true, true);
    });
    document.getElementById("btn-delete-node").addEventListener("click", function() {
        // LiteGraph standard way to delete selected
        if(canvas.selected_nodes) {
            for(var i in canvas.selected_nodes) {
                graph.remove(canvas.selected_nodes[i]);
            }
            canvas.selected_nodes = {};
        }
    });

    // Ensure canvas focus for keyboard events
    canvas.canvas.addEventListener("mousedown", function() {
        this.focus();
    });

    // Create a default graph
    var node_market = LiteGraph.createNode("Market/Data");
    node_market.pos = [100, 200];
    graph.add(node_market);

    var node_sma = LiteGraph.createNode("Indicators/SMA");
    node_sma.pos = [400, 100];
    graph.add(node_sma);

    var node_signal = LiteGraph.createNode("Trade/Signal");
    node_signal.pos = [700, 200];
    graph.add(node_signal);

    // Connect
    node_market.connect(0, node_sma, 0); // Close -> SMA Input

    graph.start();
})();
