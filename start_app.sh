#!/bin/bash
#==============================================================================
# ROX Quant 3.0 启动脚本
# 端口: 7860 | 外网访问: 支持
#==============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PORT=7860
HOST="0.0.0.0"
CONDA_ENV="py312"

echo -e "${BLUE}=========================================="
echo "  ROX Quant 3.0 启动脚本"
echo "  端口: ${PORT} | 外网访问: 支持"
echo -e "==========================================${NC}\n"

# 1. 获取项目目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || { echo -e "${RED}✗ 无法进入项目目录${NC}"; exit 1; }
echo -e "${GREEN}✓${NC} 项目目录: ${SCRIPT_DIR}"

# 2. 检查 conda 是否可用
if ! command -v conda &> /dev/null; then
    echo -e "${RED}✗ conda 未找到，请先安装 Miniconda/Anaconda${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} conda 已安装"

# 3. 初始化 conda（支持 bash/zsh）
CONDA_BASE=$(conda info --base)
if [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
    source "$CONDA_BASE/etc/profile.d/conda.sh"
else
    echo -e "${RED}✗ 无法初始化 conda${NC}"
    exit 1
fi

# 4. 检查并激活 py312 环境
if ! conda env list | grep -q "^${CONDA_ENV} "; then
    echo -e "${YELLOW}⚠ ${CONDA_ENV} 环境不存在，正在创建...${NC}"
    conda create -n ${CONDA_ENV} python=3.12 -y
    echo -e "${GREEN}✓${NC} ${CONDA_ENV} 环境创建完成"
fi

conda activate ${CONDA_ENV}
echo -e "${GREEN}✓${NC} 已激活环境: ${CONDA_ENV} (Python $(python --version 2>&1 | awk '{print $2}'))"

# 5. 检查依赖是否安装
if ! python -c "import fastapi" &> /dev/null; then
    echo -e "${YELLOW}⚠ 依赖未安装，正在安装 requirements.txt...${NC}"
    pip install -r requirements.txt -q
    echo -e "${GREEN}✓${NC} 依赖安装完成"
else
    echo -e "${GREEN}✓${NC} 依赖已安装"
fi

# 6. 检测端口占用并优雅释放
echo -e "\n${BLUE}[端口检测]${NC} 检查端口 ${PORT}..."
PIDS=$(lsof -nP -iTCP:${PORT} -sTCP:LISTEN -t 2>/dev/null || true)

if [ -n "$PIDS" ]; then
    echo -e "${YELLOW}⚠ 端口 ${PORT} 被占用 (PID: ${PIDS})${NC}"
    echo -e "${YELLOW}  正在优雅终止进程...${NC}"

    # 第一步：发送 SIGTERM（优雅终止）
    for pid in $PIDS; do
        kill -TERM $pid 2>/dev/null || true
    done

    # 等待进程退出
    sleep 2

    # 第二步：检查是否还存在，强制 SIGKILL
    PIDS_REMAIN=$(lsof -nP -iTCP:${PORT} -sTCP:LISTEN -t 2>/dev/null || true)
    if [ -n "$PIDS_REMAIN" ]; then
        echo -e "${YELLOW}  进程未响应，强制终止...${NC}"
        for pid in $PIDS_REMAIN; do
            kill -KILL $pid 2>/dev/null || true
        done
        sleep 1
    fi

    echo -e "${GREEN}✓${NC} 端口 ${PORT} 已释放"
else
    echo -e "${GREEN}✓${NC} 端口 ${PORT} 可用"
fi

# 再次确认端口已释放
sleep 2

# 7. 设置环境变量
export DESKTOP_HOST="${HOST}"
export DESKTOP_PORT="${PORT}"
export ENVIRONMENT="production"

# 8. 启动应用
echo -e "\n${BLUE}=========================================="
echo "  启动 ROX Quant 3.0"
echo -e "==========================================${NC}"
echo -e "${GREEN}访问地址:${NC}"
echo -e "  • 经典版: ${BLUE}http://${HOST}:${PORT}${NC}"
echo -e "  • 专业版: ${BLUE}http://${HOST}:${PORT}/pro${NC}"
echo -e "  • 健康检查: ${BLUE}http://${HOST}:${PORT}/health${NC}"
echo -e "\n${YELLOW}提示:${NC}"
echo -e "  • 外网访问: 使用服务器 IP 或域名替换 ${HOST}"
echo -e "  • 停止服务: 按 ${RED}Ctrl+C${NC}"
echo -e "${BLUE}==========================================${NC}\n"

# 使用 python -m 方式运行主程序（正确的模块导入方式）
exec python -m app.main
