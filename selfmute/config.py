from dataclasses import dataclass

from .constants import (
    MAX_DAILY_COUNT,
    MAX_RANDOM_SECONDS,
    MIN_RANDOM_SECONDS,
)


@dataclass(frozen=True)
class SelfMuteConfig:
    max_daily_count: int
    min_random_seconds: int
    max_random_seconds: int
    use_wake_prefix: bool


def load_config(config: dict | None) -> SelfMuteConfig:
    """按主插件当前行为加载配置。"""
    if not config:
        return SelfMuteConfig(
            max_daily_count=MAX_DAILY_COUNT,
            min_random_seconds=MIN_RANDOM_SECONDS,
            max_random_seconds=MAX_RANDOM_SECONDS,
            use_wake_prefix=False,
        )

    return SelfMuteConfig(
        max_daily_count=config.get("max_daily_count", MAX_DAILY_COUNT),
        min_random_seconds=config.get("min_random_seconds", MIN_RANDOM_SECONDS),
        max_random_seconds=config.get("max_random_seconds", MAX_RANDOM_SECONDS),
        use_wake_prefix=config.get("use_wake_prefix", False),
    )


__all__ = ["SelfMuteConfig", "load_config"]

