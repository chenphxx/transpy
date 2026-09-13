"""翻译结果弹窗。

窗口用 Toplevel 而不是 Tk: 整个进程里只能有一个 Tk 根窗口, 且它必须由主
线程创建, 所以根窗口由 app.appcontext 持有 (隐藏), 这里只负责弹出子窗口。
"""

import tkinter as tk

import pyperclip

from ..constants import ICON_PATH
from ..paths import resource_path

WRAP_LENGTH = 320
MARGIN = 8          # 与屏幕边缘的最小间距
CURSOR_OFFSET = 12  # 窗口相对光标的偏移, 避免正好盖住光标
MIN_WIDTH = 240
MIN_HEIGHT = 100


class ResultWindow(tk.Toplevel):
    """显示翻译结果, 支持一键复制并关闭, 窗口出现在鼠标位置。"""

    def __init__(self, master, result, title="翻译结果"):
        super().__init__(master)

        # 先在隐藏状态下把内容建好再定位: 窗口一旦以默认尺寸显示出来, 系统
        # 会把它摆到默认级联位置, 之后再设置位置多半会被丢掉, 结果就是弹窗
        # 不在光标处
        self.withdraw()
        self.title(title)
        self.minsize(MIN_WIDTH, MIN_HEIGHT)

        try:
            self.iconbitmap(resource_path(ICON_PATH))
        except Exception:
            # 图标缺失不应导致程序崩溃
            pass

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

        self._place_at_pointer()
        self.deiconify()
        self.lift()
        try:
            self.attributes("-topmost", True)
            self.focus_force()
        except tk.TclError:
            pass

    def _place_at_pointer(self):
        """把窗口定位到光标处, 并保证整个窗口都在屏幕内。

        尺寸取内容实际需要的大小 (长译文的窗口更高), 位置和尺寸一起在
        deiconify 之前设置好, 否则系统会用默认尺寸重新摆放窗口。
        """
        try:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
        except tk.TclError:
            return

        self.update_idletasks()
        width = max(self.winfo_reqwidth(), MIN_WIDTH)
        height = max(self.winfo_reqheight(), MIN_HEIGHT)

        x = self.winfo_pointerx() + CURSOR_OFFSET
        y = self.winfo_pointery() + CURSOR_OFFSET

        # 光标右下放不下就翻到左上, 两种情况都不允许超出屏幕
        if x + width > screen_w - MARGIN:
            x = max(MARGIN, x - width - 2 * CURSOR_OFFSET)
        if y + height > screen_h - MARGIN:
            y = max(MARGIN, y - height - 2 * CURSOR_OFFSET)

        self.geometry(f"{width}x{height}+{x}+{y}")

    def copy_to_clipboard(self):
        pyperclip.copy(self.label.cget("text"))
        self.destroy()
