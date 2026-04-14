from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .state import SelfMuteStateStore


DurationCalculator = Callable[[str, int], tuple[int, bool]]
SuccessMessageBuilder = Callable[[str, str, int, int, bool], str]


def _resolve_bot_self_id(event: AstrMessageEvent) -> str:
    """解析机器人自身 ID，优先依赖 AstrBot 官方事件抽象。"""
    get_self_id = getattr(event, "get_self_id", None)
    if callable(get_self_id):
        value = get_self_id()
        if value not in {None, ""}:
            return str(value)

    message_obj = getattr(event, "message_obj", None)
    message_self_id = getattr(message_obj, "self_id", None)
    if message_self_id not in {None, ""}:
        return str(message_self_id)

    raise ValueError("无法解析机器人自身 ID")


def _require_int_id(value: str, field_name: str) -> int:
    """将平台 ID 规范为整数，便于对接 OneBot v11 接口。"""
    try:
        return int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} 不是有效的整数 ID: {value!r}") from exc


@dataclass(slots=True)
class SelfMuteService:
    """自裁业务服务：负责权限检查、禁言执行与状态落盘。"""

    state_store: SelfMuteStateStore
    state_lock: asyncio.Lock
    max_daily_count: int
    calculate_duration: DurationCalculator
    build_success_message: SuccessMessageBuilder

    async def handle_selfmute(self, event: AstrMessageEvent, seconds: str = "") -> str:
        """执行一次自裁流程，返回最终提示文案。"""
        logger.debug(
            "handle_selfmute 开始执行: user=%s, group=%s, seconds=%r, is_at_or_wake=%s",
            event.get_sender_id(),
            event.get_group_id(),
            seconds,
            event.is_at_or_wake_command,
        )

        group_id = event.get_group_id()
        if not group_id:
            logger.debug("拒绝: 非群聊消息")
            return "该指令只能在群聊中使用"

        if event.role in {"admin", "owner"} or event.is_admin():
            logger.debug("拒绝: 管理员免疫 (role=%s, is_admin=%s)", event.role, event.is_admin())
            return "群主和管理员对本指令免疫的噢!~"

        user_id = event.get_sender_id()
        user_name = event.get_sender_name()
        logger.debug("通过权限检查: user_id=%s, user_name=%s", user_id, user_name)

        async with self.state_lock:
            state = await self.state_store.load_today_state()
            used_count = self.state_store.get_used_count(state, group_id, user_id)

            if used_count >= self.max_daily_count:
                return "你是抖m吧?😨当日自裁次数达到上限了!明天再来吧!真是的...😡"

            try:
                bot_self_id = _resolve_bot_self_id(event)
                group_id_int = _require_int_id(group_id, "group_id")
                bot_self_id_int = _require_int_id(bot_self_id, "bot_self_id")
                logger.debug("检查 Bot 权限: bot_self_id=%s, group_id=%s", bot_self_id, group_id)
                bot_info = await event.bot.call_action(
                    "get_group_member_info",
                    group_id=group_id_int,
                    user_id=bot_self_id_int,
                    self_id=bot_self_id_int,
                )
                bot_role = bot_info.get("role", "member")
                logger.debug("Bot 权限查询结果: bot_role=%s, raw=%s", bot_role, bot_info)
                if bot_role not in {"admin", "owner"}:
                    return "机器人权限不足: 非群主或管理员,无法执行禁言操作😭..."
            except Exception as e:
                logger.exception("无法获取机器人权限信息: %s", e)
                return "无法确认机器人群权限，请稍后重试"

            duration, is_random = self.calculate_duration(seconds, used_count + 1)
            logger.debug("禁言时长: duration=%s, is_random=%s", duration, is_random)

            try:
                user_id_int = _require_int_id(user_id, "user_id")
                logger.debug(
                    "执行 set_group_ban: group_id=%s, user_id=%s, duration=%s",
                    group_id,
                    user_id,
                    duration,
                )
                await event.bot.call_action(
                    "set_group_ban",
                    group_id=group_id_int,
                    user_id=user_id_int,
                    duration=duration,
                    self_id=bot_self_id_int,
                )
                logger.debug("set_group_ban 执行成功")
            except Exception as e:
                logger.exception("selfmute ban failed: %s", e)
                return "禁言失败: 机器人权限不足或平台不支持该操作"

            current_count = await self.state_store.increment_used_count(state, group_id, user_id, used_count)
            logger.debug("次数更新成功: user_id=%s, count=%s/%s", user_id, current_count, self.max_daily_count)

        message = self.build_success_message(user_name, user_id, duration, current_count, is_random)
        logger.debug("返回成功消息: %s", message)
        return message
