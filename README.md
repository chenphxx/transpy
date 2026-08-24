# transpy

## 关于

基于华为NLP的划词翻译脚本软件, 选中需要翻译的文本, 双击`ctrl`即可触发翻译 

- 中文默认翻译为英文 

- 其他语言默认翻译为中文 

安装运行依赖:

```bash
pip install -r requirements.txt
```

## 配置密钥

密钥不写入代码, 程序按以下优先级读取 `AK/SK`:

1. 环境变量 `HUAWEI_AK` / `HUAWEI_SK` 
2. 项目根目录的 `.env` 文件 (参考 `.env.example`) 
3. 华为云控制台下载的 `IAM_transpy-accessKeys.csv` 

`project_id` 需通过环境变量 `HUAWEI_PROJECT_ID` 或 `.env` 文件提供 

> 打包后的 exe 运行时, 请在 exe 同级目录放置 `IAM_transpy-accessKeys.csv` (或
> 填好 `HUAWEI_AK`/`HUAWEI_SK`/`HUAWEI_PROJECT_ID` 的 `.env`)。程序会依次查找
> 「环境变量 → exe 目录 → 当前工作目录」。

## 打包

```bash
pyinstaller --clean --noconsole --onefile --name transpy --icon assets/images/logo.ico --add-data "assets/images/logo.ico;assets/images" --exclude-module PyQt5 --exclude-module PySide2 --exclude-module PySide6 --exclude-module PIL main.py
```
