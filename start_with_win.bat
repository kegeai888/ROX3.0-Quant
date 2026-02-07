@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==================================================
echo    🚀 ROX 3.0 Pro 量化终端 (Windows 启动器)
echo    正在初始化环境，请稍候...
echo ==================================================

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未检测到 Python 环境！
    echo 💡 请前往 https://www.python.org/downloads/ 下载并安装 Python 3.9+
    echo    注意: 安装时请勾选 "Add Python to PATH"
    pause
    exit /b
)

:: 检查/创建虚拟环境
if not exist venv (
    echo 正在为您创建虚拟环境 (首次运行可能较慢)...
    python -m venv venv
    echo ✅ 虚拟环境创建成功！
)

:: 激活虚拟环境
call venv\Scripts\activate

:: 安装依赖
echo 正在检查并安装依赖库...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

:: 启动浏览器
echo ✅ 环境准备就绪，正在启动 ROX 服务...
start "" "http://localhost:8002"

echo 🌐 服务已启动，请勿关闭此窗口
echo --------------------------------------------------

python -m uvicorn app.main:app --host 0.0.0.0 --port 8002
pause
