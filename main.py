"""transpy 启动入口。

启动顺序有讲究:
    1. 单实例检测 —— 避免双击多次导致多个键盘钩子各弹各的窗口;
    2. 设置 AppUserModelID —— 让翻译弹窗在任务栏使用本程序图标;
    3. 初始化日志 —— 之后所有异常都有迹可循;
    4. 配置缺失时弹首次配置向导, 而不是静默退出;
    5. tkinter 占用主线程, 热键监听与托盘图标在各自的后台线程。
"""

import logging
import sys
import tkinter as tk

from app import constants, errors, logging_setup, storage, win32
from app.config import Config
from app.constants import APP_TITLE

logger = logging.getLogger("transpy")


class Application:
    """进程级应用对象: 负责单实例、配置与运行上下文的组装。"""

    def __init__(self, selftest_seconds=None):
        self.context = None
        self._activation_server = None
        self.selftest_seconds = selftest_seconds

    # -- 启动 -------------------------------------------------------------

    def run(self):
        if not win32.acquire_single_instance():
            win32.notify_existing_instance()
            logger.info("已有实例在运行, 本实例退出")
            self._notify_already_running()
            return 0

        win32.set_app_user_model_id()
        logging_setup.install_excepthook()

        # 第二个实例启动时会被唤起, 直接打开配置对话框
        self._activation_server = win32.start_activation_server(
            lambda: self.context and self.context.post("show_settings")
        )

        try:
            config = storage.load()
        except storage.MissingConfigError as exc:
            logger.info("未找到完整凭据, 进入首次配置流程: %s", exc)
            try:
                config = self._first_run_setup()
            except Exception:
                # 冻结环境里这里最容易出问题, 务必留下完整堆栈
                logger.exception("首次配置流程失败")
                config = None

        if config is None:
            self._notify_not_configured()
            logger.info("用户未完成配置, 退出")
            self._cleanup()
            return 1

        return self._serve(config)

    @staticmethod
    def _hold_dialog(title, message, error=False):
        """在 mainloop 之外弹一个提示框 (自己起一个临时 root 并等它关掉)。"""
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        try:
            if error:
                errors.show_error(title, message, parent=root)
            else:
                errors.show_info(title, message, parent=root)
        finally:
            try:
                root.destroy()
            except tk.TclError:
                pass

    def _notify_already_running(self):
        self._hold_dialog(
            APP_TITLE,
            "transpy 已经在运行了。\n\n"
            "请在系统托盘 (任务栏右下角, 可能在 ^ 折叠区) 找到它的图标进行设置或退出。",
        )

    def _notify_not_configured(self):
        self._hold_dialog(
            APP_TITLE,
            "尚未完成配置, transpy 无法启动。\n"
            "下次运行时会再次提示你填写华为云 NLP 凭据。",
        )

    def _first_run_setup(self):
        """弹出首次配置向导, 保存成功后返回 Config, 取消则返回 None。"""
        import tkinter as tk

        from app.ui.settings_dialog import setup_first_run

        # 已有 config.ini 但缺项时, 把已有值预填进表单
        ini = storage._read_ini(storage.config_path())
        outcome = {"config": None, "cancelled": False}

        # 根窗口隐藏: 说明信息由 setup_first_run 创建的引导窗口呈现。
        # 更早的版本用 MessageBox 做前导提示, 而它在 windowed 打包进程里
        # 无法作为可靠交互手段, 因此不再使用。
        root = tk.Tk()
        root.title(f"{APP_TITLE} 初始化")
        root.withdraw()
        logger.info("首次配置: 已创建引导窗口")

        def on_save(values):
            try:
                config = Config(
                    ak=values["ak"],
                    sk=values["sk"],
                    project_id=values["project_id"],
                    region=values["region"] or constants.REGION,
                )
                storage.save(config)
            except Exception:
                logger.exception("首次配置: 保存失败")
                raise
            outcome["config"] = config
            logger.info("配置已保存到 %s", storage.config_path())

        def on_closed():
            # 保存、取消或直接关窗都从这里统一收尾
            try:
                root.quit()
            except tk.TclError:
                pass

        window = setup_first_run(
            root,
            defaults={key: ini.get(key.upper(), "") for key in
                      ("ak", "sk", "project_id", "region")},
            on_save=on_save,
            on_closed=on_closed,
            on_cancel=lambda: outcome.update(cancelled=True),
        )
        logger.info("首次配置: 向导窗口已创建 (%s)", type(window).__name__)

        try:
            root.mainloop()
        except Exception as exc:
            errors.show_exception(APP_TITLE, exc, context="首次配置失败", parent=root)

        logger.info(
            "首次配置向导已结束 (saved=%s, cancelled=%s)",
            outcome["config"] is not None,
            outcome["cancelled"],
        )

        for widget in (window, root):
            try:
                widget.destroy()
            except tk.TclError:
                pass

        if outcome["cancelled"] and outcome["config"] is None:
            return None
        return outcome["config"]

    # -- 常驻运行 ---------------------------------------------------------

    def _serve(self, config):
        from app.appcontext import AppContext

        def on_settings_save(values):
            """对话框保存后写盘, 并同步到当前上下文。"""
            updated = Config(
                ak=values["ak"],
                sk=values["sk"],
                project_id=values["project_id"],
                region=values["region"] or constants.REGION,
            )
            storage.save(updated)
            logger.info("配置已更新: %s", storage.config_path())
            self.context.config = updated

        self.context = AppContext(
            config,
            on_settings_save=on_settings_save,
            on_exit=self._cleanup,
        )

        logger.info("transpy 已就绪: 选中文本后连续按两次 Ctrl 触发翻译")
        self.context.start()
        self._schedule_selftest()
        self.context.run()  # 阻塞, 直到托盘菜单选择退出

        logger.info("transpy 已退出")
        return 0

    def _schedule_selftest(self):
        """`--selftest[=秒数]`: 常驻若干秒后自动走一次与托盘退出完全相同的路径。

        打包后没有终端可交互, 又不可能在自动化里点击托盘菜单, 因此用它来
        验证「启动 -> 常驻 -> 干净退出」这条链路, 避免只能靠任务管理器收尾。
        """
        if self.selftest_seconds is None:
            return
        logger.info("自检模式: %s 秒后自动退出", self.selftest_seconds)
        self.context.root.after(
            int(self.selftest_seconds * 1000),
            lambda: self.context.post("exit"),
        )

    # -- 清理 -------------------------------------------------------------

    def _cleanup(self):
        server, self._activation_server = self._activation_server, None
        if server is not None:
            try:
                server.close()
            except OSError:
                pass


def _parse_selftest(argv):
    """解析 --selftest[=秒数]; 未启用时返回 None。"""
    for arg in argv:
        if arg == "--selftest":
            return 6.0
        if arg.startswith("--selftest="):
            try:
                return max(1.0, float(arg.split("=", 1)[1]))
            except ValueError:
                return 6.0
    return None


def _seed_selftest_config():
    """自检模式且完全没有凭据时, 造一份临时凭据。

    这样 --selftest 不依赖用户是否配置过, 又能顺带验证"写配置"这条路径。
    """
    config = Config(
        ak="selftest-ak",
        sk="selftest-sk",
        project_id="selftest-project",
        region=constants.REGION,
    )
    storage.save(config)
    logger.info("自检模式: 已写入临时凭据到 %s", storage.config_path())
    return config


def main(argv=None):
    """进程入口, 返回退出码。"""
    argv = list(sys.argv[1:] if argv is None else argv)
    logging_setup.setup()
    selftest = _parse_selftest(argv)
    logger.info(
        "transpy 启动 (Python %s, frozen=%s, argv=%s)",
        sys.version.split()[0],
        bool(getattr(sys, "frozen", False)),
        argv or "-",
    )
    try:
        if selftest is not None:
            try:
                storage.load()
            except storage.MissingConfigError:
                _seed_selftest_config()
        return Application(selftest_seconds=selftest).run()
    except Exception as exc:
        errors.show_exception("transpy", exc, context="程序启动失败")
        return 1


def _flush_streams():
    """窗口模式下 sys.stdout/stderr 可能为 None (甚至整个属性都不存在)。"""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is not None:
            try:
                stream.flush()
            except (OSError, ValueError):
                pass


if __name__ == "__main__":
    _code = main()
    # 打包后没有终端, 自检结果要立即落盘; 同时把退出码明确交给系统
    _flush_streams()
    sys.exit(_code)