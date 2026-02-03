import os
import sys

def get_resource_path(relative_path):
    """
    获取资源的绝对路径。
    在打包后的 .exe 中，资源会被解压到临时目录 _MEIxxxx 中。
    在开发环境下，则返回相对于当前文件的路径。
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的路径
        return os.path.join(sys._MEIPASS, relative_path)
    # 开发环境下的路径
    return os.path.join(os.path.abspath("."), relative_path)
