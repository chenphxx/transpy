from app.config import load
from app.hotkey import DoubleCtrlListener
from app.translator import Translator
from app.ui.result_window import ResultWindow


def show_result(text):
    # 结果弹窗 
    window = ResultWindow(text)
    window.mainloop()


def main():
    print("正在初始化 transpy ...")
    config = load()
    translator = Translator(config)
    listener = DoubleCtrlListener(translator, show_result)
    print("初始化完成, 选中文本后连续按下两次 Ctrl 进行翻译")
    listener.start()


if __name__ == "__main__":
    main()
