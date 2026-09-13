"""翻译结果弹窗。

窗口用 Toplevel 而不是 Tk: 整个进程里只能有一个 Tk 根窗口, 且它必须由主
线程创建, 所以根窗口由 app.appcontext 持有 (隐藏), 这里只负责弹出子窗口。
"""

import tkinter as tk

import pyperclip

from ..constants import ICON_PATH
from ..paths import resource_path

WINDOW_WIDTH = 360
WINDOW_HEIGHT = 180
WRAP_LENGTH = 320
MARGIN = 8          # 与屏幕边缘的最小间距
CURSOR_OFFSET = 12  # 窗口相对鼠标的偏移


class ResultWindow(tk.Toplevel):
    """显示翻译结果, 支持一键复制并关闭, 窗口出现在鼠标位置。"""

    def __init__(self, master, result, title="翻译结果"):
        super().__init__(master)
        self.title(title)
        self.minsize(240, 100)

        try:
            self.iconbitmap(resource_path(ICON_PATH))
        except Exception:
            # 图标缺失不应导致程序崩溃
            pass

        self._place_near_pointer()

        self.label = tk.Label(
            self, text=result, wraplength=WRAP_LENGTH, justify="left",
            font=("Cascadia Code", 12),
        )
        self.label.pack(padx=7, pady=7, fill="both", expand=True)

        self.copy_button = tk.Button(
            self,
            text="复制并关闭",
            command=self.copy_to_clipboard,
            font=("Cascadia Code", 10),
        )
        self.copy_button.pack(pady=(0, 7))

        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Control-c>", lambda _event: self.copy_to_clipboard())

        self.lift()
        try:
            self.attributes("-topmost", True)
            self.focus_force()
        except tk.TclError:
            pass

    def _place_near_pointer(self):
        """把窗口放在鼠标附近, 并保证不会跑到屏幕外。

        直接用鼠标坐标会出现窗口下边缘超出屏幕的情况 (鼠标在屏幕底部时),
        所以这里按鼠标位置钳制到工作区内。
        """
        try:
            width, height = self.winfo_screenwidth(), self.winfo_screenheight()
        except tk.TclError:
            return

        x, y = self.winfo_pointerx() + CURSOR_OFFSET, self.winfo_pointery() + CURSOR_OFFSET

        if x + WINDOW_WIDTH > width - MARGIN:
            x = max(MARGIN, x - WINDOW_WIDTH - 2 * CURSOR_OFFSET)
        if y + WINDOW_HEIGHT > height - MARGIN:
            y = max(MARGIN, y - WINDOW_HEIGHT - 2 * CURSOR_OFFSET)

        self.geometry(f"+{x}+{y}")

    def copy_to_clipboard(self):
        pyperclip.copy(self.label.cget("text"))
        self.destroy()
