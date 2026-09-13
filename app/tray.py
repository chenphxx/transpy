"""系统托盘图标。

这是程序在任务栏/通知区域的「存在感」: 无窗口的后台进程本来就不会出现在
任务栏, 托盘图标既能让用户看到程序在运行, 也提供了退出入口, 不必再开任务
管理器结束进程。

注意 pystray 与 tkinter 都要求主线程, 因此这里统一用 run_detached() 让托盘
在自己的线程里跑, 主线程留给 tkinter。
"""

import logging

import pystray
from PIL import Image

from .constants import APP_TITLE, APP_TIP, ICON_PATH
from .paths import resource_path

logger = logging.getLogger(__name__)


def load_icon_image():
    """加载托盘图标; 失败时返回一个纯色占位图, 保证托盘仍可用。"""
    try:
        return Image.open(resource_path(ICON_PATH))
    except Exception:
        logger.warning("加载托盘图标失败, 使用占位图标", exc_info=True)
        return Image.new("RGBA", (64, 64), (0, 120, 215, 255))


class TrayIcon:
    """托盘图标与右键菜单。

    参数均为回调, 且在非主线程中被调用, 回调内部必须自行投递到主线程:
        on_settings()  打开配置对话框
        on_pause()     暂停/恢复翻译热键
        on_exit()      退出程序
    """

    def __init__(self, on_settings, on_pause, on_exit):
        self._on_settings = on_settings
        self._on_pause = on_pause
        self._on_exit = on_exit
        self._paused = False

        self._icon = pystray.Icon(
            APP_TITLE,
            load_icon_image(),
            APP_TIP,
            menu=self._build_menu(),
        )

    # -- 菜单 -------------------------------------------------------------

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem("设置密钥...", self._safe(self._settings), default=True),
            pystray.MenuItem(
                "暂停翻译热键",
                self._safe(self._toggle_pause),
                checked=lambda _item: self._paused,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._safe(self._exit)),
        )

    def _safe(self, func):
        """包装菜单回调, 避免异常打断托盘线程。"""

        def wrapper(icon, item):  # pystray 会传入 (icon, item)
            try:
                func()
            except Exception:
                logger.exception("托盘菜单操作失败")

        return wrapper

    # -- 回调实现 ---------------------------------------------------------

    def _settings(self):
        logger.info("托盘: 打开设置")
        self._on_settings()

    def _toggle_pause(self):
        self._paused = not self._paused
        logger.info("托盘: %s翻译热键", "暂停" if self._paused else "恢复")
        self._on_pause(self._paused)
        self._refresh()

    def _exit(self):
        logger.info("托盘: 退出程序")
        self._on_exit()

    # -- 对外接口 ---------------------------------------------------------

    def set_paused(self, paused):
        self._paused = bool(paused)
        self._refresh()

    def _refresh(self):
        try:
            self._icon.update_menu()
        except Exception:
            logger.debug("刷新托盘菜单失败", exc_info=True)

    def notify(self, message, title=APP_TITLE):
        """弹出气泡提示; 不支持时静默忽略。"""
        try:
            self._icon.notify(message, title)
        except Exception:
            logger.debug("托盘气泡提示不可用", exc_info=True)

    def start(self):
        """在后台线程启动托盘图标 (主线程要继续跑 tkinter)。"""
        self._icon.run_detached()
        logger.info("托盘图标已启动")

    def stop(self):
        try:
            self._icon.stop()
        except Exception:
            logger.debug("停止托盘图标失败", exc_info=True)
        logger.info("托盘图标已停止")
