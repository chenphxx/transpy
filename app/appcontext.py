"""应用上下文: 主线程事件循环 + 后台线程投递。

线程模型 (这是本程序最容易出错的地方):

    主线程      —— 唯一的 Tk 根窗口 (隐藏) 与 root.mainloop(),
                   所有 tkinter 窗口都只能在这里创建和销毁。
    pynput 线程 —— 键盘监听, 只把待展示的文本投递到队列。
    pystray线程 —— 托盘图标, 菜单回调同样只投递队列。

跨线程一律不碰 tkinter 对象, 统一走 self._queue + root.after 轮询。
"""

import logging
import queue
import threading
import tkinter as tk

from .constants import UI_POLL_INTERVAL_MS
from .errors import set_owner, show_error, show_exception, show_info
from .translator import Translator
from .ui.result_window import ResultWindow
from .ui.settings_dialog import SettingsDialog

logger = logging.getLogger(__name__)

CMD_SHOW_RESULT = "show_result"
CMD_SHOW_SETTINGS = "show_settings"
CMD_SHOW_ERROR = "show_error"
CMD_EXIT = "exit"


class AppContext:
    """持有根窗口、翻译器与后台组件的运行上下文。

    参数:
        config:    已加载的 Config
        on_settings_save: callable(values dict), 保存配置对话框内容
        on_exit:   callable(), 进程级清理钩子 (停止单实例监听等)
    """

    def __init__(self, config, on_settings_save, on_exit=None):
        self.config = config
        self._on_settings_save = on_settings_save
        self._on_exit = on_exit

        self._queue = queue.Queue()
        self._stopping = False
        self._displayed = False

        self.root = self._create_root()
        set_owner(self.root)

        self.translator = Translator(config)
        self._listener = None
        self._tray = None

    # -- 构造 -------------------------------------------------------------

    def _create_root(self):
        """创建隐藏的根窗口。

        这个窗口不会显示、不会出现在任务栏, 只是给 Tk 一个主线程的锚点,
        让翻译弹窗和配置对话框都能以 Toplevel 的形式在主线程出现。
        """
        root = tk.Tk()
        root.withdraw()
        try:
            root.title("transpy")
        except tk.TclError:
            pass
        return root

    # -- 生命周期 ---------------------------------------------------------

    def start(self):
        """启动热键监听与托盘图标, 由调用方随后进入 mainloop。"""
        self._start_listener()
        self._start_tray()
        self.root.after(UI_POLL_INTERVAL_MS, self._dispatch)

    def _start_listener(self):
        from .hotkey import DoubleCtrlListener

        self._listener = DoubleCtrlListener(self.translator, self.post)
        self._listener.start()

    def _start_tray(self):
        try:
            from .tray import TrayIcon

            self._tray = TrayIcon(
                on_settings=lambda: self.post(CMD_SHOW_SETTINGS),
                on_pause=self._on_tray_pause,
                on_exit=lambda: self.post(CMD_EXIT),
            )
            self._tray.start()
        except Exception:
            # 托盘不可用不应导致程序无法运行, 但必须让用户知道怎么退出
            self._tray = None
            logger.exception("托盘图标不可用")
            show_error(
                "transpy",
                "系统托盘图标初始化失败, 程序仍会在后台运行。\n"
                "如需退出, 请在任务管理器中结束 transpy.exe。\n"
                "详情见日志文件。",
                parent=self.root,
            )

    def run(self):
        """进入 Tk 主循环, 阻塞直到退出。"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.post(CMD_EXIT)
            self._do_exit()

    def shutdown(self):
        """释放后台资源 (不销毁根窗口, 便于托盘菜单重建上下文)。

        托盘停止在独立线程中执行并最多等待一小会儿: pystray 的 stop 在
        Windows 上偶有阻塞, 不能让它卡住退出流程。
        """
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        if self._tray is not None:
            tray, self._tray = self._tray, None
            stopper = threading.Thread(
                target=tray.stop, name="transpy-tray-stop", daemon=True
            )
            stopper.start()
            stopper.join(timeout=2.0)

    # -- 跨线程投递 -------------------------------------------------------

    def post(self, command, payload=None):
        """任何线程都可以调用, 把要在主线程执行的动作排队。"""
        self._queue.put((command, payload))

    def _dispatch(self):
        """主线程轮询队列并执行 UI 操作。"""
        if self._stopping:
            return
        handled = 0
        while handled < 16:
            try:
                command, payload = self._queue.get_nowait()
            except queue.Empty:
                break
            handled += 1
            try:
                self._execute(command, payload)
            except Exception as exc:
                logger.exception("处理命令 %s 失败", command)
                show_exception(
                    "transpy", exc, context=f"处理 {command} 时出错", parent=self.root
                )
            if self._stopping:
                return
        self.root.after(UI_POLL_INTERVAL_MS, self._dispatch)

    def _execute(self, command, payload):
        if command == CMD_SHOW_RESULT:
            self._show_result(payload)
        elif command == CMD_SHOW_SETTINGS:
            self._show_settings()
        elif command == CMD_SHOW_ERROR:
            # payload 约定为 (message, title)
            message, title = payload
            show_error(title, message, parent=self.root)
        elif command == CMD_EXIT:
            self._do_exit()
        else:
            logger.warning("未知命令: %s", command)

    # -- 主线程 UI 操作 ---------------------------------------------------

    def _show_result(self, text):
        self._displayed = True
        try:
            ResultWindow(self.root, text)
        except tk.TclError:
            logger.debug("窗口被提前销毁", exc_info=True)

    def _show_settings(self):
        values = {
            "ak": self.config.ak,
            "sk": self.config.sk,
            "project_id": self.config.project_id,
            "region": self.config.region,
        }
        SettingsDialog(self.root, values, on_save=self._on_saved)

    def _on_saved(self, values):
        """保存配置并重启后台组件, 让新凭据立即生效。"""
        self._on_settings_save(values)
        self.restart()
        show_info("transpy", "配置已保存, 翻译服务已重新加载。", parent=self.root)

    # -- 托盘回调 (运行在托盘线程) ----------------------------------------

    def _on_tray_pause(self, paused):
        if self._listener is None:
            return
        if paused:
            self._listener.pause()
        else:
            self._listener.resume()

    # -- 重启与退出 -------------------------------------------------------

    def restart(self):
        """用当前 self.config 重建翻译器与热键监听。

        注意: 不重建根窗口, 也不重新启动托盘 —— 这两者在整个进程里是唯一的。
        """
        self.shutdown()
        self.translator = Translator(self.config)
        self._start_listener()
        if self._tray is None:
            self._start_tray()

    def _do_exit(self):
        if self._stopping:
            return
        self._stopping = True
        logger.info("正在退出")
        self.shutdown()
        if self._on_exit is not None:
            try:
                self._on_exit()
            except Exception:
                logger.debug("退出钩子执行失败", exc_info=True)
        try:
            self.root.quit()
        except tk.TclError:
            pass
