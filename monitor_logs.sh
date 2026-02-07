#!/bin/bash
# ROX Quant 日志实时监控脚本

echo "=========================================="
echo "  ROX Quant 日志实时监控"
echo "  按 Ctrl+C 停止监控"
echo "=========================================="
echo ""

# 检查服务是否运行
if lsof -nP -iTCP:7860 -sTCP:LISTEN > /dev/null 2>&1; then
    echo "✓ 服务正在运行"
    PID=$(lsof -nP -iTCP:7860 -sTCP:LISTEN -t)
    echo "  PID: $PID"
else
    echo "✗ 服务未运行"
    exit 1
fi

echo ""
echo "========== 开始监控日志 =========="
echo ""

# 实时监控日志，过滤掉重复的日志
tail -f /tmp/rox_app.log | grep --line-buffered -E "(ERROR|WARNING|✓|✗|INFO.*startup|INFO.*shutdown|Uvicorn)"
