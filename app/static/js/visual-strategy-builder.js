
(function() {
    // Ensure the main app object exists, or create it.
    window.Rox = window.Rox || {};

    const VisualStrategyBuilder = {
        graph: null,
        graphCanvas: null,
        isInitialized: false,

        init() {
            if (this.isInitialized) {
                // Ensure canvas is resized correctly if window size changed
                this.graphCanvas.resize();
                return;
            }
            
            console.log("Initializing Visual Strategy Builder for the first time...");

            // 1. Create the graph instance
            this.graph = new LGraph();

            // 2. Create the canvas and link it to the graph
            this.graphCanvas = new LGraphCanvas("#visual-strategy-canvas", this.graph);
            this.graphCanvas.background_image = "/static/imgs/grid.png"; // A common grid background
            
            // 3. Redraw the graph on every execution
            this.graph.onAfterExecute = () => {
                this.graphCanvas.draw(true);
            };

            // 4. Start the rendering loop
            this.graph.start();
            
            // 5. Register our custom nodes
            this.registerCustomNodes();
            
            // 6. Add a default data source node to start
            this.addDefaultNode();

            this.isInitialized = true;
            console.log("Visual Strategy Builder Initialized.");
        },

        addDefaultNode() {
            const dataSourceNode = LiteGraph.createNode("quant/DataSource");
            dataSourceNode.pos = [200, 200];
            this.graph.add(dataSourceNode);

            const factorNode = LiteGraph.createNode("quant/Factor");
            factorNode.pos = [500, 200];
            this.graph.add(factorNode);

            dataSourceNode.connect(0, factorNode, 0);
        },

        loadStrategies() {
            console.log("Loading strategies...");
            fetch('/api/strategy/strategy/') // Note: redundant prefix as per project convention
                .then(response => response.json())
                .then(data => {
                    console.log("Strategies loaded:", data);
                    const listContainer = document.getElementById("strategy-list-container");
                    if (listContainer) {
                        listContainer.innerHTML = "";
                        data.forEach(strategy => {
                            const item = document.createElement("div");
                            item.className = "p-2 border-b border-gray-700 cursor-pointer hover:bg-gray-700";
                            item.innerText = strategy.name;
                            item.onclick = () => this.loadStrategy(strategy.id);
                            listContainer.appendChild(item);
                        });
                    }
                })
                .catch(error => console.error("Error loading strategies:", error));
        },

        loadStrategy(strategyId) {
            console.log(`Loading strategy: ${strategyId}`);
            this.currentStrategyId = strategyId;
            fetch(`/api/strategy/strategy/${strategyId}`)
                .then(response => response.json())
                .then(strategy => {
                    if (strategy && strategy.graph_json) {
                        const graphData = JSON.parse(strategy.graph_json);
                        this.graph.configure(graphData);
                        console.log("Strategy graph loaded.");
                    }
                })
                .catch(error => console.error("Error loading strategy:", error));
        },

        saveStrategy() {
            console.log("Saving strategy...");
            const name = prompt("请输入策略名称 (Enter Strategy Name):", "My Strategy");
            if (!name) return;

            const graphData = JSON.stringify(this.graph.serialize());
            const payload = {
                name: name,
                description: "Created via Visual Builder",
                graph_json: graphData
            };

            fetch('/api/strategy/strategy/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error("Network response was not ok");
                }
                return response.json();
            })
            .then(data => {
                console.log("Strategy saved:", data);
                alert("策略保存成功！");
                this.currentStrategyId = data.id; // Store current ID
                this.loadStrategies(); // Refresh the list
            })
            .catch(error => {
                console.error("Error saving strategy:", error);
                alert("保存失败，请查看控制台。");
            });
        },
        
        currentStrategyId: null,
        
        runStrategy() {
            if (!this.currentStrategyId) {
                alert("请先保存或加载一个策略！");
                return;
            }
            
            console.log(`Running strategy: ${this.currentStrategyId}`);
            // Show loading state
            const btn = event.target; // Assuming triggered by button click
            const originalText = btn.innerText;
            btn.innerText = "运行中...";
            btn.disabled = true;

            fetch(`/api/strategy/run/${this.currentStrategyId}`, {
                method: 'POST'
            })
            .then(response => response.json())
            .then(result => {
                btn.innerText = originalText;
                btn.disabled = false;
                
                console.log("Strategy execution result:", result);
                if (result.status === "success") {
                    this.showResultsModal(result.results);
                } else {
                    alert("执行失败：" + result.message);
                }
            })
            .catch(error => {
                btn.innerText = originalText;
                btn.disabled = false;
                console.error("Error running strategy:", error);
                alert("执行请求失败，请查看控制台。");
            });
        },

        runBacktest() {
            if (!this.currentStrategyId) {
                alert("请先保存或加载一个策略！");
                return;
            }

            const startDate = prompt("请输入回测开始日期 (YYYY-MM-DD):", "2023-01-01");
            if (!startDate) return;
            const endDate = prompt("请输入回测结束日期 (YYYY-MM-DD):", new Date().toISOString().split('T')[0]);
            if (!endDate) return;

            const btn = event.target;
            const originalText = btn.innerText;
            btn.innerText = "回测中...";
            btn.disabled = true;

            fetch(`/api/strategy/backtest/${this.currentStrategyId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ start_date: startDate, end_date: endDate, initial_capital: 100000 })
            })
            .then(response => response.json())
            .then(result => {
                btn.innerText = originalText;
                btn.disabled = false;

                console.log("Backtest result:", result);
                this.showBacktestModal(result);
            })
            .catch(error => {
                btn.innerText = originalText;
                btn.disabled = false;
                console.error("Error running backtest:", error);
                alert("回测请求失败，请查看控制台。");
            });
        },

        showBacktestModal(data) {
            const modalId = "backtest-result-modal";
            let modal = document.getElementById(modalId);
            if (modal) modal.remove();

            const modalHtml = `
                <div id="${modalId}" class="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50">
                    <div class="bg-[#1e293b] rounded-lg shadow-xl w-[800px] max-h-[90vh] flex flex-col border border-gray-600">
                        <div class="p-4 border-b border-gray-700 flex justify-between items-center bg-[#0f172a] rounded-t-lg">
                            <h3 class="text-lg font-bold text-white">历史回测结果</h3>
                            <button onclick="document.getElementById('${modalId}').remove()" class="text-gray-400 hover:text-white">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        <div class="p-4 flex-1 flex flex-col">
                            <div id="backtest-chart" class="w-full h-[400px] bg-[#0f172a] mb-4"></div>
                            <div class="text-sm text-gray-300">
                                <p>总收益: <span class="text-green-400 font-bold">${((data.equity_curve[data.equity_curve.length-1] - 100000)/1000).toFixed(2)}k</span></p>
                            </div>
                        </div>
                        <div class="p-4 border-t border-gray-700 bg-[#0f172a] rounded-b-lg text-right">
                             <button onclick="document.getElementById('${modalId}').remove()" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-500 text-sm">关闭</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHtml);

            // Render Chart using LightweightCharts
            const chartContainer = document.getElementById('backtest-chart');
            const chart = LightweightCharts.createChart(chartContainer, {
                width: chartContainer.clientWidth,
                height: 400,
                layout: { backgroundColor: '#0f172a', textColor: '#d1d5db' },
                grid: { vertLines: { color: '#334155' }, horzLines: { color: '#334155' } },
                timeScale: { borderColor: '#475569' }
            });

            const lineSeries = chart.addLineSeries({
                color: '#4ade80',
                lineWidth: 2,
            });

            const chartData = data.dates.map((date, index) => ({
                time: date,
                value: data.equity_curve[index]
            }));

            lineSeries.setData(chartData);
            chart.timeScale().fitContent();
        },

        showResultsModal(results) {
            // Find SignalOutput results
            let signalData = null;
            for (const nodeId in results) {
                // Heuristic: Check if the result looks like a signal dict {symbol: weight}
                const res = results[nodeId];
                if (typeof res === 'object' && res !== null && !Array.isArray(res)) {
                    // Check if keys look like symbols
                    const keys = Object.keys(res);
                    if (keys.length > 0 && (keys[0].includes(".SH") || keys[0].includes(".SZ") || keys[0].match(/^\d{6}$/))) {
                        signalData = res;
                        break;
                    }
                }
            }

            if (!signalData) {
                alert("执行成功，但未找到有效的信号输出。\n" + JSON.stringify(results, null, 2));
                return;
            }

            // Create Modal HTML
            const modalId = "strategy-result-modal";
            let modal = document.getElementById(modalId);
            if (modal) modal.remove();

            const rows = Object.entries(signalData)
                .sort((a, b) => b[1] - a[1])
                .map(([symbol, weight]) => `
                <tr class="border-b border-gray-700">
                    <td class="p-2 text-sky-400 font-mono">${symbol}</td>
                    <td class="p-2 text-right text-green-400">${(weight * 100).toFixed(2)}%</td>
                </tr>
            `).join("");

            const modalHtml = `
                <div id="${modalId}" class="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50">
                    <div class="bg-[#1e293b] rounded-lg shadow-xl w-96 max-h-[80vh] flex flex-col border border-gray-600">
                        <div class="p-4 border-b border-gray-700 flex justify-between items-center bg-[#0f172a] rounded-t-lg">
                            <h3 class="text-lg font-bold text-white">策略回测结果</h3>
                            <button onclick="document.getElementById('${modalId}').remove()" class="text-gray-400 hover:text-white">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        <div class="p-4 overflow-y-auto flex-1">
                            <p class="text-sm text-gray-400 mb-2">生成信号数量: ${Object.keys(signalData).length}</p>
                            <table class="w-full text-sm text-left">
                                <thead class="text-xs text-gray-500 uppercase bg-gray-800">
                                    <tr>
                                        <th class="p-2">代码 (Symbol)</th>
                                        <th class="p-2 text-right">权重 (Weight)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${rows}
                                </tbody>
                            </table>
                        </div>
                        <div class="p-4 border-t border-gray-700 bg-[#0f172a] rounded-b-lg text-right">
                             <button onclick="document.getElementById('${modalId}').remove()" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-500 text-sm">关闭</button>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHtml);
        },

        newStrategy() {
            this.graph.clear();
            console.log("New blank strategy created.");
        },

        registerCustomNodes() {
            console.log("Registering custom nodes...");

            // Data Source Node
            function DataSourceNode() {
                this.addOutput("股票池 (Stock Pool)", "Array");
                this.properties = {
                    poolName: "沪深300"
                };
                this.widget = this.addWidget("combo", "股票池", this.properties.poolName, (value) => {
                    this.properties.poolName = value;
                }, {
                    values: ["沪深300", "中证500", "全市场"]
                });
                this.title = "数据源 (Data Source)";
                this.color = "#2B547E"; // A nice blue color
            }
            DataSourceNode.title = "数据源 (Data Source)";
            DataSourceNode.desc = "选择一个股票池作为策略的起点";
            
            // This function is called when the graph is executed
            DataSourceNode.prototype.onExecute = function() {
                // For now, we just output the name of the pool.
                // Later, this will trigger a data fetch.
                this.setOutputData(0, this.properties.poolName);
            };
            
            LiteGraph.registerNodeType("quant/DataSource", DataSourceNode);
            
            console.log("Node 'quant/DataSource' registered.");

            // Factor Node
            function FactorNode() {
                this.addInput("股票池 (Stock Pool)", "Array");
                this.addOutput("筛选后股票 (Filtered)", "Array");
                this.properties = {
                    factor: "pe_ratio",
                    operator: "<",
                    value: 30
                };

                // Widgets for user interaction
                this.addWidget("combo", "因子 (Factor)", this.properties.factor, (v) => { this.properties.factor = v; }, { values: ["pe_ratio", "pb_ratio", "market_cap"] });
                this.addWidget("combo", "操作 (Operator)", this.properties.operator, (v) => { this.properties.operator = v; }, { values: ["<", ">", "=", "<=", ">="] });
                this.addWidget("number", "值 (Value)", this.properties.value, (v) => { this.properties.value = v; }, { min: 0, step: 0.1 });

                this.title = "因子筛选 (Factor Filter)";
                this.color = "#7E542B"; // An earthy orange color
            }
            FactorNode.title = "因子筛选 (Factor Filter)";
            FactorNode.desc = "根据指定的因子条件筛选股票";

            FactorNode.prototype.onExecute = function() {
                // In a real scenario, we would get an array of stock objects
                // and filter them based on the properties.
                const inputPool = this.getInputData(0);
                if (!inputPool) {
                    return;
                }
                // For now, just pass the data through with the filter info
                const filterInfo = `${inputPool} where ${this.properties.factor} ${this.properties.operator} ${this.properties.value}`;
                this.setOutputData(0, filterInfo);
            };

            LiteGraph.registerNodeType("quant/Factor", FactorNode);
            console.log("Node 'quant/Factor' registered.");

            // Combine Node
            function CombineNode() {
                this.addInput("输入 A (Input A)", "Array");
                this.addInput("输入 B (Input B)", "Array");
                this.addOutput("组合结果 (Result)", "Array");
                this.properties = {
                    operation: "AND"
                };
                this.addWidget("combo", "逻辑 (Logic)", this.properties.operation, (v) => { this.properties.operation = v; }, { values: ["AND", "OR"] });
                this.title = "逻辑组合 (Combine)";
                this.color = "#2B7E54"; // A nice green color
            }
            CombineNode.title = "逻辑组合 (Combine)";
            CombineNode.desc = "对两个输入集合进行逻辑运算 (交集/并集)";

            CombineNode.prototype.onExecute = function() {
                const inputA = this.getInputData(0);
                const inputB = this.getInputData(1);
                
                if (!inputA || !inputB) {
                    return;
                }

                const result = `(${inputA}) ${this.properties.operation} (${inputB})`;
                this.setOutputData(0, result);
            };

            LiteGraph.registerNodeType("quant/Combine", CombineNode);
            console.log("Node 'quant/Combine' registered.");

            // Selection Node
            function SelectionNode() {
                this.addInput("股票池 (Stock Pool)", "Array");
                this.addOutput("选股结果 (Selected)", "Array");
                this.properties = {
                    sortBy: "market_cap",
                    direction: "desc", // desc or asc
                    topN: 10
                };
                
                this.addWidget("combo", "排序依据 (Sort By)", this.properties.sortBy, (v) => { this.properties.sortBy = v; }, { values: ["market_cap", "pe_ratio", "pb_ratio", "return_rate"] });
                this.addWidget("combo", "方向 (Direction)", this.properties.direction, (v) => { this.properties.direction = v; }, { values: ["desc", "asc"] });
                this.addWidget("number", "数量 (Top N)", this.properties.topN, (v) => { this.properties.topN = v; }, { min: 1, step: 1, precision: 0 });

                this.title = "筛选排序 (Sort & Select)";
                this.color = "#7E2B54"; // A purple/magenta color
            }
            SelectionNode.title = "筛选排序 (Sort & Select)";
            SelectionNode.desc = "对股票进行排序并选择前N名";

            SelectionNode.prototype.onExecute = function() {
                const inputPool = this.getInputData(0);
                if (!inputPool) {
                    return;
                }
                const result = `Top ${this.properties.topN} from (${inputPool}) sorted by ${this.properties.sortBy} ${this.properties.direction}`;
                this.setOutputData(0, result);
            };

            LiteGraph.registerNodeType("quant/Selection", SelectionNode);
            console.log("Node 'quant/Selection' registered.");

            // Weighting Node
            function WeightingNode() {
                this.addInput("选股结果 (Selected)", "Array");
                this.addOutput("持仓权重 (Weights)", "Array");
                this.properties = {
                    method: "equal", // equal or market_cap
                    totalWeight: 1.0
                };
                
                this.addWidget("combo", "权重方式 (Method)", this.properties.method, (v) => { this.properties.method = v; }, { values: ["equal", "market_cap"] });
                this.addWidget("number", "总仓位 (Total Pos)", this.properties.totalWeight, (v) => { this.properties.totalWeight = v; }, { min: 0.1, max: 1.0, step: 0.1 });

                this.title = "仓位分配 (Weighting)";
                this.color = "#542B7E"; // A deep violet color
            }
            WeightingNode.title = "仓位分配 (Weighting)";
            WeightingNode.desc = "为选定的股票分配持仓权重";

            WeightingNode.prototype.onExecute = function() {
                const inputPool = this.getInputData(0);
                if (!inputPool) {
                    return;
                }
                const result = `Assign ${this.properties.method} weights to (${inputPool}), total: ${this.properties.totalWeight}`;
                this.setOutputData(0, result);
            };

            LiteGraph.registerNodeType("quant/Weighting", WeightingNode);
            console.log("Node 'quant/Weighting' registered.");

            // Signal Output Node
            function SignalOutputNode() {
                this.addInput("持仓权重 (Weights)", "Array");
                this.title = "信号输出 (Signal Output)";
                this.color = "#8B0000"; // Dark red for final output
            }
            SignalOutputNode.title = "信号输出 (Signal Output)";
            SignalOutputNode.desc = "策略的最终输出节点";

            SignalOutputNode.prototype.onExecute = function() {
                const inputWeights = this.getInputData(0);
                if (!inputWeights) {
                    return;
                }
                // In a real app, this would be collected by the graph runner
                console.log("Strategy Signal Output:", inputWeights);
            };

            LiteGraph.registerNodeType("quant/SignalOutput", SignalOutputNode);
            console.log("Node 'quant/SignalOutput' registered.");
        }
    };

    // Expose the builder to the global Rox object so it can be called from main.js
    window.Rox.VisualStrategyBuilder = VisualStrategyBuilder;

})();
