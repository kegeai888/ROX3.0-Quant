import webview
import threading
import uvicorn
import time
import sys
import os
import socket
import logging

# 将当前目录加入路径，确保能导入 app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.main import app

logger = logging.getLogger("rox-desktop")

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """检查端口是否被占用/服务是否已监听"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False

def run_server():
    """启动 FastAPI 后端服务"""
    uvicorn.run(app, host="127.0.0.1", port=8081, log_level="error")

def start_app():
    # 1. 在子线程启动后端
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 2. 等待服务器启动并检查端口（避免窗口打开后白屏）
    print("正在启动罗克思量化引擎...")
    host = "127.0.0.1"
    port = 8081
    server_ready = False
    for _ in range(40):  # 最多等待 20 秒
        if is_port_in_use(port, host=host):
            server_ready = True
            break
        time.sleep(0.5)

    # 3. 启动桌面窗口
    # 设置高科技感窗口参数
    if server_ready:
        window = webview.create_window(
            title='ROX QUANT v13.9 | 罗克思量化诊断系统',
            url=f'http://{host}:{port}',
            width=1280,
            height=850,
            resizable=True,
            min_size=(1000, 700),
            background_color='#0f172a'
        )
    else:
        # 后端没起来时给出可见错误提示，避免“空白窗口”
        logger.error("后端服务启动超时或端口不可用，窗口将显示错误页")
        html = f"""
        <html>
          <head><meta charset="utf-8"><title>ROX QUANT</title></head>
          <body style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto; background:#0f172a; color:#e2e8f0; padding:24px;">
            <h2 style="margin:0 0 12px 0;">后端服务未就绪</h2>
            <p style="margin:0 0 12px 0;">无法连接到 <code>http://{host}:{port}</code>，因此界面显示为空白。</p>
            <ul>
              <li>如果你是直接运行 <code>run_desktop.py</code>：请改用 <code>start_rox.sh</code> 或 <code>rox_desktop.py</code> 启动（带依赖/端口检查）。</li>
              <li>检查端口是否被占用：<code>lsof -i :{port}</code></li>
              <li>如果是公司网络/代理：可能导致后端拉取数据阻塞，但不应阻止页面渲染。</li>
            </ul>
          </body>
        </html>
        """
        window = webview.create_window(
            title='ROX QUANT - 启动失败',
            html=html,
            width=900,
            height=600,
            resizable=True,
            min_size=(800, 500),
            background_color='#0f172a'
        )
    
    # 启用调试模式以排查错误
    webview.start(debug=True)

if __name__ == '__main__':
    start_app()
