"""运行配置与密钥加载。

密钥 (AK/SK) 的读取优先级: 环境变量 > 项目根目录 .env 文件 > 华为云下载的
IAM_transpy-accessKeys.csv。project_id 从环境变量或 .env 读取。
所有涉密文件均已被 .gitignore 忽略, 不会进入版本库。
"""

import os
import sys
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
    """返回源码运行时的项目根目录 (app 包所在目录的上一级)。"""
    return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def _candidate_dirs():
    """返回按优先级排序的配置查找目录。

    源码运行: 项目根目录 + 当前工作目录。
    打包运行: exe 所在目录 + 当前工作目录 (把密钥文件放到 exe 旁边即可)。
    """
    if getattr(sys, "frozen", False):
        dirs = [os.path.dirname(sys.executable)]
    else:
        dirs = [_project_root()]
    cwd = os.getcwd()
    if cwd not in dirs:
        dirs.append(cwd)
    return dirs


def _read_env_file(path):
    """读取 KEY=VALUE 样式的 .env 文件, 返回 dict。跳过注释与空行。"""
    env = {}
    if not os.path.isfile(path):
        return env
    with open(path, "r", encoding="utf-8-sig") as f:
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
    会依次在多个候选目录中查找 .env 与 CSV。
    """
    dirs = _candidate_dirs()

    # 合并各目录的 .env: 优先级高者优先, 缺失项用低优先级补足
    file_env = {}
    for d in dirs:
        for k, v in _read_env_file(os.path.join(d, env_file)).items():
            file_env.setdefault(k, v)

    def pick(name):
        return (
            os.environ.get(f"{constants.ENV_PREFIX}{name}")
            or file_env.get(f"HUAWEI_{name}")
        )

    region = pick("REGION") or constants.REGION
    ak = pick("AK")
    sk = pick("SK")
    project_id = pick("PROJECT_ID")

    # CSV 兜底 (仅 AK/SK): 在候选目录中依次查找
    if not ak or not sk:
        for d in dirs:
            csv_ak, csv_sk = _read_access_key_csv(
                os.path.join(d, constants.CREDENTIAL_FILE)
            )
            if csv_ak and csv_sk:
                ak = ak or csv_ak
                sk = sk or csv_sk
                break

    searched = " / ".join(dirs)

    if not (ak and sk):
        raise ConfigError(
            "缺少 AK/SK。请设置 HUAWEI_AK/HUAWEI_SK 环境变量, 或把 "
            f"{constants.CREDENTIAL_FILE} (或填好 AK/SK 的 .env) 放到以下任一目录: {searched}"
        )
    if not project_id:
        raise ConfigError(
            "缺少 project_id。请设置 HUAWEI_PROJECT_ID 环境变量, 或在 .env 中 "
            f"填写 HUAWEI_PROJECT_ID。查找目录: {searched}"
        )

    return Config(ak=ak, sk=sk, project_id=project_id, region=region)
