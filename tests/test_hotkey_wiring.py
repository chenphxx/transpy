"""回归测试: 双击 Ctrl 的译文必须真正走到主线程弹窗。

针对的历史缺陷: app.appcontext 曾把 self.post 直接当作热键结果回调传给
DoubleCtrlListener, 而 post 的签名是 (command, payload=None)。监听器是按
callback(text) 单参数调用的, 于是译文被当成「命令名」, 主线程只记一条
「未知命令: xxx」的日志, 结果弹窗永远不出现 —— 用户看到的就是「双击 Ctrl
毫无反应」。

注意 tests/test_smoke.py 是直接 ctx.post(CMD_SHOW_RESULT, ...) 投递的, 恰好
绕过了出错的那一环, 所以抓不到这个问题。本测试因此刻意走完整链路:

    DoubleCtrlListener._on_press -> _handle -> 结果回调 -> 队列 -> 主线程 Tk

真实的键盘钩子与按键合成在测试里被替换掉 (不占用全局键盘、不影响剪贴板)。
同时覆盖长按 Ctrl 的自动重复: 系统会在按住期间反复补发"按下", 若不忽略,
长按一次就会连续弹出十几个翻译窗口。

运行 (在仓库根目录): python tests/test_hotkey_wiring.py
"""

import os
import sys
import threading
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.appcontext as ac  # noqa: E402
import app.hotkey as hotkey  # noqa: E402
from app.config import Config  # noqa: E402
from pynput.keyboard import Key  # noqa: E402

FAKE_CLIPBOARD = "hello world"
FAKE_TRANSLATION = "FAKE-译文"

shown = []       # [(线程名, 弹窗文本)]
translated = []  # [传给翻译器的原文]
problems = []


class _NullContext:
    def __enter__(self):
        return None

    def __exit__(self, *exc):
        return False


class FakeController:
    """替代 pynput Controller: 不真的发送 Ctrl+C。"""

    def pressed(self, key):
        return _NullContext()

    def press(self, key):
        pass

    def release(self, key):
        pass


class FakeListener:
    """替代 pynput Listener: 不安装真实的全局键盘钩子。"""

    def __init__(self, on_press=None, on_release=None):
        self.on_press = on_press
        self.on_release = on_release

    def start(self):
        pass

    def stop(self):
        pass


class FakeTranslator:
    """替代 Translator: 不访问华为云。"""

    def __init__(self, result):
        self.result = result

    def translate(self, text):
        translated.append(text)
        return self.result


def main():
    hotkey.Controller = FakeController
    hotkey.Listener = FakeListener
    hotkey.wait_for_text = lambda wait, attempts=3: FAKE_CLIPBOARD

    config = Config(ak="x" * 8, sk="y" * 8, project_id="z" * 8)
    ctx = ac.AppContext(config, on_settings_save=lambda values: None)
    ctx.translator = FakeTranslator(FAKE_TRANSLATION)
    ctx._start_tray = lambda: None  # 测试不需要托盘

    class SpyWindow(ac.ResultWindow):
        """记录被展示的文本与所在线程后自动关闭。"""

        def __init__(self, master, result, title="翻译结果"):
            shown.append((threading.current_thread().name, result))
            super().__init__(master, result, title)
            self.after(80, self.destroy)

    ac.ResultWindow = SpyWindow

    # 启动真实的热键接线 (仅替换掉底层的键盘钩子与按键合成)
    ctx._start_listener()
    if ctx._listener is None:
        problems.append("热键监听未创建")
    ctx.root.after(ac.UI_POLL_INTERVAL_MS, ctx._dispatch)

    def double_ctrl():
        """模拟用户操作, 与真实键盘线程走同一条调用路径。"""
        time.sleep(0.2)
        # 正常双击 Ctrl: 按下 -> 抬起 -> 按下
        ctx._listener._on_press(Key.ctrl_l)
        ctx._listener._on_release(Key.ctrl_l)
        time.sleep(0.05)
        ctx._listener._on_press(Key.ctrl_l)
        ctx._listener._on_release(Key.ctrl_l)

        # 长按 Ctrl: 只补发按下、没有抬起, 不应再触发
        time.sleep(0.3)
        for _ in range(8):
            ctx._listener._on_press(Key.ctrl_l)
            time.sleep(0.02)

    threading.Thread(target=double_ctrl, name="fake-hotkey-thread", daemon=True).start()

    ctx.root.after(1000, lambda: ctx.post(ac.CMD_EXIT))
    ctx.root.after(
        6000,
        lambda: (problems.append("超时未退出"), ctx.post(ac.CMD_EXIT)),
    )

    main_thread = threading.main_thread().name
    ctx.run()

    print(f"翻译器收到的原文: {translated}")
    for name, text in shown:
        print(f"  展示于 [{name}]: {text}")

    if problems:
        print("问题:", problems)
        return 1
    if translated != [FAKE_CLIPBOARD]:
        if len(translated) > 1:
            print(f"失败: 长按 Ctrl 的自动重复被误判为多次双击 (共翻译 {len(translated)} 次)")
        else:
            print("失败: 双击 Ctrl 后没有把剪贴板文本送去翻译")
        return 1
    if not shown:
        print("失败: 译文没有弹窗 (结果回调可能被当成了命令名)")
        return 1
    if shown != [(main_thread, FAKE_TRANSLATION)]:
        print(f"失败: 弹窗内容/线程不符, 期望主线程展示 {FAKE_TRANSLATION!r}")
        return 1
    print("通过: 双击 Ctrl -> 复制 -> 翻译 -> 主线程弹窗 全链路正常, 且长按不误触发")
    return 0


if __name__ == "__main__":
    sys.exit(main())
