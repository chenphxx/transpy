"""资源路径与运行目录辅助工具。"""

import os
import sys

APP_DIR_NAME = "transpy"


def resource_path(relative_path):
    """返回随程序分发的只读资源路径。

    打包运行时资源被解压到 sys._MEIPASS (临时目录, 只读),
    源码运行时回落到项目根目录。

    注意: 这个目录只适合读取, 不要向其中写入任何用户配置。
    """
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path is None:
        # 未打包时使用项目根目录 (app 包所在目录的上一级)
        base_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_path, relative_path)


def _project_root():
    """返回源码运行时的项目根目录 (app 包所在目录的上一级)。"""
    return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def app_root():
    """返回「程序所在目录」。

    打包运行: exe 所在目录 (sys.executable)。
    源码运行: 项目根目录。

    这是便携版放置 .env / csv 的位置; 之所以不用 __file__ 推算,
    是因为 onefile 模式下 __file__ 指向临时解压目录。
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return _project_root()


def user_data_dir():
    """返回用户级配置目录: %APPDATA%\\transpy。

    与程序安装位置解耦, 始终可写, 是保存密钥的主位置。
    """
    appdata = (
        os.environ.get("APPDATA")
        or os.environ.get("LOCALAPPDATA")
        or os.path.expanduser("~")
    )
    return os.path.join(appdata, APP_DIR_NAME)


def user_log_dir():
    """返回用户级日志目录: %LOCALAPPDATA%\\transpy\\logs。"""
    local = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if local:
        return os.path.join(local, APP_DIR_NAME, "logs")
    return os.path.join(os.path.expanduser("~"), "." + APP_DIR_NAME, "logs")


def ensure_dir(path):
    """确保目录存在并返回该路径; 失败时抛出 OSError 由调用方处理。"""
    os.makedirs(path, exist_ok=True)
    return path
