from .constants import SELFMUTE_RE


def extract_seconds_argument(message: str) -> str:
    """从完整消息中提取秒数字符串参数，不匹配时返回空串。"""
    m = SELFMUTE_RE.match(message.strip())
    if not m:
        return ""
    return m.group(1) or ""


def parse_seconds_input(seconds_str: str) -> float:
    """按主插件现有规则解析秒数字符串。"""
    try:
        if not seconds_str:
            seconds = 0.0
        else:
            seconds = float(seconds_str)
            if not (0 <= seconds < float("inf")):
                seconds = 0.0
    except (ValueError, OverflowError):
        seconds = 0.0
    return seconds


__all__ = ["extract_seconds_argument", "parse_seconds_input"]

