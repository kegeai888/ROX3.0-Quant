#!/bin/bash

# ROX 3.0 仙宫云启动脚本
# 用法: bash start_xiangong.sh

echo "=== ROX 3.0 启动助手 (仙宫云版) ==="

# 1. 检查并启动 Redis
if ! pgrep redis-server > /dev/null; then
    echo "正在启动 Redis..."
    if ! command -v redis-server &> /dev/null; then
        echo "Redis 未安装，尝试安装..."
        apt-get update && apt-get install -y redis-server
    fi
    redis-server --daemonize yes
else
    echo "Redis 已在运行"
fi

# 2. 激活虚拟环境 (如果有)
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 3. 安装依赖 (首次运行或更新后)
if [ "$1" == "--install" ]; then
    echo "正在安装依赖..."
    pip install -r requirements.txt
fi

# 4. 启动后端服务
echo "正在启动后端服务..."
# 注意：仙宫云通常需要监听 0.0.0.0 才能被外部访问
# 端口 8081 需要在控制台设置端口映射
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8081 > rox_server.log 2>&1 &

echo "服务已在后台启动！"
echo "日志查看: tail -f rox_server.log"
echo "请在仙宫云控制台将容器端口 8081 映射到公网端口，然后访问生成的链接。"
