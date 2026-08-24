# transpy

## 关于

一款基于华为云自然语言处理 (NLP) 的划词翻译桌面工具。选中要翻译的文本, 连续按下两次 `Ctrl`, 程序会自动复制文本、调用华为云机器翻译接口, 并以弹窗形式展示结果。

## 功能

- 自动识别源语言: 中文翻译为英文, 其他语言翻译为中文
- 处理日语含汉字时的语种误判
- 结果弹窗跟随鼠标位置, 支持一键复制并关闭
- 基于华为云 AK/SK 认证, 密钥保存在本地, 不进入版本库

## 依赖库

- Python 3.10+
- `pynput`: 监听/模拟按键 (`pip install pynput`)
- `pyperclip`: 剪贴板读写 (`pip install pyperclip`)
- `huaweicloudsdkcore` / `huaweicloudsdknlp`: 华为云 SDK (AK/SK 签名认证)
- `pyinstaller`: 打包 (`pip install pyinstaller`)

安装运行依赖:

```bash
pip install -r requirements.txt
```

## 配置密钥

密钥不写入代码。程序按以下优先级读取 `AK/SK`:

1. 环境变量 `HUAWEI_AK` / `HUAWEI_SK`
2. 项目根目录的 `.env` 文件 (参考 `.env.example`)
3. 华为云控制台下载的 `IAM_transpy-accessKeys.csv`

`project_id` 需通过环境变量 `HUAWEI_PROJECT_ID` 或 `.env` 文件提供。

## 运行

```bash
python main.py
```

## 打包

```bash
pyinstaller --clean --noconsole --onefile --name transpy \
  --icon assets/images/logo.ico \
  --add-data "assets/images/logo.ico;assets/images" \
  --exclude-module PyQt5 --exclude-module PySide2 --exclude-module PySide6 \
  --exclude-module PIL --exclude-module pymongo --exclude-module bson --exclude-module dnspython \
  main.py
```

> 提示: 华为云 SDK 会触发无关依赖 (Qt/Image 剪辑板后端, PyMongo 等) 被一起打包,
> 使用 `--exclude-module` 剔除后可大幅减小体积 (约从 100MB 降到 25MB)。

## 项目结构

```text
main.py                 # 入口: 加载配置并启动按键监听
app/                    # 应用包
  constants.py          # 全局常量与华为云服务区域
  config.py             # 密钥/配置加载
  auth.py               # 华为云 AK/SK 客户端构建
  translator.py         # NLP 文本翻译服务封装
  language.py           # 语言检测与翻译方向决策
  clipboard.py          # 剪贴板读写
  hotkey.py             # 双击 Ctrl 触发
  ui/result_window.py   # 结果弹窗
assets/images/          # 图标等资源
```
