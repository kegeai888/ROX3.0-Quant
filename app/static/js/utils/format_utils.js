/**
 * ROX Data Formatting Utilities
 * Handles consistent number formatting (Wan/Yi), colors, and time.
 */

const FormatUtils = {
    /**
     * Format a large number with units (万/亿)
     * @param {number} value - The number to format
     * @param {number} decimals - Decimal places (default 2)
     * @returns {string} Formatted string
     */
    formatBigNumber(value, decimals = 2) {
        if (value == null || isNaN(value)) return '--';
        const absVal = Math.abs(value);
        if (absVal >= 100000000) {
            return (value / 100000000).toFixed(decimals) + '亿';
        } else if (absVal >= 10000) {
            return (value / 10000).toFixed(decimals) + '万';
        }
        return value.toFixed(decimals);
    },

    /**
     * Format price with consistent precision
     * @param {number} price 
     * @returns {string}
     */
    formatPrice(price) {
        if (price == null || isNaN(price)) return '--';
        // Future: Detect if it's ETF (3 decimals) or Stock (2 decimals)
        // For now, default to 2
        return Number(price).toFixed(2);
    },

    /**
     * Get color class for value (Red up, Green down)
     * @param {number} value 
     * @returns {string} Tailwind class name
     */
    getColorClass(value) {
        const v = Number(value);
        if (isNaN(v) || v === 0) return 'text-slate-200';
        return v > 0 ? 'text-rose-500' : 'text-emerald-500'; // CN Market: Red=Up
    },
    
    /**
     * Format percentage with sign
     * @param {number} pct 
     * @returns {string} e.g. "+1.23%"
     */
    formatPct(pct) {
        if (pct == null || isNaN(pct)) return '--';
        const p = Number(pct);
        const sign = p > 0 ? '+' : '';
        return `${sign}${p.toFixed(2)}%`;
    }
};

// Export globally
window.FormatUtils = FormatUtils;
