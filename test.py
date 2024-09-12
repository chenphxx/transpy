import tkinter
import pyperclip


result = "hello world"

def copy_and_clos():
    pyperclip.copy(label.cget("text"))  # 复制
    window.destroy()  # 关闭

window = tkinter.Tk()
window.minsize(240, 100)  # 窗口最小尺寸, 保证正常显示logo和标题
window.title("翻译结果")  # 窗口标题
# window.configure(bg="#ADD8E6")  # 背景颜色
window.iconbitmap("source/logo.ico")  # 图标

# lael result
label = tkinter.Label(window, text=result, wraplength=340, font=("Cascadia Code", 12))
label.pack(pady=12)

# button copy_and_close
button = tkinter.Button(window, text="复制并关闭", command=copy_and_clos)
button.pack(pady=10)

if __name__ == "__main__":
    window.mainloop()
