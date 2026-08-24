"""华为云 NLP 文本翻译服务封装。"""

from huaweicloudsdknlp.v2.model import RunTextTranslationRequest, TextTranslationReq

from .auth import build_client
from .config import Config
from .constants import MAX_TEXT_LENGTH
from .language import detect_language, pick_direction


class TranslationError(RuntimeError):
    """翻译调用失败。"""


class Translator:
    """封装华为云 NLP 文本翻译接口。"""

    def __init__(self, config: Config):
        self.config = config
        self._client = build_client(config)

    def translate(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            raise TranslationError("待翻译文本为空。")
        if len(text) > MAX_TEXT_LENGTH:
            raise TranslationError(f"文本过长 (超过 {MAX_TEXT_LENGTH} 字符)。")

        source = detect_language(text)
        src_lang, dst_lang = pick_direction(source)

        request = RunTextTranslationRequest(
            body=TextTranslationReq(
                text=text,
                _from=src_lang,
                to=dst_lang,
                scene="common",
            )
        )

        try:
            response = self._client.run_text_translation(request)
        except Exception as exc:
            raise TranslationError(f"调用翻译接口失败: {exc}") from exc

        if getattr(response, "error_code", None):
            raise TranslationError(f"{response.error_code}: {response.error_msg}")
        return response.translated_text
