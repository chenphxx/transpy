"""运行配置与密钥加载。

密钥 (AK/SK) 的读取优先级: 环境变量 > 项目根目录 .env 文件 > 华为云下载的
IAM_transpy-accessKeys.csv。project_id 从环境变量或 .env 读取。
所有涉密文件均已被 .gitignore 忽略, 不会进入版本库。
"""

import os
from dataclasses import dataclass

from . import constants


class ConfigError(RuntimeError):
    """配置缺失或格式错误。"""


@dataclass
class Config:
    ak: str
    sk: str
    project_id: str
    region: str = constants.REGION

    @property
    def endpoint(self):
        return f"https://nlp-ext.{self.region}.myhuaweicloud.com"


def _project_root():
    """返回项目根目录 (app 包所在目录的上一级)。"""
    return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def _read_env_file(path):
    """读取 KEY=VALUE 样式的 .env 文件, 返回 dict。跳过注释与空行。"""
    env = {}
    if not os.path.isfile(path):
        return env
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env


def _read_access_key_csv(path):
    """从华为云下载的 accessKeys csv 读取 (ak, sk)。兼容带 BOM 的文件。"""
    import csv

    if not os.path.isfile(path):
        return None, None
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ak = (row.get("Access key ID") or "").strip()
            sk = (row.get("Secret access key") or "").strip()
            if ak and sk:
                return ak, sk
    return None, None


def load(env_file=".env"):
    """加载运行配置。

    优先级: 环境变量 > .env 文件 > IAM_transpy-accessKeys.csv (仅 AK/SK)。
    """
    base = _project_root()
    file_env = _read_env_file(os.path.join(base, env_file))

    region = (
        os.environ.get(f"{constants.ENV_PREFIX}REGION")
        or file_env.get("HUAWEI_REGION")
        or constants.REGION
    )

    ak = os.environ.get(f"{constants.ENV_PREFIX}AK") or file_env.get("HUAWEI_AK")
    sk = os.environ.get(f"{constants.ENV_PREFIX}SK") or file_env.get("HUAWEI_SK")
    if not ak or not sk:
        csv_ak, csv_sk = _read_access_key_csv(
            os.path.join(base, constants.CREDENTIAL_FILE)
        )
        ak = ak or csv_ak
        sk = sk or csv_sk

    project_id = (
        os.environ.get(f"{constants.ENV_PREFIX}PROJECT_ID")
        or file_env.get("HUAWEI_PROJECT_ID")
    )

    if not (ak and sk):
        raise ConfigError(
            "缺少 AK/SK。请设置 HUAWEI_AK/HUAWEI_SK 环境变量, 或在项目目录放置 "
            f"{constants.CREDENTIAL_FILE} 或本地 .env 文件。"
        )
    if not project_id:
        raise ConfigError(
            "缺少 project_id。请设置 HUAWEI_PROJECT_ID 环境变量, 或在 .env 中 "
            "填写 HUAWEI_PROJECT_ID。"
        )

    return Config(ak=ak, sk=sk, project_id=project_id, region=region)
