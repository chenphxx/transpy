"""应用全局常量与华为云服务配置 (非机密信息)。

注意: 此处仅存放区域、功能参数等可公开信息。AK/SK 密钥与 project_id 等
涉密信息由 app.storage 单独加载, 不会写入版本库。
"""

APP_TITLE = "transpy"
APP_TIP = "transpy 运行中 · 双击 Ctrl 翻译"

# 华为云自然语言处理 (NLP) 服务区域。区域标识并非机密信息。
REGION = "cn-north-4"
SERVICE_ENDPOINT = f"https://nlp-ext.{REGION}.myhuaweicloud.com"

# 凭据来源文件名
CREDENTIAL_FILE = "IAM_transpy-accessKeys.csv"   # 华为云控制台下载的 csv
CONFIG_FILE_NAME = "config.ini"                  # %APPDATA%\transpy 下的主配置
LEGACY_ENV_FILE = ".env"                         # 便携版 / 向后兼容
ENV_PREFIX = "HUAWEI_"

# 功能参数
MAX_TEXT_LENGTH = 2000          # API 单次可翻译的最大字符数
DOUBLE_PRESS_INTERVAL = 1.0     # 两次 Ctrl 之间的最大间隔 (秒)
CTRL_REPEAT_GAP = 0.5           # 小于该间隔的重复 Ctrl 按下判定为长按自动重复 (秒)
COPY_SETTLE_TIME = 0.05         # 复制后等待剪贴板刷新的时间 (秒)
UI_POLL_INTERVAL_MS = 60        # 主线程轮询后台任务的间隔 (毫秒)

# 默认目标语言规则: 中文 -> 英文, 其他 -> 中文
TARGET_LANG_WHEN_ZH = "en"
TARGET_LANG_OTHERWISE = "zh"

# 图标资源路径 (相对项目根目录)
ICON_PATH = "assets/images/logo.ico"
