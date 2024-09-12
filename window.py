import tkinter
import pyperclip
import os
import sys


def resource_path(relative_path):
    # 根据是否打包，返回资源文件的绝对路径
    try:
        # PyInstaller 创建的临时文件夹路径
        base_path = sys._MEIPASS
    except Exception:
        # 未打包时使用当前路径
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# 在设置图标时使用 resource_path 函数
icon_path = resource_path("source/logo.ico")

# 弹窗类
class ResultWindow(tkinter.Tk):
    def __init__(self, result):
        super().__init__()
        self.minsize(240, 100)  # 最小尺寸, 确保正常显示logo和标题
        self.title("翻译结果")  # 窗口标题
        
        self.iconbitmap(icon_path)
        # 340像素时换行 字体Cascadia Code 大小12
        self.label = tkinter.Label(self, text=result, wraplength=340, font=("Cascadia Code", 12))
        self.label.pack(pady=7)
        
        # 复制并关闭
        self.copy_button = tkinter.Button(self, text="复制并关闭", command=self.copy_to_clipboard, font=("Cascadia Code", 10))
        self.copy_button.pack(pady=7)

    # button copy_and_close
    def copy_to_clipboard(self):
        pyperclip.copy(self.label.cget("text"))
        self.destroy()


if __name__ == "__main__":
    root.mainloop()
