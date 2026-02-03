/**
 * 组件管理器 - 管理页面组件生命周期
 * 
 * 功能特性：
 * - 组件注册和生命周期管理
 * - 自动资源清理
 * - 组件间依赖管理
 * - 懒加载支持
 * - 错误边界处理
 */
class ComponentManager {
    constructor() {
        this.components = new Map();
        this.activeComponents = new Set();
        this.componentDependencies = new Map();
        this.errorBoundaries = new Map();
        this.loadingStates = new Map();
        
        // 绑定方法
        this.handleError = this.handleError.bind(this);
        
        // 设置全局错误处理
        this.setupGlobalErrorHandling();
    }

    /**
     * 注册组件
     * @param {string} name - 组件名称
     * @param {Object} component - 组件定义
     */
    register(name, component) {
        if (this.components.has(name)) {
            console.warn(`[ComponentManager] Component "${name}" already registered`);
            return;
        }

        const componentDef = {
            name,
            init: component.init || (() => {}),
            destroy: component.destroy || (() => {}),
            update: component.update || (() => {}),
            dependencies: component.dependencies || [],
            lazy: component.lazy || false,
            errorBoundary: component.errorBoundary || false,
            ...component
        };

        this.components.set(name, componentDef);
        
        // 处理依赖关系
        if (componentDef.dependencies.length > 0) {
            this.componentDependencies.set(name, componentDef.dependencies);
        }

        console.log(`[ComponentManager] Registered component "${name}"`);
    }

    /**
     * 初始化组件
     * @param {string} name - 组件名称
     * @param {Object} options - 初始化选项
     * @returns {Promise<boolean>} 是否成功初始化
     */
    async init(name, options = {}) {
        const component = this.components.get(name);
        if (!component) {
            console.error(`[ComponentManager] Component "${name}" not found`);
            return false;
        }

        if (this.activeComponents.has(name)) {
            console.warn(`[ComponentManager] Component "${name}" already active`);
            return true;
        }

        try {
            this.setLoading(name, true);

            // 检查并初始化依赖
            const dependencies = this.componentDependencies.get(name) || [];
            for (const dep of dependencies) {
                if (!this.activeComponents.has(dep)) {
                    console.log(`[ComponentManager] Initializing dependency "${dep}" for "${name}"`);
                    const success = await this.init(dep);
                    if (!success) {
                        throw new Error(`Failed to initialize dependency "${dep}"`);
                    }
                }
            }

            // 初始化组件
            const result = await this.safeExecute(name, 'init', component.init, options);
            
            if (result.success) {
                this.activeComponents.add(name);
                console.log(`[ComponentManager] Initialized component "${name}"`);
                
                // 触发初始化事件
                if (window.eventBus) {
                    window.eventBus.emit('component:initialized', { name, options });
                }
                
                return true;
            } else {
                throw result.error;
            }
        } catch (error) {
            console.error(`[ComponentManager] Failed to initialize component "${name}":`, error);
            this.handleError(name, 'init', error);
            return false;
        } finally {
            this.setLoading(name, false);
        }
    }

    /**
     * 销毁组件
     * @param {string} name - 组件名称
     * @returns {Promise<boolean>} 是否成功销毁
     */
    async destroy(name) {
        const component = this.components.get(name);
        if (!component) {
            console.error(`[ComponentManager] Component "${name}" not found`);
            return false;
        }

        if (!this.activeComponents.has(name)) {
            console.warn(`[ComponentManager] Component "${name}" not active`);
            return true;
        }

        try {
            // 检查是否有其他组件依赖此组件
            const dependents = this.findDependents(name);
            if (dependents.length > 0) {
                console.log(`[ComponentManager] Destroying dependents of "${name}":`, dependents);
                for (const dependent of dependents) {
                    await this.destroy(dependent);
                }
            }

            // 销毁组件
            const result = await this.safeExecute(name, 'destroy', component.destroy);
            
            if (result.success) {
                this.activeComponents.delete(name);
                console.log(`[ComponentManager] Destroyed component "${name}"`);
                
                // 触发销毁事件
                if (window.eventBus) {
                    window.eventBus.emit('component:destroyed', { name });
                }
                
                return true;
            } else {
                throw result.error;
            }
        } catch (error) {
            console.error(`[ComponentManager] Failed to destroy component "${name}":`, error);
            this.handleError(name, 'destroy', error);
            return false;
        }
    }

    /**
     * 更新组件
     * @param {string} name - 组件名称
     * @param {Object} data - 更新数据
     * @returns {Promise<boolean>} 是否成功更新
     */
    async update(name, data = {}) {
        const component = this.components.get(name);
        if (!component) {
            console.error(`[ComponentManager] Component "${name}" not found`);
            return false;
        }

        if (!this.activeComponents.has(name)) {
            console.warn(`[ComponentManager] Component "${name}" not active`);
            return false;
        }

        try {
            const result = await this.safeExecute(name, 'update', component.update, data);
            
            if (result.success) {
                // 触发更新事件
                if (window.eventBus) {
                    window.eventBus.emit('component:updated', { name, data });
                }
                
                return true;
            } else {
                throw result.error;
            }
        } catch (error) {
            console.error(`[ComponentManager] Failed to update component "${name}":`, error);
            this.handleError(name, 'update', error);
            return false;
        }
    }

    /**
     * 安全执行组件方法
     * @param {string} name - 组件名称
     * @param {string} method - 方法名
     * @param {Function} fn - 要执行的函数
     * @param {...any} args - 参数
     * @returns {Promise<Object>} 执行结果
     */
    async safeExecute(name, method, fn, ...args) {
        try {
            const result = await fn(...args);
            return { success: true, result };
        } catch (error) {
            // 检查是否有错误边界
            const errorBoundary = this.errorBoundaries.get(name);
            if (errorBoundary) {
                try {
                    await errorBoundary(error, method, ...args);
                    return { success: true, result: null };
                } catch (boundaryError) {
                    return { success: false, error: boundaryError };
                }
            }
            
            return { success: false, error };
        }
    }

    /**
     * 查找依赖某个组件的其他组件
     * @param {string} name - 组件名称
     * @returns {Array<string>} 依赖组件列表
     */
    findDependents(name) {
        const dependents = [];
        
        for (const [componentName, dependencies] of this.componentDependencies) {
            if (dependencies.includes(name) && this.activeComponents.has(componentName)) {
                dependents.push(componentName);
            }
        }
        
        return dependents;
    }

    /**
     * 设置组件加载状态
     * @param {string} name - 组件名称
     * @param {boolean} loading - 是否加载中
     */
    setLoading(name, loading) {
        this.loadingStates.set(name, loading);
        
        // 触发加载状态变化事件
        if (window.eventBus) {
            window.eventBus.emit('component:loading-changed', { name, loading });
        }
    }

    /**
     * 获取组件加载状态
     * @param {string} name - 组件名称
     * @returns {boolean} 是否加载中
     */
    isLoading(name) {
        return this.loadingStates.get(name) || false;
    }

    /**
     * 检查组件是否活跃
     * @param {string} name - 组件名称
     * @returns {boolean} 是否活跃
     */
    isActive(name) {
        return this.activeComponents.has(name);
    }

    /**
     * 批量初始化组件
     * @param {Array<string>} names - 组件名称数组
     * @param {Object} options - 初始化选项
     * @returns {Promise<Object>} 初始化结果
     */
    async batchInit(names, options = {}) {
        const results = {};
        const errors = [];

        for (const name of names) {
            try {
                results[name] = await this.init(name, options);
            } catch (error) {
                errors.push({ name, error });
                results[name] = false;
            }
        }

        return { results, errors };
    }

    /**
     * 批量销毁组件
     * @param {Array<string>} names - 组件名称数组
     * @returns {Promise<Object>} 销毁结果
     */
    async batchDestroy(names) {
        const results = {};
        const errors = [];

        for (const name of names) {
            try {
                results[name] = await this.destroy(name);
            } catch (error) {
                errors.push({ name, error });
                results[name] = false;
            }
        }

        return { results, errors };
    }

    /**
     * 设置错误边界
     * @param {string} name - 组件名称
     * @param {Function} handler - 错误处理函数
     */
    setErrorBoundary(name, handler) {
        this.errorBoundaries.set(name, handler);
    }

    /**
     * 处理组件错误
     * @param {string} name - 组件名称
     * @param {string} method - 出错的方法
     * @param {Error} error - 错误对象
     */
    handleError(name, method, error) {
        console.error(`[ComponentManager] Component "${name}" error in "${method}":`, error);
        
        // 触发错误事件
        if (window.eventBus) {
            window.eventBus.emit('component:error', { name, method, error });
        }

        // 如果是关键错误，可能需要重新初始化组件
        if (method === 'init' || method === 'destroy') {
            this.activeComponents.delete(name);
        }
    }

    /**
     * 设置全局错误处理
     */
    setupGlobalErrorHandling() {
        // 捕获未处理的Promise拒绝
        window.addEventListener('unhandledrejection', (event) => {
            console.error('[ComponentManager] Unhandled promise rejection:', event.reason);
            
            // 尝试恢复
            this.attemptRecovery(event.reason);
        });

        // 捕获全局错误
        window.addEventListener('error', (event) => {
            console.error(`[ComponentManager] Global error in ${event.filename}:${event.lineno}:${event.colno}`, event.error);
            
            // 尝试恢复
            this.attemptRecovery(event.error);
        });
    }

    /**
     * 尝试错误恢复
     * @param {Error} error - 错误对象
     */
    attemptRecovery(error) {
        // 简单的恢复策略：重新初始化失败的组件
        // 在实际应用中，可以根据错误类型实施更复杂的恢复策略
        
        if (window.eventBus) {
            window.eventBus.emit('system:error-recovery', { error });
        }
    }

    /**
     * 获取组件统计信息
     * @returns {Object} 统计信息
     */
    getStats() {
        return {
            totalComponents: this.components.size,
            activeComponents: this.activeComponents.size,
            loadingComponents: Array.from(this.loadingStates.entries())
                .filter(([, loading]) => loading).length,
            componentList: Array.from(this.components.keys()),
            activeList: Array.from(this.activeComponents),
            dependencies: Object.fromEntries(this.componentDependencies)
        };
    }

    /**
     * 销毁所有组件
     * @returns {Promise<void>}
     */
    async destroyAll() {
        const activeComponents = Array.from(this.activeComponents);
        console.log(`[ComponentManager] Destroying ${activeComponents.length} active components`);
        
        // 按依赖关系逆序销毁
        const sortedComponents = this.topologicalSort(activeComponents).reverse();
        
        for (const name of sortedComponents) {
            await this.destroy(name);
        }
        
        // 清理状态
        this.activeComponents.clear();
        this.loadingStates.clear();
        this.errorBoundaries.clear();
    }

    /**
     * 拓扑排序（处理依赖关系）
     * @param {Array<string>} components - 组件列表
     * @returns {Array<string>} 排序后的组件列表
     */
    topologicalSort(components) {
        const visited = new Set();
        const result = [];
        
        const visit = (name) => {
            if (visited.has(name)) return;
            visited.add(name);
            
            const dependencies = this.componentDependencies.get(name) || [];
            for (const dep of dependencies) {
                if (components.includes(dep)) {
                    visit(dep);
                }
            }
            
            result.push(name);
        };
        
        for (const name of components) {
            visit(name);
        }
        
        return result;
    }
}

// 创建全局组件管理器实例
window.componentManager = new ComponentManager();

// 页面卸载时销毁所有组件
window.addEventListener('beforeunload', async () => {
    if (window.componentManager) {
        await window.componentManager.destroyAll();
    }
});

// 注册一些基础组件
window.componentManager.register('chartManager', {
    init: () => {
        if (!window.chartManager) {
            console.error('ChartManager not available');
            return false;
        }
        return true;
    },
    destroy: () => {
        if (window.chartManager) {
            window.chartManager.disposeAll();
        }
    }
});
