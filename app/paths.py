"""资源路径辅助工具。"""

import os
import sys


def resource_path(relative_path):
    """返回资源文件的绝对路径, 兼容 PyInstaller 打包后的 _MEIPASS 目录。"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        # 未打包时使用项目根目录 (app 包所在目录的上一级)
        base_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_path, relative_path)
