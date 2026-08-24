"""剪贴板读写工具。"""

import time

import pyperclip


def copy(text: str) -> None:
    pyperclip.copy(text)


def paste() -> str:
    return pyperclip.paste() or ""


def wait_for_text(wait: float, attempts: int = 3) -> str:
    """延时后读取剪贴板, 对空值做简单重试。"""
    text = ""
    for _ in range(attempts):
        time.sleep(wait)
        text = paste()
        if text:
            return text
    return paste()
