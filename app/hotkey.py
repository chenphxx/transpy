"""双击 Ctrl 触发翻译, 基于 pynput 监听键盘。

监听回调运行在 pynput 自己的后台线程里, 因此这里绝对不能直接创建或操作
tkinter 窗口 —— Tk 有线程亲和性, 跨线程操作会导致偶发崩溃或窗口不显示。
本模块只负责把待展示的文本交给 result_callback, 由它投递到主线程。
"""

import logging
import time

from pynput.keyboard import Controller, Key, Listener

from .clipboard import wait_for_text
from .constants import COPY_SETTLE_TIME, CTRL_REPEAT_GAP, DOUBLE_PRESS_INTERVAL

logger = logging.getLogger(__name__)


class DoubleCtrlListener:
    """监听连续两次 Ctrl, 自动复制选中文本, 调用翻译并展示结果。"""

    def __init__(self, translator, result_callback):
        self.translator = translator
        self.result_callback = result_callback  # callable(str), 必须线程安全
        self._first_press = None
        self._ctrl_down = False
        self._ctrl_down_at = 0.0
        self._controller = Controller()
        self._listener = None
        self._paused = False

    # -- 生命周期 ---------------------------------------------------------

    def start(self):
        """启动监听 (非阻塞)。"""
        if self._listener is not None:
            return
        self._listener = Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()  # 不阻塞调用方, 主线程要留给 tkinter
        logger.info("键盘监听已启动")

    def stop(self):
        """停止监听并释放键盘钩子。"""
        if self._listener is None:
            return
        try:
            self._listener.stop()
        except Exception:
            logger.debug("停止键盘监听失败", exc_info=True)
        self._listener = None
        logger.info("键盘监听已停止")

    def pause(self):
        self._paused = True
        self._first_press = None
        logger.info("已暂停翻译热键")

    def resume(self):
        self._paused = False
        logger.info("已恢复翻译热键")

    @property
    def paused(self):
        return self._paused

    # -- 事件处理 ---------------------------------------------------------

    def _on_press(self, key):
        if self._paused:
            return
        if key not in (Key.ctrl_l, Key.ctrl_r):
            # 两次 Ctrl 之间按了别的键, 判定为普通操作而非双击手势,
            # 避免 Ctrl+C 之后紧接着一次 Ctrl 就误触发。
            self._first_press = None
            return

        now = time.monotonic()

        # 按住 Ctrl 时系统会持续补发「按下」事件 (自动重复)。若不忽略,
        # 长按 Ctrl 会被当成连续双击, 每秒弹出十几个翻译窗口。
        # 真正的双击中间必然有一次抬起, 所以这里以「上一次按下之后是否
        # 抬起过」来区分。
        if self._ctrl_down and (now - self._ctrl_down_at) < CTRL_REPEAT_GAP:
            return
        self._ctrl_down = True
        self._ctrl_down_at = now

        if self._first_press is None:
            self._first_press = now
            return

        elapsed = now - self._first_press
        self._first_press = None
        if elapsed < DOUBLE_PRESS_INTERVAL:
            try:
                self._handle()
            except Exception:
                logger.exception("处理双击 Ctrl 时出错")

    def _on_release(self, key):
        """记录 Ctrl 抬起, 用于区分「再次按下」与「长按自动重复」。

        注意: _handle() 合成的 Ctrl+C 同样会产生抬起事件, 这里只是把状态
        置为未按下; 若它抢在用户真正抬起之前到达, 后续重复事件会以
        CTRL_REPEAT_GAP 兜底, 不会连续触发。
        """
        if key in (Key.ctrl_l, Key.ctrl_r):
            self._ctrl_down = False

    def _handle(self):
        # 模拟 Ctrl+C 复制当前选中的文本
        with self._controller.pressed(Key.ctrl):
            self._controller.press("c")
            self._controller.release("c")

        text = wait_for_text(COPY_SETTLE_TIME)
        if not text:
            self._show("未检测到剪贴板文本 (请先选中要翻译的内容)。")
            return

        try:
            result = self.translator.translate(text)
        except Exception as exc:
            logger.warning("翻译失败: %s", exc)
            self._show(f"翻译失败:\n{exc}")
            return

        self._show(result)

    def _show(self, text):
        """把文本交给 UI 层; 这里只是回调, 不涉及任何 tkinter 对象。"""
        try:
            self.result_callback(text)
        except Exception:
            logger.exception("把结果投递给主线程失败")
