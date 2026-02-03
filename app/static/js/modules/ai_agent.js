
export class AIAgentController {
    constructor() {
        this.card = document.getElementById('ai-agent-card');
        if (!this.card) {
            console.log("AIAgentController: AI Agent Card not found in DOM, skipping init.");
            return;
        }
        this.chatHistory = document.getElementById('ai-chat-history');
        this.input = document.getElementById('ai-input');
        this.isVisible = false;
        
        // Stock Info Elements
        this.elStockName = document.getElementById('ai-stock-name');
        this.elStockCode = document.getElementById('ai-stock-code');
        this.elStockPrice = document.getElementById('ai-stock-price');
        this.elStockChange = document.getElementById('ai-stock-change');
        
        // Analysis Elements
        this.elSentimentScore = document.getElementById('ai-sentiment-score');
        this.elSentimentBar = document.getElementById('ai-sentiment-bar');
        this.elSentimentText = document.getElementById('ai-sentiment-text');
        this.elFundVal = document.getElementById('ai-fund-val');
        this.elFundText = document.getElementById('ai-fund-text');
        this.elDiagnosisList = document.getElementById('ai-diagnosis-list');
        
        this.currentStock = null;
        
        this.init();
    }
    
    init() {
        // Expose toggle globally
        window.toggleAIAgent = () => this.toggle();
        window.sendAIMessage = () => this.sendMessage();
        window.setInput = (text) => {
            if (this.input) {
                this.input.value = text;
                this.input.focus();
            }
        };
        
        // Enter key to send
        if (this.input) {
            this.input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        // Make draggable
        this.makeDraggable();
    }
    
    makeDraggable() {
        const header = this.card.querySelector('.ai-header') || this.card.firstElementChild; 
        if (!header) return;
        
        header.style.cursor = 'move';
        let isDragging = false;
        let startX, startY, initialLeft, initialTop;
        
        const onMouseDown = (e) => {
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            
            // Get current computed position
            const rect = this.card.getBoundingClientRect();
            // If right/bottom are set, we need to switch to left/top for dragging
            if (this.card.style.left === '' && this.card.style.right !== '') {
                this.card.style.left = rect.left + 'px';
                this.card.style.right = 'auto';
            }
            if (this.card.style.top === '' && this.card.style.bottom !== '') {
                this.card.style.top = rect.top + 'px';
                this.card.style.bottom = 'auto';
            }
            
            initialLeft = this.card.offsetLeft;
            initialTop = this.card.offsetTop;
            
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        };
        
        const onMouseMove = (e) => {
            if (!isDragging) return;
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            this.card.style.left = `${initialLeft + dx}px`;
            this.card.style.top = `${initialTop + dy}px`;
        };
        
        const onMouseUp = () => {
            isDragging = false;
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };
        
        header.addEventListener('mousedown', onMouseDown);
    }
    
    toggle() {
        this.isVisible = !this.isVisible;
        if (this.isVisible) {
            this.card.classList.remove('hidden');
            // Sync with current stock if available
            if (window.currentStockCode) {
                this.analyzeStock(window.currentStockCode);
            }
            this.input.focus();
        } else {
            this.card.classList.add('hidden');
        }
    }
    
    appendMessage(role, text) {
        const isUser = role === 'user';
        const div = document.createElement('div');
        div.className = `flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`;
        
        const avatar = isUser 
            ? `<div class="w-8 h-8 rounded-full bg-gray-700 flex-shrink-0 flex items-center justify-center mt-1"><i class="fas fa-user text-xs text-gray-400"></i></div>`
            : `<div class="w-8 h-8 rounded-full bg-gradient-to-br from-purple-600 to-blue-500 flex-shrink-0 flex items-center justify-center mt-1"><i class="fas fa-robot text-white text-xs"></i></div>`;
            
        const bubbleClass = isUser
            ? 'bg-[#333] text-white border border-[#444]'
            : 'bg-[#1e1e1e] text-gray-300 border border-[#333]';
            
        div.innerHTML = `
            ${avatar}
            <div class="flex-1 max-w-[80%]">
                <div class="${bubbleClass} p-3 rounded-lg ${isUser ? 'rounded-tr-none' : 'rounded-tl-none'} text-sm leading-relaxed shadow-sm">
                    ${this.formatText(text)}
                </div>
            </div>
        `;
        
        this.chatHistory.appendChild(div);
        this.chatHistory.scrollTop = this.chatHistory.scrollHeight;
    }
    
    formatText(text) {
        // Simple markdown-like formatting
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }
    
    async sendMessage() {
        const text = this.input.value.trim();
        if (!text) return;
        
        this.appendMessage('user', text);
        this.input.value = '';
        
        // Show typing indicator
        const typingId = 'typing-' + Date.now();
        this.appendMessage('ai', `<span id="${typingId}"><i class="fas fa-circle-notch fa-spin mr-2"></i>思考中...</span>`);
        
        try {
            // Call API
            const response = await fetch('/api/ai/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, context: this.getContext() })
            });
            
            const data = await response.json();
            
            // Remove typing
            const typingEl = document.getElementById(typingId);
            if(typingEl && typingEl.parentElement) {
                typingEl.parentElement.parentElement.parentElement.remove(); // Remove entire bubble
            }
            
            this.appendMessage('ai', data.response || "抱歉，我暂时无法回答。");
            
            // If response contains stock analysis data (structured), update dashboard
            // For now, we simulate this update if the user asked about a stock code
            const stockMatch = text.match(/\d{6}/);
            if (stockMatch) {
                this.analyzeStock(stockMatch[0]);
            }
            
        } catch (e) {
            console.error(e);
            this.appendMessage('ai', "网络连接错误，请稍后再试。");
        }
    }
    
    getContext() {
        return `当前正在查看股票：${this.currentStock ? this.currentStock.name : '未知'}`;
    }
    
    async analyzeStock(code) {
        // Fetch real-time data to populate the dashboard
        try {
            // 1. Fetch Basic Info
            const resp = await fetch('/api/market/fetch-realtime', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({ stock_name: code })
            });
            const data = await resp.json();
            
            if (data.error) return;
            
            this.currentStock = data;
            
            // Update UI
            this.elStockName.textContent = data.name;
            this.elStockCode.textContent = data.code;
            this.elStockPrice.textContent = data.p_now.toFixed(2);
            // Assuming data has change info, if not calculate or leave placeholder
            // Mocking change for now if missing
            const change = (Math.random() * 4 - 2).toFixed(2); 
            this.elStockChange.textContent = `${change > 0 ? '+' : ''}${change}%`;
            this.elStockChange.className = `text-xs font-mono ${change > 0 ? 'text-red-500' : 'text-green-500'}`;
            this.elStockPrice.className = `text-xl font-mono font-bold ${change > 0 ? 'text-red-500' : 'text-green-500'}`;

            // 2. Fetch Diagnosis (Simulated or Real)
            const diagResp = await fetch(`/api/market/diagnose?code=${code}`);
            const diagData = await diagResp.json();
            
            // Update Sentiment
            // Map score 0-100 to text
            const score = diagData.score || 75;
            this.elSentimentScore.textContent = score;
            this.elSentimentBar.style.width = `${score}%`;
            this.elSentimentText.textContent = diagData.summary || "分析完成";
            
            // Update Fund Flow
            this.elFundVal.textContent = diagData.capital_score ? "强劲流入" : "正常波动"; // Mock logic
            this.elFundText.textContent = diagData.capital || "资金面平稳";
            
            // Update Diagnosis List
            this.elDiagnosisList.innerHTML = `
                <li>${diagData.technicals || '技术面中性'}</li>
                <li>${diagData.fundamentals || '基本面稳健'}</li>
                <li>${diagData.capital || '资金流向关注'}</li>
            `;
            
            // Update Indicators (Mock for now as diagnose API returns text summary)
            document.getElementById('ai-ind-rsi').textContent = (30 + Math.random() * 40).toFixed(1);
            document.getElementById('ai-ind-kdj').textContent = (20 + Math.random() * 60).toFixed(1);
            
            // Draw Mini Chart
            this.drawMiniChart(data.p_now);
            
        } catch (e) {
            console.error("Analysis failed", e);
        }
    }
    
    drawMiniChart(currentPrice) {
        const container = document.getElementById('ai-mini-chart');
        if (!container) return;
        
        container.innerHTML = '';
        const w = container.clientWidth;
        const h = container.clientHeight;
        
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        container.appendChild(canvas);
        
        const ctx = canvas.getContext('2d');
        
        // Generate mock minute data
        const points = [];
        let price = currentPrice * 0.98;
        for(let i=0; i<60; i++) {
            price = price + (Math.random() - 0.5) * currentPrice * 0.005;
            points.push(price);
        }
        // Force end at current
        points.push(currentPrice);
        
        const min = Math.min(...points);
        const max = Math.max(...points);
        const range = max - min;
        
        ctx.beginPath();
        ctx.strokeStyle = currentPrice > points[0] ? '#ef4444' : '#22c55e'; // Red if up, Green if down
        ctx.lineWidth = 2;
        
        points.forEach((p, i) => {
            const x = (i / (points.length - 1)) * w;
            const y = h - ((p - min) / range) * h * 0.8 - h * 0.1; // Padding
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();
        
        // Fill gradient
        ctx.lineTo(w, h);
        ctx.lineTo(0, h);
        ctx.closePath();
        const grad = ctx.createLinearGradient(0, 0, 0, h);
        grad.addColorStop(0, currentPrice > points[0] ? 'rgba(239, 68, 68, 0.2)' : 'rgba(34, 197, 94, 0.2)');
        grad.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = grad;
        ctx.fill();
    }
}
