#!/bin/bash
echo "🚀 启动极速分享模式 (SSH Tunnel)..."
echo "---------------------------------------------"
echo "ℹ️  说明: 此模式使用 SSH 隧道，通常比 LocalTunnel 更快更稳定。"
echo "⏳ 正在连接节点..."

# 1. 确保服务已启动
if ! pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo "启动本地服务器..."
    ./start_server.sh > /dev/null 2>&1 &
    sleep 5
fi

echo "---------------------------------------------"
echo "✅ 连接成功！请复制下方终端输出的 https 链接："
echo "   (例如: https://xxxxxx.lhr.life)"
echo "---------------------------------------------"

# Use localhost.run (no install needed, usually faster)
# -o StrictHostKeyChecking=no avoids the "Are you sure..." prompt
ssh -o StrictHostKeyChecking=no -R 80:localhost:8081 nokey@localhost.run
