"""测试: 首次配置向导的完整流程。

覆盖三条链路 (不依赖华为云网络与真实键盘/托盘):
    A. 全新用户 + 已填写: 向导出现 -> 保存 -> 写 config.ini -> 继续常驻启动;
    B. 全新用户 + 取消: 向导关闭 -> run() 返回 1, 不写 config.ini;
    C. 全新用户 + 关闭窗口: 行为同 B (不能卡死/不能留下 Tcl 报错)。

注意: 必须在导入 app 之前把 cwd 切到沙箱, 否则 legacy_dirs() 会找到
项目根目录的 .env / csv, 变成"已有凭据"的场景而不是首次运行。

运行 (在仓库根目录): python tests/test_firstrun.py <A|B|C>
"""

import os
import shutil
import sys
import tempfile
import time
import tkinter as tk

# 允许从仓库根目录运行本文件
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 必须在导入 app 之前隔离配置目录与工作目录
SANDBOX = tempfile.mkdtemp(prefix="transpy-firstrun-")
os.environ["APPDATA"] = os.path.join(SANDBOX, "appdata")
os.environ["LOCALAPPDATA"] = os.path.join(SANDBOX, "local")
for name in ("HUAWEI_AK", "HUAWEI_SK", "HUAWEI_PROJECT_ID", "HUAWEI_REGION"):
    os.environ.pop(name, None)
os.chdir(SANDBOX)

from app import storage  # noqa: E402

# 源码运行时 app_root() 始终是项目根目录 (那里有 .env 和 csv),
# 因此这里把兼容来源一并指向沙箱, 才是真正的"全新用户"场景
storage.legacy_dirs = lambda: [SANDBOX]

import app.appcontext as appcontext  # noqa: E402
import main as main_module  # noqa: E402


def run_case(case):
    from app.ui.settings_dialog import SettingsDialog

    # 前置自检: 这个沙箱必须真的是"没有凭据"的场景
    try:
        cfg = storage.load()
        print(f"[{case}] !! 沙箱里竟然加载到了凭据, 测试无效 (ak len={len(cfg.ak)})")
        print(f"[{case}]    legacy_dirs = {storage.legacy_dirs()}")
        print(f"[{case}]    config_path = {storage.config_path()}")
    except storage.MissingConfigError as exc:
        print(f"[{case}] 前置自检通过: 无凭据 ({exc})")

    seen = {"dialog": None}
    original_init = SettingsDialog.__init__

    def patched_init(self, master, values, *args, **kwargs):
        original_init(self, master, values, *args, **kwargs)
        seen["dialog"] = self

        def act():
            if case == "A":
                for key, value in (
                    ("ak", "A" * 20),
                    ("sk", "S" * 40),
                    ("project_id", "P" * 32),
                    ("region", "cn-north-4"),
                ):
                    self._vars[key].set(value)
                # 跳过"测试连接"(需要网络), 直接保存
                self._save()
            elif case == "B":
                self._on_close()
            else:
                # 走与点击窗口关闭按钮完全相同的代码路径 (WM_DELETE_WINDOW 的处理器)
                self._on_close()

        self.after(250, act)

    SettingsDialog.__init__ = patched_init

    # 向导前的提示 MessageBox 会阻塞自动化, 直接跳过弹窗 (要单独人工验证外观)
    main_module.errors.show_info = lambda *a, **k: None

    # 不启动真实热键监听与托盘 (避免占用全局键盘 / 污染通知区域)
    appcontext.AppContext._start_listener = lambda self: None
    appcontext.AppContext._start_tray = lambda self: None

    # 关掉翻译结果窗口, 让常驻流程没有 UI 干扰即可退出
    class NoopWindow(tk.Toplevel):
        def __init__(self, master, result, title="翻译结果"):
            super().__init__(master)

    appcontext.ResultWindow = NoopWindow

    app = main_module.Application()

    # 真正走 run() -> _serve() 的完整链路, 只把"进入 mainloop 后自动退出"加进去,
    # 避免常驻流程永久阻塞
    original_run = appcontext.AppContext.run

    def auto_exit_run(self):
        self.root.after(1200, lambda: self.post("exit"))
        return original_run(self)

    appcontext.AppContext.run = auto_exit_run

    start = time.monotonic()
    try:
        code = app.run()
    except Exception as exc:
        print(f"[{case}] 运行异常: {exc!r}")
        code = -1
    elapsed = time.monotonic() - start

    print(f"[{case}] 向导是否弹出 = {seen['dialog'] is not None}")
    print(f"[{case}] 退出码 = {code}, 耗时 = {elapsed:.1f}s")
    print(f"[{case}] config.ini 存在 = {os.path.isfile(storage.config_path())}")

    expected = {
        "A": (True, 0),
        "B": (False, 1),
        "C": (False, 1),
    }[case]
    exists, want_code = expected

    ok = True
    if seen["dialog"] is None:
        print(f"[{case}] 失败: 首次配置向导没有弹出")
        ok = False
    if os.path.isfile(storage.config_path()) != exists:
        print(f"[{case}] 失败: config.ini 存在性与预期不符")
        ok = False
    if code != want_code:
        print(f"[{case}] 失败: 退出码 {code} != 期望 {want_code}")
        ok = False
    if elapsed > 30:
        print(f"[{case}] 失败: 耗时过长, 可能卡住")
        ok = False

    if ok and exists:
        import configparser

        parser = configparser.ConfigParser()
        parser.read(storage.config_path(), encoding="utf-8")
        print(f"[{case}] 写入内容: {dict(parser['huawei'])}")

    print(f"[{case}] {'通过' if ok else '未通过'}")
    return 0 if ok else 1


if __name__ == "__main__":
    case = sys.argv[1] if len(sys.argv) > 1 else "A"
    try:
        exit_code = run_case(case)
    finally:
        # 清理本次沙箱, 避免在 %TEMP% 里堆积
        os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        shutil.rmtree(SANDBOX, ignore_errors=True)
    sys.exit(exit_code)
