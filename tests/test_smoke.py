"""测试: 主线程收敛 (后台线程 -> 队列 -> 主线程 Tk) 是否工作。

不依赖华为云网络与真实键盘钩子/托盘, 只检查线程模型:
    1. 后台线程 post 结果, 主线程能弹出 Toplevel;
    2. 连续多次投递不丢失、不乱序;
    3. 退出命令能让 mainloop 正常结束。

运行 (在仓库根目录): python tests/test_smoke.py
"""

import os
import sys
import threading
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.appcontext import AppContext, CMD_EXIT, CMD_SHOW_RESULT  # noqa: E402
from app.config import Config  # noqa: E402

created = []
problems = []


def main():
    config = Config(ak="x" * 8, sk="y" * 8, project_id="z" * 8)
    ctx = AppContext(config, on_settings_save=lambda values: None)

    # 不启动真实的热键监听与托盘 (测试环境不需要, 也不想占用全局键盘)
    ctx._start_listener = lambda: None
    ctx._start_tray = lambda: None

    import app.appcontext as ac

    class SpyWindow(ac.ResultWindow):
        """替换真实窗口, 记录被展示的文本后自动关闭。"""

        def __init__(self, master, result, title="翻译结果"):
            created.append((threading.current_thread().name, result))
            super().__init__(master, result, title)
            self.after(120, self.destroy)

    ac.ResultWindow = SpyWindow

    def worker():
        """模拟 pynput / pystray 线程: 只投递, 不碰 tkinter。"""
        for i in range(3):
            time.sleep(0.15)
            ctx.post(CMD_SHOW_RESULT, f"第 {i + 1} 条结果")
        time.sleep(0.3)
        ctx.post(CMD_EXIT)

    ctx.start()
    threading.Thread(target=worker, name="fake-hotkey-thread", daemon=True).start()

    # 兜底: 避免测试挂死
    ctx.root.after(6000, lambda: (problems.append("超时未收到退出命令"), ctx.post(CMD_EXIT)))

    main_thread = threading.main_thread().name
    ctx.run()

    texts = [text for _name, text in created]
    print("主线程名:", main_thread)
    for name, text in created:
        print(f"  展示于 [{name}]: {text}")

    if problems:
        print("问题:", problems)
        return 1
    if texts != ["第 1 条结果", "第 2 条结果", "第 3 条结果"]:
        print("失败: 结果数量或顺序不符")
        return 1
    if any(name != main_thread for name, _ in created):
        print("失败: 窗口不是在主线程创建的")
        return 1
    print("通过: 后台线程 -> 队列 -> 主线程 Tk 的投递链路正常, 窗口均创建于主线程")
    return 0


if __name__ == "__main__":
    sys.exit(main())
