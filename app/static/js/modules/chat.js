
// ==========================================
// ROX QUANT AI CHAT MODULE
// ==========================================

export class AIChatWidget {
    constructor() {
        this.isOpen = false;
        this.isTyping = false;
        this.messages = [];
        this.initUI();
    }

    initUI() {
        // Create Floating Button
        this.btn = document.createElement('button');
        this.btn.className = "fixed bottom-6 right-6 w-14 h-14 bg-gradient-to-r from-cyan-500 to-blue-600 rounded-full shadow-lg shadow-cyan-500/30 text-white flex items-center justify-center text-2xl z-50 hover:scale-110 transition-transform cursor-pointer touch-none";
        // Icon should not capture events to ensure button captures mousedown for dragging
        this.btn.innerHTML = '<i class="fas fa-robot pointer-events-none"></i>';
        
        // Draggable Button Logic
        this.makeDraggable(this.btn);
        
        // Click handling (distinguish from drag)
        this.btn.addEventListener('click', (e) => {
            if (!this.btn.isDragging) {
                this.toggle();
            }
        });

        document.body.appendChild(this.btn);

        // Create Chat Window
        this.window = document.createElement('div');
        this.window.className = "fixed w-80 md:w-96 h-[500px] bg-[#0f172a]/95 backdrop-blur-xl border border-[#2a3f5f] rounded-2xl shadow-2xl z-50 flex flex-col hidden transition-opacity duration-300";
        // Default position handled in toggle() or CSS if not moved
        
        this.window.innerHTML = `
            <!-- Header -->
            <div id="chat-header" class="h-14 border-b border-[#2a3f5f] flex items-center justify-between px-4 bg-gradient-to-r from-[#141928] to-[#0f172a] rounded-t-2xl cursor-move select-none">
                <div class="flex items-center gap-2 pointer-events-none">
                    <div class="w-8 h-8 rounded-full bg-cyan-500/20 flex items-center justify-center text-cyan-400">
                        <i class="fas fa-brain"></i>
                    </div>
                    <div>
                        <h3 class="font-bold text-white text-sm">Rox AI 助手</h3>
                        <p class="text-[10px] text-emerald-500 flex items-center"><span class="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-1 animate-pulse"></span>在线</p>
                    </div>
                </div>
                <button id="chat-toggle-btn" class="text-[#a8b5c8] hover:text-white transition-colors cursor-pointer">
                    <i class="fas fa-times"></i>
                </button>
            </div>

            <!-- Messages Area -->
            <div id="chat-messages" class="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar bg-[#0f172a]/50">
                <!-- Welcome Message -->
                <div class="flex gap-3">
                    <div class="w-8 h-8 rounded-full bg-cyan-500/20 flex-shrink-0 flex items-center justify-center text-cyan-400 text-xs mt-1">AI</div>
                    <div class="bg-[#1e293b] text-slate-200 p-3 rounded-2xl rounded-tl-none text-sm leading-relaxed border border-[#2a3f5f] shadow-sm">
                        你好！我是你的专属量化助手。你可以问我：
                        <ul class="list-disc list-inside mt-2 text-xs text-[#a8b5c8] space-y-1">
                            <li>分析当前股票 (如: 分析茅台)</li>
                            <li>解释 MACD 指标</li>
                            <li>生成布林带策略代码</li>
                            <li>查询最新的市场热点</li>
                        </ul>
                    </div>
                </div>
            </div>

            <!-- Input Area -->
            <div class="p-4 border-t border-[#2a3f5f] bg-[#141928] rounded-b-2xl">
                <div class="relative">
                    <input type="text" id="chat-input" 
                        class="w-full bg-[#0a0f23] text-sm text-white rounded-full pl-4 pr-12 py-3 border border-[#2a3f5f] focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 outline-none transition-all placeholder-slate-600"
                        placeholder="输入问题..." autocomplete="off">
                    <button id="chat-send-btn" type="button"
                        class="absolute right-2 top-2 w-8 h-8 bg-cyan-600 hover:bg-cyan-500 text-white rounded-full flex items-center justify-center transition-colors shadow-lg cursor-pointer z-10">
                        <i class="fas fa-paper-plane text-xs pointer-events-none"></i>
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(this.window);

        // Bind Events
        const input = this.window.querySelector('#chat-input');
        const sendBtn = this.window.querySelector('#chat-send-btn');
        const toggleBtn = this.window.querySelector('#chat-toggle-btn'); // Header close button

        if (input) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault(); // Prevent default form submission if any
                    this.send();
                }
            });
        } else {
            console.error("Chat: Input element not found");
        }

        if (sendBtn) {
            // Remove any existing listeners (not possible on new element, but good practice if logic changes)
            sendBtn.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log("Chat: Send button clicked");
                this.send();
            };
        } else {
            console.error("Chat: Send button not found");
        }

        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => this.toggle());
        }

        // Draggable Window Logic
        const header = this.window.querySelector('#chat-header');
        if (header) {
            this.makeDraggable(this.window, header);
        }
    }

    // Make an element draggable
    makeDraggable(elmnt, handle) {
        const dragHandle = handle || elmnt;
        let isDragging = false;
        let startX, startY, initialLeft, initialTop;

        const onMouseDown = (e) => {
            // Only left click
            if (e.button !== 0) return;
            // If target is the close button or its child, don't drag
            const closestBtn = e.target.closest('button');
            if (e.target.closest('#chat-toggle-btn') || (closestBtn && closestBtn !== elmnt)) {
                return;
            }

            e.preventDefault(); // Prevent text selection
            
            isDragging = false;
            startX = e.clientX;
            startY = e.clientY;

            // 1. Lock current position to absolute left/top before moving
            const rect = elmnt.getBoundingClientRect();
            
            // If we haven't converted to top/left yet (e.g. initial bottom/right state)
            // or just to be safe, always sync.
            elmnt.style.left = rect.left + 'px';
            elmnt.style.top = rect.top + 'px';
            elmnt.style.bottom = 'auto';
            elmnt.style.right = 'auto';
            
            // Remove margin effects if any, to ensure pure absolute positioning
            elmnt.style.margin = '0';

            initialLeft = rect.left;
            initialTop = rect.top;

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        };

        const onMouseMove = (e) => {
            // Threshold to consider it a drag (prevent jitter clicks)
            if (!isDragging && (Math.abs(e.clientX - startX) > 2 || Math.abs(e.clientY - startY) > 2)) {
                isDragging = true;
                elmnt.isDragging = true; // Flag for click handler
            }
            
            if (!isDragging) return;

            e.preventDefault();

            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            
            let newLeft = initialLeft + dx;
            let newTop = initialTop + dy;

            // Boundary checks
            const winW = window.innerWidth;
            const winH = window.innerHeight;
            const elW = elmnt.offsetWidth;
            const elH = elmnt.offsetHeight;

            if (newLeft < 0) newLeft = 0;
            if (newTop < 0) newTop = 0;
            if (newLeft + elW > winW) newLeft = winW - elW;
            if (newTop + elH > winH) newTop = winH - elH;

            elmnt.style.left = newLeft + 'px';
            elmnt.style.top = newTop + 'px';
        };

        const onMouseUp = () => {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            
            // Reset flag after a short delay to allow click handler to check it
            setTimeout(() => {
                elmnt.isDragging = false;
                isDragging = false;
            }, 50);
        };

        dragHandle.addEventListener('mousedown', onMouseDown);
    }

    toggle() {
        this.isOpen = !this.isOpen;
        if (this.isOpen) {
            this.window.classList.remove('hidden');
            
            // Initial positioning if not set
            if (!this.window.style.top && !this.window.style.left) {
                 const btnRect = this.btn.getBoundingClientRect();
                 const winWidth = 384; // w-96 = 24rem = 384px (approx)
                 const winHeight = 500;
                 
                 // Default: Above and Left of button
                 let t = btnRect.top - winHeight - 20;
                 let l = btnRect.right - winWidth;
                 
                 // Boundary check
                 if (t < 10) t = 10;
                 if (l < 10) l = 10;
                 if (l + winWidth > window.innerWidth) l = window.innerWidth - winWidth - 10;
                 
                 this.window.style.top = t + 'px';
                 this.window.style.left = l + 'px';
                 this.window.style.bottom = 'auto';
                 this.window.style.right = 'auto';
            }
            
            this.window.classList.remove('scale-95', 'opacity-0');
            this.window.classList.add('scale-100', 'opacity-100');
            setTimeout(() => {
                const inp = this.window.querySelector('#chat-input');
                if (inp) inp.focus();
            }, 100);
        } else {
            this.window.classList.add('hidden');
        }
    }

    async send() {
        console.log("Chat: Send triggered");
        const input = this.window.querySelector('#chat-input');
        if (!input) {
            console.error("Chat: Input element missing in send()");
            return;
        }
        const text = input.value.trim();
        if (!text) {
            console.log("Chat: Empty input, ignoring");
            return;
        }

        // User Message
        try {
            this.appendMessage('user', text);
            input.value = '';
            this.isTyping = true;
            
            // Typing Indicator
            const typingId = this.showTyping();
            this.scrollToBottom();

            // Context Awareness
            let contextObj = {};
            try {
                contextObj = {
                    currentStock: window.currentStockCode || window._lastDiagnosisSymbol || '',
                    currentPrice: document.getElementById('diag-price')?.innerText || document.getElementById('diag-f-current')?.innerText || '',
                    mode: 'market' // Default
                };
                
                // Try to get active tab mode safely
                try {
                    const activeTab = document.querySelector('.text-[#06b6d4].bg-\\[\\#1a2332\\]');
                    if (activeTab && activeTab.id) {
                        contextObj.mode = activeTab.id.replace('nav-', '');
                    }
                } catch (err) {
                    console.warn("Chat: Failed to detect active tab", err);
                }
            } catch (ctxErr) {
                console.warn("Chat: Context creation failed, using empty context", ctxErr);
            }

            // Call Backend API
            const token = localStorage.getItem('access_token');
            const headers = { 'Content-Type': 'application/json' };
            if (token) {
                headers['Authorization'] = 'Bearer ' + token;
            }

            console.log("Sending chat message:", text, contextObj);

            const response = await fetch('/api/ai/chat', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({ 
                    message: text, 
                    context: JSON.stringify(contextObj) 
                })
            });

            if (!response.ok) {
                console.error("Chat API Error:", response.status, response.statusText);
                const errText = await response.text();
                console.error("Error details:", errText);
                throw new Error(`Server error: ${response.status}`);
            }

            if (response.status === 401) {
                this.removeMessage(typingId);
                this.appendMessage('ai', '请先登录后再使用 AI 助手。');
                if (typeof showAuthModal === 'function') showAuthModal();
                return;
            }

            const data = await response.json();
            const reply = data.response || "抱歉，我暂时无法回答。";

            this.removeMessage(typingId);
            this.appendMessage('ai', reply);

        } catch (e) {
            console.error("Chat Error:", e);
            // Try to remove typing indicator if it exists
            const typingInd = this.window.querySelector('[id^="typing-"]');
            if (typingInd) typingInd.remove();
            
            this.appendMessage('ai', '抱歉，网络连接异常，请稍后再试。');
        }

        this.isTyping = false;
        this.scrollToBottom();
    }

    appendMessage(role, text) {
        const container = this.window.querySelector('#chat-messages');
        if (!container) return;
        
        const div = document.createElement('div');
        div.className = "flex gap-3 animate-fade-in";
        
        if (role === 'user') {
            div.innerHTML = `
                <div class="flex-1 flex justify-end">
                    <div class="bg-cyan-600 text-white p-3 rounded-2xl rounded-tr-none text-sm shadow-md max-w-[85%]">
                        ${this.escapeHtml(text)}
                    </div>
                </div>
                <div class="w-8 h-8 rounded-full bg-slate-700 flex-shrink-0 flex items-center justify-center text-slate-300 text-xs mt-1">我</div>
            `;
        } else {
            // AI Message supports simple Markdown (Code blocks, Bold)
            const formatted = this.formatText(text);
            div.innerHTML = `
                <div class="w-8 h-8 rounded-full bg-cyan-500/20 flex-shrink-0 flex items-center justify-center text-cyan-400 text-xs mt-1">AI</div>
                <div class="bg-[#1e293b] text-slate-200 p-3 rounded-2xl rounded-tl-none text-sm leading-relaxed border border-[#2a3f5f] shadow-sm max-w-[85%]">
                    ${formatted}
                </div>
            `;
        }
        
        container.appendChild(div);
    }

    showTyping() {
        const container = this.window.querySelector('#chat-messages');
        if (!container) return null;
        
        const id = 'typing-' + Date.now();
        const div = document.createElement('div');
        div.id = id;
        div.className = "flex gap-3";
        div.innerHTML = `
            <div class="w-8 h-8 rounded-full bg-cyan-500/20 flex-shrink-0 flex items-center justify-center text-cyan-400 text-xs mt-1">AI</div>
            <div class="bg-[#1e293b] p-3 rounded-2xl rounded-tl-none border border-[#2a3f5f] flex items-center gap-1">
                <span class="w-2 h-2 bg-slate-500 rounded-full animate-bounce"></span>
                <span class="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style="animation-delay: 0.2s"></span>
                <span class="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style="animation-delay: 0.4s"></span>
            </div>
        `;
        container.appendChild(div);
        return id;
    }

    removeMessage(id) {
        if (!id) return;
        const el = this.window.querySelector('#' + id);
        if (el) el.remove();
    }

    scrollToBottom() {
        const container = this.window.querySelector('#chat-messages');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatText(text) {
        // Basic Markdown Support
        let html = this.escapeHtml(text);
        
        // Bold
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="text-cyan-400">$1</strong>');
        
        // Code Block
        html = html.replace(/```([\s\S]*?)```/g, '<pre class="bg-[#0a0f23] p-2 rounded mt-2 text-xs font-mono text-emerald-400 overflow-x-auto"><code>$1</code></pre>');
        
        // Inline Code
        html = html.replace(/`([^`]+)`/g, '<code class="bg-[#0a0f23] px-1 rounded text-xs font-mono text-amber-400">$1</code>');
        
        // Newlines
        html = html.replace(/\n/g, '<br>');

        return html;
    }
}

