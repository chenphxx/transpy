"""日志初始化。

GUI 模式下没有控制台, print() 的内容会消失。这里做两件事:

1. 把日志写入 %LOCALAPPDATA%\\transpy\\logs\\transpy.log (按大小轮转);
2. 若确实没有可用的 stdout/stderr, 把 print 重定向到日志, 保留现有
   print 代码的可见性。

日志目录不可写时自动降级为只输出到 stderr, 不影响程序启动。
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from .paths import ensure_dir, user_log_dir

LOGGER_NAME = "transpy"
_LOG_FILE = "transpy.log"
_MAX_BYTES = 512 * 1024
_BACKUP_COUNT = 2


def log_file_path():
    return os.path.join(user_log_dir(), _LOG_FILE)


class _StreamToLogger:
    """把被重定向的 stdout/stderr 逐行转投到 logger。"""

    def __init__(self, logger, level):
        self._logger = logger
        self._level = level
        self._buffer = ""

    def write(self, text):
        if not text:
            return 0
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line.strip():
                self._logger.log(self._level, line)
        return len(text)

    def flush(self):
        if self._buffer.strip():
            self._logger.log(self._level, self._buffer)
        self._buffer = ""

    def isatty(self):
        return False


def setup(level=logging.INFO):
    """配置根 logger, 返回 logger 实例。重复调用是安全的。

    处理器必须挂在 root 上: 各子模块用的是 logging.getLogger(__name__)
    (app.hotkey / app.tray / app.storage ...), 它们会向 root 传播。早先只给
    "transpy" 这一个 logger 配 handler 并关掉传播, 结果这些模块的 INFO
    日志在打包 (windowed) 环境里彻底消失, 排查问题时看不到任何线索。
    """
    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if not root.handlers:
        # 无控制台时 sys.stderr 可能为 None (pythonw / console=False)
        if sys.stderr is not None:
            stream = logging.StreamHandler(sys.stderr)
            stream.setFormatter(formatter)
            root.addHandler(stream)

        try:
            ensure_dir(user_log_dir())
            file_handler = RotatingFileHandler(
                log_file_path(),
                maxBytes=_MAX_BYTES,
                backupCount=_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError:
            # 日志写不了不是致命问题
            root.warning("无法创建日志文件, 仅输出到标准错误")

    # 第三方库的 INFO 太吵, 只保留告警以上
    for noisy in ("PIL", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logger = logging.getLogger(LOGGER_NAME)

    # 打包运行且无 stderr 时, print() 会丢失, 重定向到日志
    if getattr(sys, "frozen", False) and sys.stderr is None:
        sys.stdout = _StreamToLogger(logger, logging.INFO)
        sys.stderr = _StreamToLogger(logger, logging.ERROR)

    return logger


def install_excepthook():
    """把未捕获异常写进日志, 避免静默死亡时无迹可寻。"""
    logger = logging.getLogger(LOGGER_NAME)

    def _hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            return
        logger.critical("未捕获异常", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = _hook

    # 后台线程里的异常默认只打印到 stderr, 同样收进日志
    try:
        from threading import excepthook as _thread_hook

        def _thread_excepthook(args):
            if issubclass(args.exc_type, SystemExit):
                return
            logger.error(
                "后台线程 %s 未捕获异常",
                getattr(args.thread, "name", "?"),
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )

        _thread_hook(_thread_excepthook)
    except Exception:
        pass
