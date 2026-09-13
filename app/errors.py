"""面向用户的错误提示。

打包时使用的是 console=False (GUI 模式), 没有终端可以看到 traceback, 所以
致命错误必须让用户看见。

但原生 MessageBoxW 在 windowed 打包进程里并不可靠: 实测在没有可见窗口作
owner 时, MessageBoxW 会既不显示也不返回, 直接把启动流程锁死。因此常规提示
一律走 tkinter 自绘对话框 (dialog_ok), 原生 MessageBox 只保留给"tkinter 都
起不来"的极端兜底。
"""

import ctypes
import logging
import traceback

MB_OK = 0x0
MB_ICONERROR = 0x10
MB_ICONWARNING = 0x30
MB_ICONINFORMATION = 0x40

_OWNER = None  # 可选的 tkinter 窗口, 用作弹窗父窗口


def set_owner(window):
    """注册一个 tkinter 窗口作为弹窗的父窗口。"""
    global _OWNER
    _OWNER = window


def show(title, message, flags=MB_OK | MB_ICONINFORMATION):
    """原生 Win32 消息框。会阻塞直到用户点击, 仅在 tkinter 不可用时使用。"""
    try:
        owner = _OWNER.winfo_id() if _OWNER is not None else 0
    except Exception:
        owner = 0
    try:
        ctypes.windll.user32.MessageBoxW(owner, str(message), str(title), flags)
    except Exception:
        # 连弹窗都失败时不能抛异常, 否则会掩盖原始错误
        logging.getLogger(__name__).exception("显示错误对话框失败")


def dialog_ok(title, message, parent=None, error=False):
    """用 tkinter 自绘的模态提示框, 返回后调用方才继续。

    这是首选方式: 不依赖原生 MessageBox 的行为, 在任何打包模式下都能正常
    显示和关闭。tkinter 不可用时回落到原生 MessageBox。
    """
    try:
        import tkinter as tk
    except Exception:
        show(title, message, MB_OK | (MB_ICONERROR if error else MB_ICONINFORMATION))
        return

    logger = logging.getLogger(__name__)
    try:
        holder = None
        if parent is None:
            holder = tk.Tk()
            holder.withdraw()
            parent = holder

        win = tk.Toplevel(parent)
        win.title(title)
        win.resizable(False, False)
        tk.Label(
            win, text=message, justify="left", wraplength=420, padx=18, pady=16
        ).pack()
        button = tk.Button(win, text="确定", width=10, command=win.destroy)
        button.pack(pady=(0, 14))

        win.bind("<Return>", lambda _e: win.destroy())
        win.bind("<Escape>", lambda _e: win.destroy())
        win.protocol("WM_DELETE_WINDOW", win.destroy)

        win.update_idletasks()
        width, height = win.winfo_width(), win.winfo_height()
        x = (win.winfo_screenwidth() - width) // 2
        y = (win.winfo_screenheight() - height) // 3
        win.geometry(f"+{max(0, x)}+{max(0, y)}")

        win.lift()
        try:
            win.attributes("-topmost", True)
            win.grab_set()
        except tk.TclError:
            pass
        button.focus_set()
        win.wait_window()

        if holder is not None:
            holder.destroy()
    except Exception:
        # 自绘失败时退回原生弹窗, 至少不会让流程中断
        logger.exception("显示提示框失败, 尝试原生弹窗")
        show(title, message, MB_OK | (MB_ICONERROR if error else MB_ICONINFORMATION))


def show_error(title, message, parent=None):
    dialog_ok(title, message, parent=parent, error=True)


def show_warning(title, message, parent=None):
    dialog_ok(title, message, parent=parent)


def show_info(title, message, parent=None):
    dialog_ok(title, message, parent=parent)


def show_exception(title, exc, context="", parent=None):
    """把异常连同堆栈写进日志, 并给用户看一条简短提示。"""
    logging.getLogger(__name__).error(
        "%s: %s", context or title, exc, exc_info=True
    )
    detail = traceback.format_exc()
    message = f"{context}\n\n{exc}" if context else str(exc)
    if len(detail) > 1200:
        detail = detail[:1200] + "\n...(详见日志)"
    dialog_ok(title, f"{message}\n\n技术细节:\n{detail}", parent=parent, error=True)
