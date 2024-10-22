## 关于项目

首先选中要翻译的文本, 随后连续按下两次`Ctrl`键, 触发翻译脚本, 翻译结果将以弹窗的形式呈现 
<br>如果遇到问题, 例如软件未触发等, 可以尝试重启程序 

## 联系作者

如在使用过程中遇到任何问题, 欢迎联系开发者`chenphxx`进行反馈, 联系方式如下 

```
E-Mail: john201950@outlook.com
```

## 打包

如果对程序进行了更新, 可以使用下面这一行代码进行打包 

```python
pyinstaller --clean --noconsole --onefile --icon=source/logo.ico --add-data "source/logo.ico;source" --name "划词翻译" main.py
```
