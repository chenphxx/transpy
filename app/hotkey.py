"""双击 Ctrl 触发翻译, 基于 pynput 监听键盘。"""

import time

import pynput
from pynput.keyboard import Controller, Key, Listener

from .clipboard import wait_for_text
from .constants import COPY_SETTLE_TIME, DOUBLE_PRESS_INTERVAL


class DoubleCtrlListener:
    """监听连续两次 Ctrl, 自动复制选中文本, 调用翻译并展示结果。"""

    def __init__(self, translator, show_result):
        self.translator = translator
        self.show_result = show_result  # callable(str)
        self._first_press = None
        self._controller = Controller()

    def start(self):
        with Listener(on_press=self._on_press) as listener:
            print("按下两次 Ctrl 来触发翻译")
            listener.join()

    def _on_press(self, key):
        if key not in (Key.ctrl_l, Key.ctrl_r):
            return
        now = time.time()
        if self._first_press is None:
            self._first_press = now
            return
        elapsed = now - self._first_press
        self._first_press = None
        if elapsed < DOUBLE_PRESS_INTERVAL:
            self._handle()

    def _handle(self):
        # 模拟 Ctrl+C 复制当前选中的文本
        with self._controller.pressed(Key.ctrl):
            self._controller.press("c")
            self._controller.release("c")

        text = wait_for_text(COPY_SETTLE_TIME)
        if not text:
            self.show_result("未检测到剪贴板文本 (请先选中要翻译的内容)。")
            return

        try:
            result = self.translator.translate(text)
        except Exception as exc:
            self.show_result(f"翻译失败:\n{exc}")
            return

        self.show_result(result)
