# transpy

基于华为云 NLP 的划词翻译工具：选中需要翻译的文本，**连续按两次 `Ctrl`** 即可翻译。

- 中文默认翻译为英文
- 其他语言默认翻译为中文
- 程序常驻系统托盘，右键托盘图标可设置密钥、暂停热键或退出

## 安装运行依赖

```bash
pip install -r requirements.txt
```

## 配置密钥

**不需要再把配置文件放到 exe 旁边。** 首次运行缺少凭据时，程序会弹出配置
对话框，填写一次后保存在用户目录：

```
%APPDATA%\transpy\config.ini
```

之后可通过托盘菜单的「设置密钥...」随时修改，也可以在该对话框里点「测试连接」
立即验证凭据是否可用。

配置读取优先级（高 → 低）：

1. 环境变量 `HUAWEI_AK` / `HUAWEI_SK` / `HUAWEI_PROJECT_ID` / `HUAWEI_REGION`
2. `%APPDATA%\transpy\config.ini`（GUI 保存的主位置）
3. 程序所在目录的 `.env`（便携版 / 向后兼容，参考 `.env.example`）
4. 当前工作目录的 `.env`
5. 华为云控制台下载的 `IAM_transpy-accessKeys.csv`（只提供 AK/SK）

> 仍然支持把 `.env` 或 csv 放在 exe 同级目录（便携版用法），但不再是必须的。
> 环境变量优先级最高，适合 CI 或临时覆盖。

## 使用与退出

- 启动后程序**不会出现在任务栏**（它是无窗口的后台程序），而是在**系统托盘**
  （任务栏右下角，可能需要点 `^` 展开）显示图标。
- 托盘图标右键菜单：`设置密钥...` / `暂停翻译热键` / `退出`；双击图标打开设置。
- 托盘图标不可用时程序会弹窗提示，此时需通过任务管理器结束 `transpy.exe`。
- 重复双击 exe 不会启动多个实例：第二个实例会提示并在已有实例中打开设置窗口。

日志位于 `%LOCALAPPDATA%\transpy\logs\transpy.log`，反馈问题时可一并提供。

### 自检模式

想确认「启动 → 常驻 → 干净退出」这条链路是否正常（尤其是托盘图标是否创建成功），
可以带上 `--selftest` 运行，它会在若干秒后自动走一遍与托盘菜单「退出」完全相同的
路径并返回退出码 0。没有任何已有配置时，它会先写入一份临时凭据，因此可以直接在
干净环境里使用：

```bash
transpy.exe --selftest        # 默认 6 秒后自动退出
transpy.exe --selftest=3      # 指定秒数
```

正常输出（日志中）为：

```
transpy 已就绪: 选中文本后连续按两次 Ctrl 触发翻译
自检模式: 6.0 秒后自动退出
transpy 已退出
```

若出现「系统托盘图标初始化失败」的弹窗，说明托盘不可用，此时只能通过任务管理器退出。

## 打包

```bash
pyinstaller --noconfirm --clean transpy.spec
```

打包配置见 `transpy.spec`，与命令行方式相比多了三点：

- `datas` 带上 `assets/images/logo.ico`，保证打包后托盘图标可加载；
- **不能排除 `PIL`**（`pystray` 依赖它），否则托盘图标创建失败；
- 写入 `version_info.txt` 版本资源，任务栏与文件属性显示 transpy 而非 python。

产物为 `dist/transpy.exe`。
