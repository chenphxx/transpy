"""运行配置的数据结构与加载入口。

密钥 (AK/SK/project_id) 的读取优先级与落点由 app.storage 负责, 见该模块
文档。这里只保留配置对象本身, 避免调用方关心具体来源。
"""

from dataclasses import dataclass

from . import constants
from .storage import ConfigError, MissingConfigError, load as _load  # noqa: F401

__all__ = ["Config", "ConfigError", "MissingConfigError", "load"]


@dataclass
class Config:
    ak: str
    sk: str
    project_id: str
    region: str = constants.REGION

    @property
    def endpoint(self):
        return f"https://nlp-ext.{self.region}.myhuaweicloud.com"


def load():
    """加载运行配置, 返回 Config。缺少凭据时抛出 MissingConfigError。"""
    return _load()
