import asyncio
import random
import sys
from pathlib import Path

# AstrBot 在部分加载路径下不会自动把插件目录加入 sys.path。
# 这里显式注入当前目录，确保同目录下的 selfmute 包可被导入。
PLUGIN_ROOT = Path(__file__).resolve().parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

from selfmute import (
    MAX_DAILY_COUNT,
    MAX_MUTE_SECONDS,
    MAX_RANDOM_SECONDS,
    MIN_RANDOM_SECONDS,
    SELFMUTE_ALIASES,
    SELFMUTE_COMMAND,
    SELFMUTE_LISTENER_PATTERN,
    SELFMUTE_RE,
    STATE_KEY,
    load_config,
)
from selfmute.messages import build_success_message as build_success_message_impl
from selfmute.messages import format_duration
from selfmute.parser import extract_seconds_argument, parse_seconds_input
from selfmute.service import SelfMuteService
from selfmute.state import SelfMuteStateStore

_SELFMUTE_RE = SELFMUTE_RE


@register(name="selfmute", author="MonkeyRay", desc="自裁插件", version="1.1.0")
class SelfMutePlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context, config)
        self._state_lock = asyncio.Lock()

        plugin_config = load_config(config)
        self.max_daily_count = plugin_config.max_daily_count
        self.min_random_seconds = plugin_config.min_random_seconds
        self.max_random_seconds = plugin_config.max_random_seconds
        self.use_wake_prefix = plugin_config.use_wake_prefix

    @filter.command(SELFMUTE_COMMAND, alias=SELFMUTE_ALIASES)
    async def selfmute_command(self, event: AstrMessageEvent, seconds: str = ""):
        """自裁指令 - 自我禁言"""
        try:
            async for result in self._handle_selfmute(event, seconds):
                yield result
        except Exception as e:
            logger.exception(f"selfmute_command 执行异常: {e}")
            yield event.plain_result(f"自裁失败: {str(e)}")

    def _should_handle_with_listener(self, event: AstrMessageEvent) -> bool:
        """判断当前消息是否应由裸消息 listener 处理。

        AstrBot 的 `command` 过滤器只处理带唤醒词/At 的消息，
        但 `regex` 过滤器不会受到 wake_prefix 约束。
        因此这里必须显式拦截所有 wake 消息，避免与标准指令重复执行。
        """
        if self.use_wake_prefix:
            return False
        return not event.is_at_or_wake_command

    @filter.regex(SELFMUTE_LISTENER_PATTERN)
    async def selfmute_listener(self, event: AstrMessageEvent):
        """消息监听 - 支持裸消息触发"""
        try:
            if not self._should_handle_with_listener(event):
                return

            msg = event.get_message_str().strip()
            if not _SELFMUTE_RE.match(msg):
                return

            seconds = extract_seconds_argument(msg)
            async for result in self._handle_selfmute(event, seconds):
                yield result
        except Exception as e:
            logger.exception(f"selfmute_listener 执行异常: {e}")
            yield event.plain_result(f"自裁失败: {str(e)}")

    def _make_state_store(self) -> SelfMuteStateStore:
        async def get_kv_data(state_key: str, default: dict) -> dict | None:
            return await self.get_kv_data(state_key, default)

        async def put_kv_data(state_key: str, state: dict) -> None:
            await self.put_kv_data(state_key, state)

        return SelfMuteStateStore(
            get_kv_data=get_kv_data,
            put_kv_data=put_kv_data,
            state_key=STATE_KEY,
        )

    def _make_service(self) -> SelfMuteService:
        return SelfMuteService(
            state_store=self._make_state_store(),
            state_lock=self._state_lock,
            max_daily_count=self.max_daily_count,
            calculate_duration=self._calculate_duration,
            build_success_message=self._build_success_message,
        )

    async def _handle_selfmute(self, event: AstrMessageEvent, seconds: str = ""):
        """自裁核心逻辑"""
        message = await self._make_service().handle_selfmute(event, seconds)
        yield event.plain_result(message)

    def _calculate_duration(self, seconds_str: str, count: int) -> tuple[int, bool]:
        """计算禁言时长（秒）和是否随机。

        Returns:
            (duration, is_random): 禁言秒数和是否为随机禁言
        """
        seconds = parse_seconds_input(seconds_str)

        if seconds < 1:
            duration = random.randint(self.min_random_seconds, self.max_random_seconds) * count
            is_random = True
        else:
            duration = int(seconds)
            is_random = False

        return min(duration, MAX_MUTE_SECONDS), is_random

    def _build_success_message(
        self,
        user_name: str,
        user_id: str,
        duration: int,
        count: int,
        is_random: bool,
    ) -> str:
        """构建成功消息"""
        return build_success_message_impl(
            user_name=user_name,
            user_id=user_id,
            duration=duration,
            count=count,
            max_daily_count=self.max_daily_count,
            is_random=is_random,
        )

    def _format_time(self, seconds: int) -> str:
        """格式化时长为可读字符串"""
        return format_duration(seconds)


__all__ = [
    "MAX_DAILY_COUNT",
    "MAX_MUTE_SECONDS",
    "MIN_RANDOM_SECONDS",
    "MAX_RANDOM_SECONDS",
    "STATE_KEY",
    "SelfMutePlugin",
]
