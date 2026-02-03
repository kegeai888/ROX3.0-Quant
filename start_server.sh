#!/bin/bash
echo "=========================================="
echo "  ROX Quant 网页版 (start_server.sh)"
echo "=========================================="

# Prefer local venv python in this repo; fallback to system python3
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || { echo "错误: 无法进入项目目录 $SCRIPT_DIR"; exit 1; }

if [ -x ".venv/bin/python" ]; then
  PYTHON_EXEC="$SCRIPT_DIR/.venv/bin/python"
else
  PYTHON_EXEC="$(command -v python3)"
fi
if [ -z "$PYTHON_EXEC" ]; then
  echo "错误: 未找到 python3，请先安装 Python 3。"
  exit 1
fi

# Free port 8081 if already in use (macOS-friendly)
PORT=8081
PIDS="$(lsof -nP -iTCP:$PORT -sTCP:LISTEN -t 2>/dev/null || true)"
if [ -n "$PIDS" ]; then
  echo "端口 $PORT 已被占用，正在尝试释放..."
  kill -TERM $PIDS 2>/dev/null || true
  sleep 1
  PIDS2="$(lsof -nP -iTCP:$PORT -sTCP:LISTEN -t 2>/dev/null || true)"
  if [ -n "$PIDS2" ]; then
    kill -KILL $PIDS2 2>/dev/null || true
    sleep 1
  fi
fi

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  echo "  提示: 未发现 .env，可复制 .env.example 并配置 AI_API_KEY 等。"
  echo ""
fi
echo "  重要：地址必须带端口 $PORT，不能只填 127.0.0.1"
echo "  经典版: http://127.0.0.1:$PORT"
echo "  专业版: http://127.0.0.1:$PORT/pro"
echo "  健康检查: http://127.0.0.1:$PORT/api/system/health"
echo "  按 Ctrl+C 停止"
echo "  详细说明: docs/打开方式与使用说明.md"
echo "=========================================="
echo ""

# Start the server using python -m uvicorn
exec "$PYTHON_EXEC" -m uvicorn app.main:app --host 127.0.0.1 --port $PORT --reload
