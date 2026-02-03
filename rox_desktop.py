import webview
import threading
import uvicorn
import time
import sys
import os
import logging
import socket

# ============ 日志配置 ============
log_path = os.path.expanduser("~/rox_quant_debug.log")
logging.basicConfig(
    filename=log_path, 
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """检查端口是否被占用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            return result == 0
    except Exception as e:
        logger.warning(f"端口检查失败: {e}")
        return False

def start_server():
    """在子线程中启动 FastAPI 服务器"""
    try:
        from app.main import app
        from app.core.config import settings
        
        logger.info(f"启动 FastAPI 服务器: {settings.DESKTOP_HOST}:{settings.DESKTOP_PORT}")
        
        # 根据环境选择日志级别
        log_level = "debug" if settings.ENVIRONMENT == "development" else "info"
        
        uvicorn.run(
            app,
            host=settings.DESKTOP_HOST,
            port=settings.DESKTOP_PORT,
            log_level=log_level,
            access_log=settings.ENVIRONMENT == "development"
        )
    except Exception as e:
        logger.error(f"服务器启动错误: {str(e)}", exc_info=True)
        sys.exit(1)

def main():
    """主程序入口"""
    try:
        logger.info("=== Rox Quant 桌面应用启动 ===")
        
        # 1. 检查端口是否已被占用
        from app.core.config import settings
        
        if is_port_in_use(settings.DESKTOP_PORT):
            logger.warning(f"端口 {settings.DESKTOP_PORT} 已被占用，可能是另一个实例在运行")
            response = input(f"是否继续启动? (y/n): ")
            if response.lower() != 'y':
                logger.info("用户取消启动")
                return

        # 2. 启动后端服务器线程
        logger.info("启动后端服务器线程...")
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()

        # 3. 等待服务器就绪 (最多10秒)
        logger.info("等待服务器就绪...")
        server_ready = False
        max_retries = 20
        
        for i in range(max_retries):
            time.sleep(0.5)
            if is_port_in_use(settings.DESKTOP_PORT):
                server_ready = True
                elapsed = (i + 1) * 0.5
                logger.info(f"✓ 服务器已就绪 (耗时: {elapsed:.1f}秒)")
                break
        
        if not server_ready:
            logger.error(f"✗ 服务器启动超时 (>{max_retries*0.5}秒)")
            print("错误: 服务器启动超时，请检查日志")
            sys.exit(1)

        # 4. 创建原生桌面窗口
        logger.info(f"创建桌面窗口: http://{settings.DESKTOP_HOST}:{settings.DESKTOP_PORT}")
        window = webview.create_window(
            title='Rox Quant - 量化交易助手 v3.0',
            url=f'http://{settings.DESKTOP_HOST}:{settings.DESKTOP_PORT}',
            width=1400,
            height=900,
            resizable=True,
            min_size=(1000, 700),
            background_color='#ffffff'
        )

        # 5. 启动 GUI
        # debug=True 允许右键查看开发者工具
        # http_server=False 表示不启动内置HTTP服务器（我们用FastAPI）
        debug_mode = settings.ENVIRONMENT == "development"
        logger.info(f"启动GUI (Debug模式: {debug_mode})")
        
        webview.start(debug=debug_mode, http_server=False)
        
        logger.info("=== Rox Quant 应用已关闭 ===")
        
    except Exception as e:
        logger.error(f"主程序错误: {str(e)}", exc_info=True)
        print(f"致命错误: {str(e)}")
        print(f"详细信息已保存到: {log_path}")
        sys.exit(1)

if __name__ == '__main__':
    main()
