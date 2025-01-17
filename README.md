## 关于项目

首先选中要翻译的文本, 随后连续按下两次`Ctrl`键, 触发翻译脚本, 翻译结果将以弹窗的形式呈现; 如果遇到问题, 例如软件未触发等, 可以尝试重启程序 

程序使用`pyinstaller`进行打包, 使用`pip install pyinstaller`命令来安装该模块 

## 打包

程序打包命令为 

```python
pyinstaller --clean --noconsole --onefile --icon=source/logo.ico --add-data "source/logo.ico;source" --name "transpy" main.py
```
