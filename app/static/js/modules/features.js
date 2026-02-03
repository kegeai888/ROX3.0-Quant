
// ==========================================
// ROX QUANT FEATURES MODULE
// Covers: Weekly, Community, KB, Trading
// ==========================================

// --- Weekly Recommendations ---
export async function loadWeeklyRecommendations() {
    const container = document.getElementById('weekly-recommendations');
    if(!container) return;
    
    container.innerHTML = '<div class="text-center py-10 text-[#a8b5c8]"><i class="fas fa-spinner fa-spin text-2xl"></i><p class="mt-2">加载核心策略...</p></div>';

    try {
        const r = await fetch('/api/market/weekly');
        const data = await r.json();
        
        if (!data || !data.items) throw new Error("No data");

        container.innerHTML = data.items.map(item => `
            <div class="glass p-4 rounded-lg border-l-4 border-amber-500 hover:bg-[#1a2332] transition-all">
                <div class="flex justify-between items-start mb-2">
                    <div>
                        <h3 class="text-lg font-bold text-white">${item.name} <span class="text-sm text-[#a8b5c8] font-normal">(${item.code})</span></h3>
                        <p class="text-xs text-amber-400 mt-1"><i class="fas fa-quote-left mr-1"></i>${item.reason}</p>
                    </div>
                    <div class="text-right">
                        <div class="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-orange-500">${item.score}</div>
                        <div class="text-[10px] text-[#6b7a96]">AI评分</div>
                    </div>
                </div>
                <div class="flex gap-4 mt-3 pt-3 border-t border-[#2a3f5f] text-sm">
                    <div class="flex-1">
                        <span class="text-[#a8b5c8] block text-xs">目标价</span>
                        <span class="text-emerald-400 font-bold font-mono">${FormatUtils.formatPrice(item.target)}</span>
                    </div>
                    <div class="flex-1">
                        <span class="text-[#a8b5c8] block text-xs">止损价</span>
                        <span class="text-rose-400 font-bold font-mono">${FormatUtils.formatPrice(item.stop)}</span>
                    </div>
                    <div class="flex-1 text-right">
                        <button class="bg-[#2a3f5f] hover:bg-[#06b6d4] text-white px-3 py-1 rounded text-xs transition-colors" onclick="selectStock('${item.code}', '${item.name}')">
                            <i class="fas fa-chart-line mr-1"></i> 分析
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
        
        // Render 334 Chart if data exists
        if (data.strategy_334) {
             render334Chart(data.strategy_334);
        }

    } catch (e) {
        console.error("Weekly load failed:", e);
        container.innerHTML = '<div class="text-center py-10 text-rose-500">加载失败，请稍后重试</div>';
    }
}

export function render334Chart(data) {
    // This function might need a container in the HTML. 
    // Currently index.html doesn't have a specific container for this chart inside 'content-weekly' except appending to it.
    // Let's create one dynamically if not exists.
    let chartContainer = document.getElementById('chart-334');
    if (!chartContainer) {
        const parent = document.getElementById('content-weekly');
        if (!parent) return;
        
        const wrapper = document.createElement('div');
        wrapper.className = "glass p-4 rounded-lg mt-6";
        wrapper.innerHTML = `
            <h3 class="text-sm font-bold text-slate-300 mb-4">334仓位管理模型演示</h3>
            <div id="chart-334" class="w-full h-64"></div>
        `;
        parent.appendChild(wrapper);
        chartContainer = document.getElementById('chart-334');
    }

    const myChart = echarts.init(chartContainer);
    const option = {
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        grid: { top: 20, bottom: 20, left: 40, right: 20 },
        xAxis: { 
            type: 'category', 
            data: data.labels || [],
            axisLine: { lineStyle: { color: '#2a3f5f' } },
            axisLabel: { color: '#a8b5c8' }
        },
        yAxis: { 
            type: 'value', 
            splitLine: { lineStyle: { color: '#2a3f5f', type: 'dashed' } },
            axisLabel: { color: '#a8b5c8' }
        },
        series: [{
            data: data.data || [],
            type: 'bar',
            itemStyle: { color: '#06b6d4', borderRadius: [4, 4, 0, 0] },
            barWidth: '90%'
        }]
    };
    myChart.setOption(option);
    window.addEventListener('resize', () => myChart.resize());
}

// --- Community Feed ---
export async function loadCommunityFeed() {
    const container = document.getElementById('content-community');
    if(!container) return;

    // Clear previous placeholder
    container.innerHTML = `
        <h2 class="text-2xl font-bold text-cyan-400 mb-6">社区跟单</h2>
        <div id="community-list" class="space-y-4">
             <div class="text-center py-10 text-[#a8b5c8]"><i class="fas fa-spinner fa-spin text-2xl"></i></div>
        </div>
    `;
    
    const list = document.getElementById('community-list');

    try {
        const r = await fetch('/api/market/community/feed');
        const data = await r.json();
        
        if (!data || !data.items) throw new Error("No data");

        list.innerHTML = data.items.map(item => `
            <div class="glass p-4 rounded-lg flex gap-4">
                <img src="${item.avatar}" class="w-12 h-12 rounded-full border-2 border-[#2a3f5f]" alt="Avatar">
                <div class="flex-1">
                    <div class="flex justify-between items-start">
                        <div>
                            <h4 class="font-bold text-white text-sm">${item.user}</h4>
                            <p class="text-xs text-[#6b7a96]">${item.time}</p>
                        </div>
                        <span class="px-2 py-1 rounded text-xs font-bold ${item.action === '买入' ? 'bg-rose-500/20 text-rose-500' : 'bg-emerald-500/20 text-emerald-500'}">
                            ${item.action} ${item.symbol}
                        </span>
                    </div>
                    <p class="text-sm text-slate-300 mt-2">${item.comment}</p>
                    <div class="mt-2 text-xs text-[#a8b5c8] font-mono">成交价: ${FormatUtils.formatPrice(item.price)}</div>
                </div>
            </div>
        `).join('');

    } catch (e) {
        console.error("Community load failed:", e);
        list.innerHTML = '<div class="text-center py-10 text-rose-500">无法加载社区动态</div>';
    }
}

// --- Knowledge Base ---
export async function loadKBList() {
    const container = document.getElementById('kb-results');
    if(!container) return;
    
    container.innerHTML = '<div class="text-center py-4 text-[#a8b5c8]"><i class="fas fa-spinner fa-spin"></i></div>';
    
    // Also Init Graph if container exists
    const graphContainer = document.getElementById('kb-graph');
    if (graphContainer) {
        renderKnowledgeGraph();
    }

    try {
        const r = await fetch('/api/kb/docs');
        const data = await r.json();
        
        if (data.docs && data.docs.length > 0) {
            container.innerHTML = data.docs.map(doc => `
                <div class="p-2 hover:bg-[#1a2332] rounded cursor-pointer border-b border-[#2a3f5f] last:border-0" onclick="openKBDoc(${doc.id})">
                    <div class="font-bold text-slate-200 truncate">${doc.title}</div>
                    <div class="text-[10px] text-[#6b7a96]">${doc.desc}</div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="text-center py-4 text-[#6b7a96]">暂无文档</div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="text-center py-4 text-rose-500">加载失败</div>';
    }
}

export function renderKnowledgeGraph() {
    const dom = document.getElementById('kb-graph');
    if (!dom) return;
    
    // Check if already initialized
    if (echarts.getInstanceByDom(dom)) return;

    const myChart = echarts.init(dom);
    
    // Mock Data for Graph (In real app, fetch from API)
    const graphData = {
        nodes: [
            { id: '0', name: '宏观经济', symbolSize: 40, category: 0 },
            { id: '1', name: '货币政策', symbolSize: 25, category: 1 },
            { id: '2', name: '财政政策', symbolSize: 25, category: 1 },
            { id: '3', name: '股市', symbolSize: 35, category: 0 },
            { id: '4', name: '大消费', symbolSize: 20, category: 2 },
            { id: '5', name: '新能源', symbolSize: 20, category: 2 },
            { id: '6', name: '半导体', symbolSize: 20, category: 2 },
            { id: '7', name: '贵州茅台', symbolSize: 15, category: 3 },
            { id: '8', name: '宁德时代', symbolSize: 15, category: 3 },
            { id: '9', name: '中芯国际', symbolSize: 15, category: 3 },
            { id: '10', name: '外资流向', symbolSize: 15, category: 1 }
        ],
        links: [
            { source: '0', target: '1' },
            { source: '0', target: '2' },
            { source: '0', target: '3' },
            { source: '1', target: '3' },
            { source: '3', target: '4' },
            { source: '3', target: '5' },
            { source: '3', target: '6' },
            { source: '4', target: '7' },
            { source: '5', target: '8' },
            { source: '6', target: '9' },
            { source: '10', target: '3' },
            { source: '10', target: '7' }
        ],
        categories: [
            { name: '核心' },
            { name: '政策/资金' },
            { name: '板块' },
            { name: '个股' }
        ]
    };

    const option = {
        backgroundColor: 'transparent',
        tooltip: {},
        legend: [{
            data: graphData.categories.map(a => a.name),
            textStyle: { color: '#a8b5c8' },
            top: 0
        }],
        series: [
            {
                type: 'graph',
                layout: 'force',
                data: graphData.nodes.map(n => ({
                    ...n,
                    label: { show: true, color: '#fff' },
                    itemStyle: {
                        color: n.category === 0 ? '#d4af37' : 
                               n.category === 1 ? '#06b6d4' : 
                               n.category === 2 ? '#8b5cf6' : '#10b981'
                    }
                })),
                links: graphData.links,
                categories: graphData.categories,
                roam: true,
                label: {
                    position: 'right',
                    formatter: '{b}'
                },
                lineStyle: {
                    color: 'source',
                    curveness: 0.3
                },
                force: {
                    repulsion: 200,
                    edgeLength: 80
                }
            }
        ]
    };

    myChart.setOption(option);
    window.addEventListener('resize', () => myChart.resize());
}


export async function loadKnowledgeEssence() {
    const container = document.getElementById('kb-content');
    if(!container) return;
    
    // Check if empty, if so load essence
    if (container.innerHTML.trim() === '') {
        try {
            const r = await fetch('/api/kb/essence');
            const data = await r.json();
            
            container.innerHTML = `
                <h3 class="text-xl font-bold text-white mb-4">今日精选 · 投资内参</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    ${data.items.map(item => `
                        <div class="glass p-4 rounded-lg hover:border-cyan-500/50 transition-colors cursor-pointer">
                            <div class="flex justify-between mb-2">
                                <span class="text-xs font-bold text-cyan-400 bg-cyan-900/30 px-2 py-0.5 rounded">${item.category}</span>
                                <span class="text-xs text-[#6b7a96]"><i class="far fa-clock mr-1"></i>${item.read_time}</span>
                            </div>
                            <h4 class="font-bold text-slate-200 mb-2">${item.title}</h4>
                            <div class="text-xs text-[#a8b5c8]">点击阅读详情 &rarr;</div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (e) {
            container.innerHTML = '<p class="text-slate-500">无法加载精选内容</p>';
        }
    }
}

export async function searchKB() {
    const q = document.getElementById('kb-q')?.value;
    if (!q) return;
    
    const container = document.getElementById('kb-results');
    container.innerHTML = '<div class="text-center py-4 text-[#a8b5c8]"><i class="fas fa-spinner fa-spin"></i> 搜索中...</div>';
    
    try {
        const r = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
        const data = await r.json();
        
        if (data.results && data.results.length > 0) {
            container.innerHTML = data.results.map(res => `
                <div class="p-2 hover:bg-[#1a2332] rounded cursor-pointer border-b border-[#2a3f5f] last:border-0">
                    <div class="font-bold text-cyan-400 truncate">${res.title}</div>
                    <div class="text-[10px] text-[#a8b5c8] line-clamp-2">${res.desc}</div>
                </div>
            `).join('');
        } else {
             container.innerHTML = '<div class="text-center py-4 text-[#6b7a96]">未找到相关内容</div>';
        }
    } catch (e) {
        console.error(e);
        container.innerHTML = '<div class="text-center py-4 text-rose-500">搜索出错</div>';
    }
}

// --- Trading System (Moved to trading.js) ---
// Kept empty to avoid breaking if referenced, but functionality is in trading.js
export async function updateTradingDashboard() {
    console.warn("Using deprecated updateTradingDashboard from features.js. Use trading.js instead.");
}

export async function executeTrade(side) {
    console.warn("Using deprecated executeTrade from features.js. Use trading.js instead.");
}

// Make globally available
window.loadWeeklyRecommendations = loadWeeklyRecommendations;
window.render334Chart = render334Chart;
window.loadCommunityFeed = loadCommunityFeed;
window.loadKBList = loadKBList;
window.loadKnowledgeEssence = loadKnowledgeEssence;
window.searchKB = searchKB;
// Window exports for trading removed to avoid conflict with trading.js
