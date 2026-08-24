"""应用全局常量与华为云服务配置 (非机密信息)。

注意: 此处仅存放区域、功能参数等可公开信息。AK/SK 密钥与 project_id 等
涉密信息由 app.config 单独加载, 不会写入版本库。
"""

APP_TITLE = "transpy"

# 华为云自然语言处理 (NLP) 服务区域。区域标识并非机密信息。
REGION = "cn-north-4"
SERVICE_ENDPOINT = f"https://nlp-ext.{REGION}.myhuaweicloud.com"

# 密钥来源文件名 (已加入 .gitignore, 不提交)
CREDENTIAL_FILE = "IAM_transpy-accessKeys.csv"
ENV_PREFIX = "HUAWEI_"

# 功能参数
MAX_TEXT_LENGTH = 2000          # API 单次可翻译的最大字符数
DOUBLE_PRESS_INTERVAL = 1.0     # 两次 Ctrl 之间的最大间隔 (秒)
COPY_SETTLE_TIME = 0.05         # 复制后等待剪贴板刷新的时间 (秒)

# 默认目标语言规则: 中文 -> 英文, 其他 -> 中文
TARGET_LANG_WHEN_ZH = "en"
TARGET_LANG_OTHERWISE = "zh"

# 图标资源路径 (相对项目根目录)
ICON_PATH = "assets/images/logo.ico"
