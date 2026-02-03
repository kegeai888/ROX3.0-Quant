/**
 * 缓存管理器 - 智能数据缓存系统
 * 
 * 功能特性：
 * - 多级缓存（内存、本地存储）
 * - LRU淘汰策略
 * - 过期时间管理
 * - 缓存统计和监控
 * - 自动清理机制
 */
class CacheManager {
    constructor(options = {}) {
        this.maxMemorySize = options.maxMemorySize || 50; // 最大内存缓存条目数
        this.maxStorageSize = options.maxStorageSize || 100; // 最大本地存储缓存条目数
        this.defaultTTL = options.defaultTTL || 5 * 60 * 1000; // 默认5分钟过期
        this.cleanupInterval = options.cleanupInterval || 60 * 1000; // 清理间隔1分钟
        
        // 内存缓存
        this.memoryCache = new Map();
        this.accessOrder = new Map(); // LRU访问顺序
        
        // 统计信息
        this.stats = {
            hits: 0,
            misses: 0,
            sets: 0,
            deletes: 0,
            cleanups: 0
        };
        
        // 启动定期清理
        this.startCleanupTimer();
        
        // 监听存储变化
        this.initStorageListener();
    }

    /**
     * 生成缓存键
     * @param {string} namespace - 命名空间
     * @param {string} key - 键名
     * @returns {string} 完整的缓存键
     */
    generateKey(namespace, key) {
        return `rox_cache_${namespace}_${key}`;
    }

    /**
     * 设置缓存
     * @param {string} namespace - 命名空间
     * @param {string} key - 键名
     * @param {any} value - 值
     * @param {Object} options - 选项
     */
    set(namespace, key, value, options = {}) {
        const {
            ttl = this.defaultTTL,
            persistent = false,
            priority = 1
        } = options;

        const cacheKey = this.generateKey(namespace, key);
        const now = Date.now();
        
        const cacheItem = {
            value,
            timestamp: now,
            ttl,
            priority,
            accessCount: 0,
            lastAccess: now
        };

        // 内存缓存
        this.memoryCache.set(cacheKey, cacheItem);
        this.accessOrder.set(cacheKey, now);
        
        // 检查内存缓存大小限制
        this.enforceMemoryLimit();

        // 持久化缓存
        if (persistent) {
            try {
                const storageItem = {
                    ...cacheItem,
                    persistent: true
                };
                localStorage.setItem(cacheKey, JSON.stringify(storageItem));
                this.enforceStorageLimit();
            } catch (error) {
                console.warn('[CacheManager] Failed to set persistent cache:', error);
            }
        }

        this.stats.sets++;
        
        // 触发缓存设置事件
        if (window.eventBus) {
            window.eventBus.emit('cache:set', { namespace, key, persistent });
        }
    }

    /**
     * 获取缓存
     * @param {string} namespace - 命名空间
     * @param {string} key - 键名
     * @returns {any|null} 缓存值或null
     */
    get(namespace, key) {
        const cacheKey = this.generateKey(namespace, key);
        const now = Date.now();

        // 先检查内存缓存
        let cacheItem = this.memoryCache.get(cacheKey);
        
        if (cacheItem) {
            // 检查是否过期
            if (now - cacheItem.timestamp > cacheItem.ttl) {
                this.memoryCache.delete(cacheKey);
                this.accessOrder.delete(cacheKey);
                cacheItem = null;
            } else {
                // 更新访问信息
                cacheItem.accessCount++;
                cacheItem.lastAccess = now;
                this.accessOrder.set(cacheKey, now);
                this.stats.hits++;
                return cacheItem.value;
            }
        }

        // 检查持久化缓存
        if (!cacheItem) {
            try {
                const stored = localStorage.getItem(cacheKey);
                if (stored) {
                    const storageItem = JSON.parse(stored);
                    
                    // 检查是否过期
                    if (now - storageItem.timestamp <= storageItem.ttl) {
                        // 恢复到内存缓存
                        storageItem.accessCount++;
                        storageItem.lastAccess = now;
                        this.memoryCache.set(cacheKey, storageItem);
                        this.accessOrder.set(cacheKey, now);
                        this.stats.hits++;
                        return storageItem.value;
                    } else {
                        // 过期，删除
                        localStorage.removeItem(cacheKey);
                    }
                }
            } catch (error) {
                console.warn('[CacheManager] Failed to get persistent cache:', error);
            }
        }

        this.stats.misses++;
        return null;
    }

    /**
     * 删除缓存
     * @param {string} namespace - 命名空间
     * @param {string} key - 键名（可选，不提供则删除整个命名空间）
     */
    delete(namespace, key = null) {
        if (key) {
            const cacheKey = this.generateKey(namespace, key);
            this.memoryCache.delete(cacheKey);
            this.accessOrder.delete(cacheKey);
            
            try {
                localStorage.removeItem(cacheKey);
            } catch (error) {
                console.warn('[CacheManager] Failed to remove persistent cache:', error);
            }
            
            this.stats.deletes++;
        } else {
            // 删除整个命名空间
            const prefix = `rox_cache_${namespace}_`;
            
            // 删除内存缓存
            for (const [cacheKey] of this.memoryCache) {
                if (cacheKey.startsWith(prefix)) {
                    this.memoryCache.delete(cacheKey);
                    this.accessOrder.delete(cacheKey);
                    this.stats.deletes++;
                }
            }
            
            // 删除持久化缓存
            try {
                const keysToRemove = [];
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    if (key && key.startsWith(prefix)) {
                        keysToRemove.push(key);
                    }
                }
                keysToRemove.forEach(key => localStorage.removeItem(key));
            } catch (error) {
                console.warn('[CacheManager] Failed to clear namespace from storage:', error);
            }
        }

        // 触发缓存删除事件
        if (window.eventBus) {
            window.eventBus.emit('cache:delete', { namespace, key });
        }
    }

    /**
     * 检查缓存是否存在且未过期
     * @param {string} namespace - 命名空间
     * @param {string} key - 键名
     * @returns {boolean} 是否存在
     */
    has(namespace, key) {
        return this.get(namespace, key) !== null;
    }

    /**
     * 获取或设置缓存（如果不存在则通过工厂函数创建）
     * @param {string} namespace - 命名空间
     * @param {string} key - 键名
     * @param {Function} factory - 工厂函数
     * @param {Object} options - 选项
     * @returns {Promise<any>} 缓存值
     */
    async getOrSet(namespace, key, factory, options = {}) {
        let value = this.get(namespace, key);
        
        if (value === null) {
            try {
                value = await factory();
                this.set(namespace, key, value, options);
            } catch (error) {
                console.error('[CacheManager] Factory function failed:', error);
                throw error;
            }
        }
        
        return value;
    }

    /**
     * 强制执行内存缓存大小限制
     */
    enforceMemoryLimit() {
        while (this.memoryCache.size > this.maxMemorySize) {
            // 找到最久未访问的项目
            let oldestKey = null;
            let oldestTime = Date.now();
            
            for (const [key, time] of this.accessOrder) {
                if (time < oldestTime) {
                    oldestTime = time;
                    oldestKey = key;
                }
            }
            
            if (oldestKey) {
                this.memoryCache.delete(oldestKey);
                this.accessOrder.delete(oldestKey);
            } else {
                break; // 防止无限循环
            }
        }
    }

    /**
     * 强制执行存储缓存大小限制
     */
    enforceStorageLimit() {
        try {
            const cacheKeys = [];
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.startsWith('rox_cache_')) {
                    const item = JSON.parse(localStorage.getItem(key));
                    cacheKeys.push({
                        key,
                        timestamp: item.timestamp,
                        priority: item.priority || 1
                    });
                }
            }
            
            if (cacheKeys.length > this.maxStorageSize) {
                // 按优先级和时间排序，删除优先级低且时间久的项目
                cacheKeys.sort((a, b) => {
                    if (a.priority !== b.priority) {
                        return a.priority - b.priority; // 优先级低的在前
                    }
                    return a.timestamp - b.timestamp; // 时间久的在前
                });
                
                const toRemove = cacheKeys.slice(0, cacheKeys.length - this.maxStorageSize);
                toRemove.forEach(item => localStorage.removeItem(item.key));
            }
        } catch (error) {
            console.warn('[CacheManager] Failed to enforce storage limit:', error);
        }
    }

    /**
     * 清理过期缓存
     */
    cleanup() {
        const now = Date.now();
        let cleaned = 0;

        // 清理内存缓存
        for (const [key, item] of this.memoryCache) {
            if (now - item.timestamp > item.ttl) {
                this.memoryCache.delete(key);
                this.accessOrder.delete(key);
                cleaned++;
            }
        }

        // 清理持久化缓存
        try {
            const keysToRemove = [];
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.startsWith('rox_cache_')) {
                    const item = JSON.parse(localStorage.getItem(key));
                    if (now - item.timestamp > item.ttl) {
                        keysToRemove.push(key);
                    }
                }
            }
            keysToRemove.forEach(key => localStorage.removeItem(key));
            cleaned += keysToRemove.length;
        } catch (error) {
            console.warn('[CacheManager] Failed to cleanup storage cache:', error);
        }

        this.stats.cleanups++;
        
        if (cleaned > 0) {
            console.log(`[CacheManager] Cleaned up ${cleaned} expired cache items`);
        }

        return cleaned;
    }

    /**
     * 启动清理定时器
     */
    startCleanupTimer() {
        this.cleanupTimer = setInterval(() => {
            this.cleanup();
        }, this.cleanupInterval);
    }

    /**
     * 停止清理定时器
     */
    stopCleanupTimer() {
        if (this.cleanupTimer) {
            clearInterval(this.cleanupTimer);
            this.cleanupTimer = null;
        }
    }

    /**
     * 初始化存储监听器
     */
    initStorageListener() {
        window.addEventListener('storage', (event) => {
            if (event.key && event.key.startsWith('rox_cache_')) {
                // 存储发生变化，可能需要同步内存缓存
                if (event.newValue === null) {
                    // 项目被删除
                    this.memoryCache.delete(event.key);
                    this.accessOrder.delete(event.key);
                }
            }
        });
    }

    /**
     * 获取缓存统计信息
     * @returns {Object} 统计信息
     */
    getStats() {
        const hitRate = this.stats.hits + this.stats.misses > 0 
            ? (this.stats.hits / (this.stats.hits + this.stats.misses) * 100).toFixed(2)
            : 0;

        return {
            ...this.stats,
            hitRate: `${hitRate}%`,
            memorySize: this.memoryCache.size,
            storageSize: this.getStorageSize()
        };
    }

    /**
     * 获取存储缓存大小
     * @returns {number} 存储缓存项目数
     */
    getStorageSize() {
        try {
            let count = 0;
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.startsWith('rox_cache_')) {
                    count++;
                }
            }
            return count;
        } catch (error) {
            return 0;
        }
    }

    /**
     * 清空所有缓存
     */
    clear() {
        // 清空内存缓存
        this.memoryCache.clear();
        this.accessOrder.clear();

        // 清空持久化缓存
        try {
            const keysToRemove = [];
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.startsWith('rox_cache_')) {
                    keysToRemove.push(key);
                }
            }
            keysToRemove.forEach(key => localStorage.removeItem(key));
        } catch (error) {
            console.warn('[CacheManager] Failed to clear storage cache:', error);
        }

        // 重置统计
        this.stats = {
            hits: 0,
            misses: 0,
            sets: 0,
            deletes: 0,
            cleanups: 0
        };

        console.log('[CacheManager] All caches cleared');
    }

    /**
     * 销毁缓存管理器
     */
    destroy() {
        this.stopCleanupTimer();
        this.clear();
    }
}

// 创建全局缓存管理器实例
window.cacheManager = new CacheManager({
    maxMemorySize: 100,
    maxStorageSize: 200,
    defaultTTL: 5 * 60 * 1000, // 5分钟
    cleanupInterval: 2 * 60 * 1000 // 2分钟清理一次
});

// 页面卸载时清理
window.addEventListener('beforeunload', () => {
    if (window.cacheManager) {
        window.cacheManager.destroy();
    }
});

// 导出缓存命名空间常量
window.CacheNamespaces = {
    MARKET_DATA: 'market',
    STOCK_DATA: 'stock',
    USER_DATA: 'user',
    CHART_DATA: 'chart',
    API_RESPONSE: 'api',
    ANALYSIS_RESULT: 'analysis'
};

console.log('[CacheManager] Initialized successfully');