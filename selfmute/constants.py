import re

# 默认常量（配置缺失时使用）
MAX_DAILY_COUNT = 3
MAX_MUTE_SECONDS = 30 * 24 * 60 * 60  # 2592000，QQ 平台最大限制，保持硬编码
MIN_RANDOM_SECONDS = 60
MAX_RANDOM_SECONDS = 3600
STATE_KEY = "selfmute_state"

SELFMUTE_COMMAND = "selfmute"
SELFMUTE_ALIASES = ["自裁"]
SELFMUTE_LISTENER_PATTERN = r"^(?:selfmute|自裁)(?:\s+[\s\S]+)?$"
SELFMUTE_RE = re.compile(r"^(?:selfmute|自裁)(?:\s+([\s\S]+))?$")

__all__ = [
    "MAX_DAILY_COUNT",
    "MAX_MUTE_SECONDS",
    "MIN_RANDOM_SECONDS",
    "MAX_RANDOM_SECONDS",
    "STATE_KEY",
    "SELFMUTE_COMMAND",
    "SELFMUTE_ALIASES",
    "SELFMUTE_LISTENER_PATTERN",
    "SELFMUTE_RE",
]
