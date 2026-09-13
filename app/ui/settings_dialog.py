"""密钥配置对话框。

取代「把 .env 放到 exe 旁边」的手工操作: 首次运行缺少凭据时弹出本对话框,
填好后保存到 %APPDATA%\\transpy\\config.ini; 之后也可以通过托盘菜单重新打开。

所有 tkinter 操作都在主线程完成, 只有耗时的连通性测试放到后台线程, 结果
通过轮询队列回到主线程。
"""

import logging
import queue
import threading
import tkinter as tk
from tkinter import ttk

logger = logging.getLogger(__name__)

FIELDS = (
    ("ak", "Access Key (AK)"),
    ("sk", "Secret Key (SK)"),
    ("project_id", "Project ID"),
    ("region", "Region"),
)
SKIP_TEST_TEXT = "Hello"


class SettingsDialog(tk.Toplevel):
    """AK/SK/project_id/region 的编辑对话框。

    参数:
        values:   预填值 {ak, sk, project_id, region}
        on_save:  callable(dict) -> None, 用户点击保存时调用
        mandatory: 缺少凭据时启动的强制配置模式 (不提供取消按钮)
        on_cancel: callable() -> None, 强制模式下用户点关闭窗口时调用
        on_closed: callable() -> None, 对话框关闭 (保存/取消/关窗) 后调用,
                   传入后同时也会放开强制模式的关闭限制
    """

    def __init__(self, master, values, on_save, mandatory=False, on_cancel=None,
                 on_closed=None):
        super().__init__(master)
        self.title("transpy 配置")
        self.resizable(False, False)
        self._on_save = on_save
        self._on_cancel = on_cancel
        self._on_closed = on_closed
        self._mandatory = mandatory
        self._queue = queue.Queue()
        self._testing = False
        self._closing = False
        self._poll_id = None

        self._vars = {key: tk.StringVar(value=values.get(key, "") or "") for key, _ in FIELDS}
        self._status = tk.StringVar(value="")

        self._build_widgets()
        self._center()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._schedule_poll()

        # 回车直接保存、Esc 关闭 (非强制模式): 填完最后一项按回车是最自然的操作,
        # 否则光标停在输入框里按回车毫无反应。
        self.bind("<Return>", lambda _e: self._save())
        self.bind("<KP_Enter>", lambda _e: self._save())
        self.bind("<Escape>", lambda _e: self._on_close())

        self.lift()
        try:
            self.attributes("-topmost", True)
            self.grab_set()
        except tk.TclError:
            pass
        self._entries["ak"].focus_set()

    # -- 界面构建 ---------------------------------------------------------

    def _build_widgets(self):
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text=(
                "填写华为云 NLP 服务的凭据, 保存后写入用户配置目录,\n"
                "无需再把 .env 放到程序旁边。"
            ),
            justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self._entries = {}
        for index, (key, label) in enumerate(FIELDS, start=1):
            ttk.Label(frame, text=label).grid(row=index, column=0, sticky="e", padx=(0, 8), pady=3)
            entry = ttk.Entry(frame, textvariable=self._vars[key], width=46)
            if key == "sk":
                entry.configure(show="*")
            entry.grid(row=index, column=1, sticky="we", pady=3)
            self._entries[key] = entry

        ttk.Label(frame, textvariable=self._status, foreground="#0a6").grid(
            row=len(FIELDS) + 1, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

        buttons = ttk.Frame(frame)
        buttons.grid(row=len(FIELDS) + 2, column=0, columnspan=2, sticky="e", pady=(12, 0))

        self._test_button = ttk.Button(buttons, text="测试连接", command=self._test)
        self._test_button.pack(side="left", padx=(0, 6))

        self._save_button = ttk.Button(buttons, text="保存", command=self._save)
        self._save_button.pack(side="left", padx=(0, 6))

        if not self._mandatory:
            ttk.Button(buttons, text="取消", command=self._on_close).pack(side="left")

    def _center(self):
        self.update_idletasks()
        width, height = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() - width) // 2
        y = (self.winfo_screenheight() - height) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    # -- 交互 -------------------------------------------------------------

    def _values(self):
        return {key: var.get().strip() for key, var in self._vars.items()}

    def _set_busy(self, busy, message=""):
        self._testing = busy
        state = "disabled" if busy else "normal"
        self._test_button.configure(state=state)
        self._save_button.configure(state=state)
        self._status.set(message)

    def _test(self):
        """在后台线程验证凭据, 结果回到主线程显示。"""
        if self._testing:
            return
        values = self._values()
        if not (values["ak"] and values["sk"] and values["project_id"]):
            self._status.set("请先填写 AK / SK / Project ID")
            return

        self._set_busy(True, "正在测试连接 ...")

        def worker():
            try:
                from ..config import Config
                from ..translator import Translator

                translator = Translator(
                    Config(
                        ak=values["ak"],
                        sk=values["sk"],
                        project_id=values["project_id"],
                        region=values["region"] or "cn-north-4",
                    )
                )
                translator.translate(SKIP_TEST_TEXT)
                self._queue.put((True, "连接成功, 凭据可用"))
            except Exception as exc:  # 网络/鉴权错误都要展示给用户
                logger.warning("测试连接失败: %s", exc)
                self._queue.put((False, f"连接失败: {exc}"))

        threading.Thread(target=worker, name="transpy-settings-test", daemon=True).start()

    def _poll(self):
        """主线程轮询后台测试结果。

        这里必须自己管住 after 链: 窗口被销毁后仍在排队的回调会以
        "invalid command name ..._poll" 的形式抛出 Tcl 错误, 严重时会让
        首次配置流程挂住。
        """
        self._poll_id = None
        if self._closing:
            return
        try:
            exists = bool(self.winfo_exists())
        except tk.TclError:
            return
        if not exists:
            return

        try:
            ok, message = self._queue.get_nowait()
        except queue.Empty:
            self._schedule_poll()
            return

        self._set_busy(False, message)
        if not ok:
            self.lift()
        self._schedule_poll()

    def _schedule_poll(self):
        if self._closing:
            return
        try:
            self._poll_id = self.after(80, self._poll)
        except tk.TclError:
            self._poll_id = None

    def _save(self):
        values = self._values()
        if not (values["ak"] and values["sk"] and values["project_id"]):
            self._status.set("AK / SK / Project ID 都不能为空")
            return
        try:
            self._on_save(values)
        except Exception as exc:
            logger.exception("保存配置失败")
            self._status.set(f"保存失败: {exc}")
            return
        # 回调里可能会连带销毁承载窗口, 关闭自身要容错
        self._close()

    def _on_close(self):
        # 允许关窗的条件: 已经指定了收尾回调 (会由调用方决定后续), 或者非强制模式
        if self._mandatory and self._on_cancel is None and self._on_closed is None:
            self._status.set("必须填写完整配置才能使用 transpy")
            self.bell()
            return
        if self._mandatory and self._on_cancel is not None:
            self._on_cancel()
        self._close()

    def _close(self):
        if self._closing:
            return
        self._closing = True

        # 先撤掉待执行的轮询, 再销毁窗口, 避免残留 after 回调报 Tcl 错误
        if self._poll_id is not None:
            try:
                self.after_cancel(self._poll_id)
            except tk.TclError:
                pass
            self._poll_id = None

        try:
            self.grab_release()
        except tk.TclError:
            pass
        try:
            self.destroy()
        except tk.TclError:
            pass
        if self._on_closed is not None:
            try:
                self._on_closed()
            except Exception:
                logger.exception("执行关闭回调失败")


def setup_first_run(root, defaults=None, on_save=None, on_closed=None,
                    on_cancel=None):
    """首次运行时的配置向导。

    这里刻意使用一个「可见」的临时窗口而不是隐藏窗口来承载对话框:
    隐藏 (withdraw) 的窗口作为 MessageBox 的 owner 时, 弹窗可能不显示或跑到
    屏幕外, 首次配置就会表现为"卡住" —— 全新用户看不到任何界面。

    参数:
        on_save:   callable(dict) -> None, 保存时先写盘
        on_closed: callable() -> None, 对话框关闭后调用 (无论保存还是取消)
        on_cancel: callable() -> None, 仅在用户取消/关窗时调用

    返回承载用的临时窗口对象, 由调用方持有。
    """
    defaults = defaults or {}

    transient = tk.Toplevel(root)
    transient.title("transpy 初始化")
    transient.resizable(False, False)
    tk.Label(
        transient,
        text="transpy 需要华为云 NLP 凭据才能工作。\n"
             "填写一次后会保存在你的用户目录中, 以后无需再配置。",
        justify="left",
        padx=16,
        pady=16,
    ).pack()

    def _saved(values):
        if on_save is not None:
            on_save(values)

    def _closed():
        if on_closed is not None:
            on_closed()

    SettingsDialog(
        transient,
        defaults,
        on_save=_saved,
        mandatory=True,
        on_cancel=on_cancel,
        on_closed=_closed,
    )
    return transient
