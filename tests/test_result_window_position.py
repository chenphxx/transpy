"""测试: 翻译结果弹窗出现在光标处且不会超出屏幕

历史缺陷: 定位在控件布局之前、窗口显示之前就做了, 用的还是写死的 360x180
尺寸, 系统随后按默认级联位置摆放窗口, 弹窗跑到屏幕左上角附近, 不再跟随光标

运行 (在仓库根目录): python tests/test_result_window_position.py
"""

import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ui.result_window import (  # noqa: E402
    CURSOR_OFFSET,
    MARGIN,
    ResultWindow,
)

problems = []


def check_follows_pointer(root):
    """普通情况: 窗口左上角落在光标右下 CURSOR_OFFSET 处"""
    win = ResultWindow(root, "这是一段测试译文 hello world")
    win.update()

    px, py = win.winfo_pointerx(), win.winfo_pointery()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    x, y = win.winfo_x(), win.winfo_y()
    w, h = win.winfo_width(), win.winfo_height()
    print(f"  光标=({px},{py}) 窗口=({x},{y}) 尺寸={w}x{h} 屏幕={sw}x{sh}")

    if x + w > sw:
        problems.append("窗口超出屏幕右边界")
    if y + h > sh:
        problems.append("窗口超出屏幕下边界")

    at_right_below = (
        abs(x - (px + CURSOR_OFFSET)) <= 1 and abs(y - (py + CURSOR_OFFSET)) <= 1
    )
    flipped_to_left_above = x <= px and y <= py
    if not (at_right_below or flipped_to_left_above):
        problems.append(f"窗口没有出现在光标附近: 光标=({px},{py}) 窗口=({x},{y})")

    win.destroy()


def check_screen_corner(root):
    """光标在屏幕右下角: 窗口翻到左上并完整留在屏幕内"""

    class CornerWindow(ResultWindow):
        def winfo_pointerx(self):
            return self.winfo_screenwidth() - 2

        def winfo_pointery(self):
            return self.winfo_screenheight() - 2

    win = CornerWindow(root, "右下角测试")
    win.update()

    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    x, y = win.winfo_x(), win.winfo_y()
    w, h = win.winfo_width(), win.winfo_height()
    print(f"  右下角 屏幕={sw}x{sh} 窗口=({x},{y}) 尺寸={w}x{h}")

    if x < MARGIN or y < MARGIN:
        problems.append("窗口没有翻到光标的左上")
    if x + w > sw or y + h > sh:
        problems.append("窗口超出了屏幕边界")

    win.destroy()


def main():
    root = tk.Tk()
    root.withdraw()

    print("跟随光标:")
    for _ in range(3):
        check_follows_pointer(root)

    print("屏幕右下角:")
    check_screen_corner(root)

    root.destroy()

    if problems:
        print("失败:")
        for problem in problems:
            print("  -", problem)
        return 1
    print("通过: 弹窗跟随光标出现, 且不会超出屏幕")
    return 0


if __name__ == "__main__":
    sys.exit(main())
