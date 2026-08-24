"""华为云 SDK 认证与客户端构建。"""

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdknlp.v2.nlp_client import NlpClient
from huaweicloudsdknlp.v2.region.nlp_region import NlpRegion

from .config import Config


class AuthError(RuntimeError):
    """认证失败。"""


def build_client(config: Config) -> NlpClient:
    """基于 AK/SK 构建 NLP 客户端。"""
    if not config.ak or not config.sk:
        raise AuthError("认证信息为空, 无法构建客户端。")
    credentials = BasicCredentials(config.ak, config.sk, config.project_id)
    return (
        NlpClient.new_builder()
        .with_credentials(credentials)
        .with_region(NlpRegion.value_of(config.region))
        .build()
    )
