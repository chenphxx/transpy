"""翻译结果弹窗。"""

import tkinter as tk

import pyperclip

from ..constants import ICON_PATH
from ..paths import resource_path


class ResultWindow(tk.Tk):
    """显示翻译结果, 支持一键复制并关闭, 窗口出现在鼠标位置。"""

    def __init__(self, result, title="翻译结果"):
        super().__init__()
        self.title(title)
        self.minsize(240, 100)

        try:
            self.iconbitmap(resource_path(ICON_PATH))
        except Exception:
            # 图标缺失不应导致程序崩溃
            pass

        x = self.winfo_pointerx()
        y = self.winfo_pointery()
        self.geometry(f"+{x}+{y}")

        self.label = tk.Label(
            self, text=result, wraplength=340, font=("Cascadia Code", 12)
        )
        self.label.pack(pady=7)

        self.copy_button = tk.Button(
            self,
            text="复制并关闭",
            command=self.copy_to_clipboard,
            font=("Cascadia Code", 10),
        )
        self.copy_button.pack(pady=7)

    def copy_to_clipboard(self):
        pyperclip.copy(self.label.cget("text"))
        self.destroy()
