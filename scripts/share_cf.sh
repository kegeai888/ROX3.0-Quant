#!/bin/bash
echo "🚀 启动 Cloudflare Tunnel (推荐，速度更快)..."
echo "---------------------------------------------"
echo "ℹ️  说明: Cloudflare Tunnel 通常比 SSH 隧道更稳定快速。"
echo "⏳ 正在检查环境..."

# 1. 确保服务已启动
if ! pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo "启动本地服务器..."
    ./start_server.sh > /dev/null 2>&1 &
    sleep 5
fi

# 2. 检查 cloudflared
CMD="cloudflared"

if ! command -v cloudflared &> /dev/null; then
    if [ -f "./cloudflared" ]; then
        CMD="./cloudflared"
    else
        echo "❌ 未检测到 cloudflared，正在自动下载..."
        
        ARCH=$(uname -m)
        if [ "$ARCH" = "arm64" ]; then
            URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64.tgz"
        else
            URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64.tgz"
        fi
        
        echo "⬇️  下载中 ($ARCH)..."
        curl -L "$URL" -o cloudflared.tgz
        
        echo "📦 解压中..."
        tar -xzf cloudflared.tgz
        rm cloudflared.tgz
        chmod +x cloudflared
        CMD="./cloudflared"
        echo "✅ 下载完成"
    fi
fi

echo "🌐 正在建立快速隧道..."
echo "---------------------------------------------"
echo "👉 请复制下方输出的 trycloudflare.com 链接："
echo "---------------------------------------------"

# 运行隧道
$CMD tunnel --url http://localhost:8081
