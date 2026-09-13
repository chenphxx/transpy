"""Windows 平台相关的原生调用。

集中放在这里, 便于在非 Windows 环境下 import 时也能给出明确错误。
"""

import ctypes
import logging
import os
import socket
import sys

logger = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"

# ---------------------------------------------------------------------------
# 任务栏图标分组
# ---------------------------------------------------------------------------

APP_USER_MODEL_ID = "transpy.agent.1"


def set_app_user_model_id(app_id=APP_USER_MODEL_ID):
    """设置进程的 AppUserModelID。

    不设置的话, 翻译弹窗在任务栏上会显示为孤立的 python 图标且不与进程
    分组; 设置后任务栏使用 exe 自带的图标。
    """
    if not _IS_WINDOWS:
        return False
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        return True
    except Exception:
        logger.debug("设置 AppUserModelID 失败", exc_info=True)
        return False


# ---------------------------------------------------------------------------
# 单实例
# ---------------------------------------------------------------------------

ERROR_ALREADY_EXISTS = 183
_MUTEX_HANDLE = None  # 必须持有到进程结束, 否则互斥量会被释放


def acquire_single_instance(name="Global\\transpy.single-instance"):
    """尝试获取单实例互斥量。

    返回 True 表示这是第一个实例; False 表示已有实例在运行。
    """
    global _MUTEX_HANDLE
    if not _IS_WINDOWS:
        return True
    try:
        handle = ctypes.windll.kernel32.CreateMutexW(None, False, name)
        if not handle:
            # 创建失败时不要阻拦用户启动程序
            return True
        if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            ctypes.windll.kernel32.CloseHandle(handle)
            return False
        _MUTEX_HANDLE = handle
        return True
    except Exception:
        logger.debug("单实例检测失败, 按允许多开处理", exc_info=True)
        return True


# ---------------------------------------------------------------------------
# 激活已有实例
# ---------------------------------------------------------------------------

_ACTIVATION_PORT = 50517
_ACTIVATION_TOKEN = b"activate"
_ACTIVATION_SOCKET = None


def _bind_activation_socket():
    global _ACTIVATION_SOCKET
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(("127.0.0.1", _ACTIVATION_PORT))
    except OSError:
        # 端口被占用说明已有实例在监听, 或者被别的程序占了
        server.close()
        return None
    server.listen(5)
    _ACTIVATION_SOCKET = server
    return server


def start_activation_server(on_activate):
    """在后台线程监听激活请求。

    第二个实例启动时会向这里发一条消息, 由 on_activate 决定如何响应
    (通常是弹窗告诉用户程序已在运行)。服务器套接字绑定失败时返回 None。
    """
    import threading

    server = _bind_activation_socket()
    if server is None:
        return None

    def _serve():
        while True:
            try:
                conn, _ = server.accept()
            except OSError:
                return
            try:
                conn.settimeout(1.0)
                if conn.recv(64).strip() == _ACTIVATION_TOKEN:
                    on_activate()
            except OSError:
                pass
            finally:
                try:
                    conn.close()
                except OSError:
                    pass

    thread = threading.Thread(target=_serve, name="transpy-activation", daemon=True)
    thread.start()
    return server


def notify_existing_instance(timeout=1.0):
    """作为第二个实例, 通知已有实例; 返回是否通知成功。"""
    try:
        with socket.create_connection(("127.0.0.1", _ACTIVATION_PORT), timeout) as s:
            s.sendall(_ACTIVATION_TOKEN)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# 其它
# ---------------------------------------------------------------------------

def is_windows():
    return _IS_WINDOWS


def ctrl_alt_shortcut_hint():
    """返回一个不依赖托盘图标的退出方式说明, 用于托盘不可用时提示用户。"""
    return "程序在后台运行中。若找不到托盘图标, 请在任务管理器中结束 transpy.exe。"


def open_folder(path):
    """用资源管理器打开目录。"""
    if not _IS_WINDOWS:
        return False
    try:
        os.startfile(path)  # noqa: S606 - 仅打开本地已知目录
        return True
    except Exception:
        logger.debug("打开目录失败: %s", path, exc_info=True)
        return False
