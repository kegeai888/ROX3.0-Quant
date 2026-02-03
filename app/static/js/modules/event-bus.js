/**
 * 事件总线 - 管理组件间通信
 * 
 * 功能特性：
 * - 发布订阅模式
 * - 事件命名空间
 * - 一次性事件监听
 * - 事件优先级
 * - 自动清理机制
 */
class EventBus {
    constructor() {
        this.events = new Map();
        this.onceEvents = new Set();
        this.namespaces = new Map();
        this.maxListeners = 50; // 防止内存泄漏
        this.debugMode = false;
    }

    /**
     * 启用调试模式
     * @param {boolean} enabled - 是否启用
     */
    setDebugMode(enabled) {
        this.debugMode = enabled;
    }

    /**
     * 记录调试信息
     * @param {string} message - 调试信息
     * @param {...any} args - 额外参数
     */
    debug(message, ...args) {
        if (this.debugMode) {
            console.log(`[EventBus] ${message}`, ...args);
        }
    }

    /**
     * 订阅事件
     * @param {string} event - 事件名称
     * @param {Function} callback - 回调函数
     * @param {Object} options - 选项
     * @returns {Function} 取消订阅函数
     */
    on(event, callback, options = {}) {
        const { 
            priority = 0, 
            once = false, 
            namespace = null,
            context = null 
        } = options;

        if (typeof callback !== 'function') {
            throw new Error('Callback must be a function');
        }

        // 检查监听器数量限制
        const listeners = this.events.get(event) || [];
        if (listeners.length >= this.maxListeners) {
            console.warn(`[EventBus] Too many listeners for event "${event}". Possible memory leak.`);
        }

        const listener = {
            callback: context ? callback.bind(context) : callback,
            priority,
            once,
            namespace,
            id: Date.now() + Math.random()
        };

        if (!this.events.has(event)) {
            this.events.set(event, []);
        }

        const eventListeners = this.events.get(event);
        
        // 按优先级插入（高优先级在前）
        let insertIndex = eventListeners.length;
        for (let i = 0; i < eventListeners.length; i++) {
            if (eventListeners[i].priority < priority) {
                insertIndex = i;
                break;
            }
        }
        
        eventListeners.splice(insertIndex, 0, listener);

        if (once) {
            this.onceEvents.add(listener.id);
        }

        // 处理命名空间
        if (namespace) {
            if (!this.namespaces.has(namespace)) {
                this.namespaces.set(namespace, new Set());
            }
            this.namespaces.get(namespace).add(listener.id);
        }

        this.debug(`Subscribed to "${event}" with priority ${priority}`, { once, namespace });

        // 返回取消订阅函数
        return () => this.off(event, listener.id);
    }

    /**
     * 订阅一次性事件
     * @param {string} event - 事件名称
     * @param {Function} callback - 回调函数
     * @param {Object} options - 选项
     * @returns {Function} 取消订阅函数
     */
    once(event, callback, options = {}) {
        return this.on(event, callback, { ...options, once: true });
    }

    /**
     * 取消订阅
     * @param {string} event - 事件名称
     * @param {string|Function} listenerOrId - 监听器ID或回调函数
     */
    off(event, listenerOrId = null) {
        if (!this.events.has(event)) {
            return;
        }

        const listeners = this.events.get(event);

        if (listenerOrId === null) {
            // 移除所有监听器
            listeners.forEach(listener => {
                this.onceEvents.delete(listener.id);
                if (listener.namespace) {
                    const nsListeners = this.namespaces.get(listener.namespace);
                    if (nsListeners) {
                        nsListeners.delete(listener.id);
                    }
                }
            });
            this.events.delete(event);
            this.debug(`Removed all listeners for "${event}"`);
        } else if (typeof listenerOrId === 'string') {
            // 通过ID移除
            const index = listeners.findIndex(l => l.id === listenerOrId);
            if (index !== -1) {
                const listener = listeners[index];
                listeners.splice(index, 1);
                this.onceEvents.delete(listener.id);
                
                if (listener.namespace) {
                    const nsListeners = this.namespaces.get(listener.namespace);
                    if (nsListeners) {
                        nsListeners.delete(listener.id);
                    }
                }
                
                this.debug(`Removed listener ${listenerOrId} for "${event}"`);
            }
        } else if (typeof listenerOrId === 'function') {
            // 通过回调函数移除
            const index = listeners.findIndex(l => l.callback === listenerOrId);
            if (index !== -1) {
                const listener = listeners[index];
                listeners.splice(index, 1);
                this.onceEvents.delete(listener.id);
                
                if (listener.namespace) {
                    const nsListeners = this.namespaces.get(listener.namespace);
                    if (nsListeners) {
                        nsListeners.delete(listener.id);
                    }
                }
                
                this.debug(`Removed callback listener for "${event}"`);
            }
        }

        // 如果没有监听器了，删除事件
        if (listeners.length === 0) {
            this.events.delete(event);
        }
    }

    /**
     * 发布事件
     * @param {string} event - 事件名称
     * @param {...any} args - 事件参数
     * @returns {boolean} 是否有监听器处理了事件
     */
    emit(event, ...args) {
        if (!this.events.has(event)) {
            this.debug(`No listeners for "${event}"`);
            return false;
        }

        const listeners = this.events.get(event).slice(); // 复制数组避免修改问题
        const toRemove = [];

        this.debug(`Emitting "${event}" to ${listeners.length} listeners`, args);

        let handled = false;
        for (const listener of listeners) {
            try {
                const result = listener.callback(...args);
                handled = true;

                // 处理Promise返回值
                if (result instanceof Promise) {
                    result.catch(error => {
                        console.error(`[EventBus] Async listener error for "${event}":`, error);
                    });
                }

                // 标记一次性监听器待移除
                if (listener.once) {
                    toRemove.push(listener.id);
                }
            } catch (error) {
                console.error(`[EventBus] Listener error for "${event}":`, error);
            }
        }

        // 移除一次性监听器
        toRemove.forEach(id => this.off(event, id));

        return handled;
    }

    /**
     * 异步发布事件
     * @param {string} event - 事件名称
     * @param {...any} args - 事件参数
     * @returns {Promise<boolean>} 是否有监听器处理了事件
     */
    async emitAsync(event, ...args) {
        if (!this.events.has(event)) {
            this.debug(`No listeners for "${event}"`);
            return false;
        }

        const listeners = this.events.get(event).slice();
        const toRemove = [];

        this.debug(`Async emitting "${event}" to ${listeners.length} listeners`, args);

        let handled = false;
        for (const listener of listeners) {
            try {
                const result = listener.callback(...args);
                handled = true;

                // 等待Promise完成
                if (result instanceof Promise) {
                    await result;
                }

                if (listener.once) {
                    toRemove.push(listener.id);
                }
            } catch (error) {
                console.error(`[EventBus] Async listener error for "${event}":`, error);
            }
        }

        // 移除一次性监听器
        toRemove.forEach(id => this.off(event, id));

        return handled;
    }

    /**
     * 移除命名空间下的所有监听器
     * @param {string} namespace - 命名空间
     */
    offNamespace(namespace) {
        const nsListeners = this.namespaces.get(namespace);
        if (!nsListeners) {
            return;
        }

        // 收集需要清理的事件
        const eventsToClean = new Set();
        
        for (const [event, listeners] of this.events) {
            for (let i = listeners.length - 1; i >= 0; i--) {
                const listener = listeners[i];
                if (nsListeners.has(listener.id)) {
                    listeners.splice(i, 1);
                    this.onceEvents.delete(listener.id);
                    eventsToClean.add(event);
                }
            }
        }

        // 清理空的事件
        for (const event of eventsToClean) {
            const listeners = this.events.get(event);
            if (listeners && listeners.length === 0) {
                this.events.delete(event);
            }
        }

        this.namespaces.delete(namespace);
        this.debug(`Removed namespace "${namespace}"`);
    }

    /**
     * 获取事件监听器数量
     * @param {string} event - 事件名称
     * @returns {number} 监听器数量
     */
    listenerCount(event) {
        const listeners = this.events.get(event);
        return listeners ? listeners.length : 0;
    }

    /**
     * 获取所有事件名称
     * @returns {Array<string>} 事件名称数组
     */
    eventNames() {
        return Array.from(this.events.keys());
    }

    /**
     * 清除所有监听器
     */
    clear() {
        this.events.clear();
        this.onceEvents.clear();
        this.namespaces.clear();
        this.debug('Cleared all listeners');
    }

    /**
     * 获取统计信息
     * @returns {Object} 统计信息
     */
    getStats() {
        const totalListeners = Array.from(this.events.values())
            .reduce((sum, listeners) => sum + listeners.length, 0);

        return {
            totalEvents: this.events.size,
            totalListeners,
            onceListeners: this.onceEvents.size,
            namespaces: this.namespaces.size,
            events: Object.fromEntries(
                Array.from(this.events.entries()).map(([event, listeners]) => [
                    event,
                    listeners.length
                ])
            )
        };
    }

    /**
     * 设置最大监听器数量
     * @param {number} max - 最大数量
     */
    setMaxListeners(max) {
        this.maxListeners = max;
    }
}

// 创建全局事件总线实例
window.eventBus = new EventBus();

// 开发环境下启用调试模式
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    window.eventBus.setDebugMode(true);
}

// 页面卸载时清理所有监听器
window.addEventListener('beforeunload', () => {
    if (window.eventBus) {
        window.eventBus.clear();
    }
});

// 导出一些常用的事件名称常量
window.EventBus = {
    Events: {
        // 数据相关
        DATA_LOADED: 'data:loaded',
        DATA_ERROR: 'data:error',
        DATA_UPDATED: 'data:updated',
        
        // UI相关
        MODE_CHANGED: 'ui:mode-changed',
        LOADING_STATE_CHANGED: 'ui:loading-changed',
        TOAST_SHOW: 'ui:toast-show',
        
        // 股票相关
        STOCK_SELECTED: 'stock:selected',
        STOCK_ANALYZED: 'stock:analyzed',
        WATCHLIST_UPDATED: 'stock:watchlist-updated',
        
        // 交易相关
        TRADE_EXECUTED: 'trade:executed',
        POSITION_UPDATED: 'trade:position-updated',
        
        // 图表相关
        CHART_CREATED: 'chart:created',
        CHART_UPDATED: 'chart:updated',
        CHART_DESTROYED: 'chart:destroyed',
        
        // WebSocket相关
        WS_CONNECTED: 'ws:connected',
        WS_DISCONNECTED: 'ws:disconnected',
        WS_MESSAGE: 'ws:message'
    }
};

console.log('[EventBus] Initialized successfully');