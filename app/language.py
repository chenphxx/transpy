"""文本语言检测与翻译方向决策。"""

import re

_JAPANESE_RE = re.compile(r"[\u3040-\u309F\u30A0-\u30FF]+")
_CJK_RE = re.compile(r"[\u4E00-\u9FFF]")


def detect_language(text: str) -> str:
    """粗略判断源语言, 返回 'zh' 或 'auto'。

    日语常包含汉字, 为避免被误判为中文, 只要出现假名就返回 'auto',
    交由华为云 API 自动识别语种。
    """
    if not text:
        return "auto"
    if _JAPANESE_RE.search(text):
        return "auto"
    if _CJK_RE.search(text):
        return "zh"
    return "auto"


def pick_direction(source: str):
    """根据源语言返回 (from, to) 翻译方向。"""
    if source == "zh":
        return ("zh", "en")
    return ("auto", "zh")
