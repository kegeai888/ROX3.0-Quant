#!/bin/bash
echo "🚀 正在启动网页分享模式..."
echo "⚠️  注意：请保持此窗口开启，关闭窗口分享将失效。"

# 1. 确保服务已启动
if ! pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo "启动本地服务器..."
    ./start_server.sh > /dev/null 2>&1 &
    sleep 5
fi

echo "🌐 正在生成公网链接 (Powered by localtunnel)..."
echo "---------------------------------------------"
echo "👉 请将下方的 URL 发送给您的朋友："
echo ""

# Use localtunnel (auto confirm install)
if ! command -v npx &> /dev/null; then
    echo "❌ 错误: 未找到 npx 命令。请确保安装了 Node.js。"
    exit 1
fi

echo "等待服务器就绪..."
sleep 2

# Get Public IP for LocalTunnel password
PUBLIC_IP=$(curl -s ipv4.icanhazip.com)
echo "---------------------------------------------"
echo "🔐 访问密码 (Tunnel Password): $PUBLIC_IP"
echo "👉 请将此 IP 告诉您的朋友，他在打开链接时需要填入这个 IP。"
echo "---------------------------------------------"

# npx -y ensures it doesn't ask for confirmation
npx -y localtunnel --port 8081

# Cleanup on exit
trap "kill $(jobs -p)" EXIT
