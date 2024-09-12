import pynput
import time
import keyboard

import translator  # 华为NLP翻译API
import window  # 提供了弹窗类


token = translator.get_iam_token()
first_press = None

def on_press(key):
    global first_press
    if key == pynput.keyboard.Key.ctrl_l or key == pynput.keyboard.Key.ctrl_r:
        current_time = time.time()
        if first_press is None:
            # 第一次按下Ctrl的时间
            first_press = current_time
        else:
            temp_time = current_time - first_press  # 间隔时间内是否第二次按下Ctrl
            if temp_time < 1:  # 两次按下的间隔（秒）
                print("检测到连续按下两次Ctrl")
                keyboard.send('ctrl+c')
                time.sleep(0.01)  # 延迟10毫秒, 确保剪贴板更新

                # 翻译并显示结果
                result = translator.nlp_demo(token).json()  # 翻译API
                print(result)
                try:
                    windows = window.ResultWindow(result["translated_text"])
                    windows.mainloop()
                except:
                    print("出错了, 请重试")
                    message = "error_code: " + result["error_code"] + "\n" + result["error_msg"]
                    windows = window.ResultWindow(message)
                    windows.mainloop()

            first_press = None   # 重置时间

# 开始监听按键事件
with pynput.keyboard.Listener(on_press=on_press) as listener:
    print("按下两次Ctrl来触发翻译")
    listener.join()
