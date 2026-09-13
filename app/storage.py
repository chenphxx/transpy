"""用户级配置的读写。

配置主落点是 `%APPDATA%\\transpy\\config.ini`, 用户无需关心程序被装在哪里,
也不需要手工编辑文件 —— 首次运行会弹出配置对话框, 保存即写入该文件。

读取优先级 (高 -> 低):
    1. 环境变量 HUAWEI_AK / HUAWEI_SK / HUAWEI_PROJECT_ID / HUAWEI_REGION
    2. %APPDATA%\\transpy\\config.ini        (GUI 保存, 主要落点)
    3. 程序所在目录的 .env                   (便携版 / 向后兼容)
    4. 当前工作目录的 .env
    5. IAM_transpy-accessKeys.csv            (只提供 AK/SK)

所有落点都找不到时抛出 MissingConfigError, 由上层弹出配置对话框。
"""

import configparser
import csv
import logging
import os

from . import constants
from .paths import app_root, ensure_dir, user_data_dir

logger = logging.getLogger(__name__)

SECTION = "huawei"


class ConfigError(RuntimeError):
    """配置缺失或格式错误。"""


class MissingConfigError(ConfigError):
    """未找到可用的凭据, 需要引导用户配置。

    attributes 里带上已搜索过的位置, 便于在对话框/日志中说明。
    """

    def __init__(self, message, searched=()):
        super().__init__(message)
        self.searched = tuple(searched)


def config_path():
    """返回 config.ini 的完整路径 (不保证文件已存在)。"""
    return os.path.join(user_data_dir(), constants.CONFIG_FILE_NAME)


def _read_ini(path):
    """读取 config.ini, 返回 {key: value}; 文件不存在或损坏时返回 {}。"""
    if not os.path.isfile(path):
        return {}
    parser = configparser.ConfigParser()
    try:
        parser.read(path, encoding="utf-8")
    except (configparser.Error, OSError, UnicodeDecodeError):
        # 配置损坏不应让程序无法启动, 走后续兜底来源
        return {}
    if not parser.has_section(SECTION):
        return {}
    return {k.upper(): (v or "").strip() for k, v in parser.items(SECTION)}


def _read_env_file(path):
    """读取 KEY=VALUE 样式的 .env 文件, 返回 dict。跳过注释与空行。"""
    env = {}
    if not os.path.isfile(path):
        return env
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    except OSError:
        return {}
    return env


def _read_access_key_csv(path):
    """从华为云下载的 accessKeys csv 读取 (ak, sk)。兼容带 BOM 的文件。"""
    if not os.path.isfile(path):
        return None, None
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ak = (row.get("Access key ID") or "").strip()
                sk = (row.get("Secret access key") or "").strip()
                if ak and sk:
                    return ak, sk
    except (OSError, csv.Error, UnicodeDecodeError):
        return None, None
    return None, None


def legacy_dirs():
    """返回兼容来源的查找目录 (程序目录 + 当前工作目录)。"""
    dirs = [app_root()]
    cwd = os.getcwd()
    if cwd not in dirs:
        dirs.append(cwd)
    return dirs


def load():
    """加载运行配置, 返回 Config。缺少凭据时抛出 MissingConfigError。"""
    from .config import Config  # 延迟导入, 避免与 config 模块循环依赖

    ini_path = config_path()
    ini = _read_ini(ini_path)

    # 收集兼容来源的 .env, 先出现者优先
    dirs = legacy_dirs()
    file_env = {}
    for d in dirs:
        for k, v in _read_env_file(os.path.join(d, ".env")).items():
            file_env.setdefault(k, v)

    searched = (ini_path,) + tuple(os.path.join(d, ".env") for d in dirs)

    def pick(name):
        """按 环境变量 -> config.ini -> .env 的顺序取值, 并记录来源。"""
        sources = (
            ("环境变量", os.environ.get(f"{constants.ENV_PREFIX}{name}")),
            (ini_path, ini.get(name)),
            (".env", file_env.get(f"{constants.ENV_PREFIX}{name}")),
        )
        for source, value in sources:
            if value:
                return value, source
        return None, None

    region, region_src = pick("REGION")
    ak, ak_src = pick("AK")
    sk, sk_src = pick("SK")
    project_id, project_src = pick("PROJECT_ID")
    region = region or constants.REGION

    # CSV 兜底 (仅 AK/SK): 在候选目录中依次查找
    csv_path = None
    if not ak or not sk:
        for d in dirs:
            candidate = os.path.join(d, constants.CREDENTIAL_FILE)
            csv_ak, csv_sk = _read_access_key_csv(candidate)
            if csv_ak and csv_sk:
                ak = ak or csv_ak
                sk = sk or csv_sk
                csv_path = candidate
                break

    # 记录凭据来源, 便于排查"为什么又要我配置"这类问题
    if ak and sk and project_id:
        logger.info(
            "凭据来源: AK/SK -> %s, project_id -> %s, region -> %s",
            ak_src or csv_path or "?",
            project_src,
            region_src or "默认值",
        )
    else:
        logger.warning(
            "未找到完整凭据 (AK: %s, SK: %s, project_id: %s); 已搜索: %s",
            ak_src or "缺失",
            sk_src or "缺失",
            project_src or "缺失",
            " / ".join(searched),
        )

    if not (ak and sk and project_id):
        missing = [
            name
            for name, value in (("AK", ak), ("SK", sk), ("PROJECT_ID", project_id))
            if not value
        ]
        raise MissingConfigError(
            "缺少配置项: " + ", ".join(f"HUAWEI_{m}" for m in missing),
            searched=searched,
        )

    return Config(ak=ak, sk=sk, project_id=project_id, region=region)


def save(config):
    """把配置写入 %APPDATA%\\transpy\\config.ini。"""
    path = config_path()
    ensure_dir(os.path.dirname(path))

    parser = configparser.ConfigParser()
    parser[SECTION] = {
        "AK": config.ak or "",
        "SK": config.sk or "",
        "PROJECT_ID": config.project_id or "",
        # 用 constants 的默认值, 避免把某个用户的区域写成全局默认
        "REGION": config.region or constants.REGION,
    }

    # 先写临时文件再替换, 避免写一半断电留下损坏的配置
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        parser.write(f)
    os.replace(tmp, path)
    return path


def clear():
    """删除 config.ini, 返回是否真的删除了文件。"""
    path = config_path()
    if os.path.isfile(path):
        try:
            os.remove(path)
            return True
        except OSError:
            return False
    return False
