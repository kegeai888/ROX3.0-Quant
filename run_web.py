#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROX Quant 网页版一键启动脚本。
默认端口 8008；若被占用则尝试 8081、9000。
启动成功后打印要在浏览器中打开的地址。
"""
import socket
import sys
import os

def is_port_free(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex((host, port)) != 0
    except Exception:
        return False

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    host = "127.0.0.1"
    for port in [8008, 8081, 9000]:
        if is_port_free(host, port):
            break
    else:
        print("错误: 端口 8008、8081、9000 均已被占用，请先关闭占用端口的程序。")
        sys.exit(1)

    print("=" * 50)
    print("  ROX Quant 网页版")
    print("=" * 50)
    print(f"  启动后请在浏览器打开: http://{host}:{port}")
    print("  专业版: http://{host}:{port}/pro")
    print("  按 Ctrl+C 停止服务")
    print("=" * 50)

    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level="info",
    )

if __name__ == "__main__":
    main()
