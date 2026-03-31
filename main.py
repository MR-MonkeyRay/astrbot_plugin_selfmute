import asyncio
import random
from datetime import date
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

# 常量定义
MAX_DAILY_COUNT = 3
MAX_MUTE_SECONDS = 30 * 24 * 60 * 60  # 2592000
MIN_RANDOM_SECONDS = 60
MAX_RANDOM_SECONDS = 3600
STATE_KEY = "selfmute_state"

@register("selfmute", "MonkeyRay", "自裁插件 - 移植自 Mirai SelfMute", "1.0.0")
class SelfMutePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self._state_lock = asyncio.Lock()

    @filter.command("selfmute", alias=["自裁"])
    async def selfmute(self, event: AstrMessageEvent, seconds: str = ""):
        """自裁指令 - 自我禁言"""
        # 1. 校验群聊
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("该指令只能在群聊中使用")
            return

        # 2. 校验管理员免疫
        if event.role in {"admin", "owner"} or event.is_admin():
            yield event.plain_result("群主和管理员对本指令免疫的噢!~")
            return

        user_id = event.get_sender_id()
        user_name = event.get_sender_name()

        # 3. 在单次锁内完成所有操作
        async with self._state_lock:
            # 3.1 读取后做结构归一化
            raw_state = await self.get_kv_data(STATE_KEY, {"date": "", "counters": {}})
            state = raw_state if isinstance(raw_state, dict) else {}
            saved_date = state.get("date", "")
            today = date.today().isoformat()

            # 3.2 日期重置
            if saved_date != today:
                state = {"date": today, "counters": {}}
                await self.put_kv_data(STATE_KEY, state)

            # 3.3 确保 counters 结构合法
            if not isinstance(state.get("counters"), dict):
                state["counters"] = {}

            # 3.4 检查次数（直接操作 state["counters"]）
            if not isinstance(state["counters"].get(group_id), dict):
                state["counters"][group_id] = {}
            group_map = state["counters"][group_id]

            try:
                used_count = int(group_map.get(user_id, 0))
            except (ValueError, TypeError, OverflowError):
                used_count = 0

            # 归一化：确保计数非负
            used_count = max(0, used_count)

            if used_count >= MAX_DAILY_COUNT:
                yield event.plain_result("你是抖m吧?😨当日自裁次数达到上限了!明天再来吧!真是的...😡")
                return

            # 3.4 检查 Bot 权限
            try:
                bot_info = await event.bot.call_action(
                    "get_group_member_info",
                    group_id=group_id,
                    user_id=event.bot.self_id
                )
                bot_role = bot_info.get("role", "member")

                if bot_role not in {"admin", "owner"}:
                    yield event.plain_result("机器人权限不足: 非群主或管理员,无法执行禁言操作😭...")
                    return
            except Exception as e:
                logger.exception("无法获取机器人权限信息: %s", e)
                yield event.plain_result("无法确认机器人群权限，请稍后重试")
                return

            # 3.5 计算禁言时长
            duration, is_random = self._calculate_duration(seconds, used_count + 1)

            # 3.6 执行禁言（在锁内）
            try:
                await event.bot.call_action(
                    "set_group_ban",
                    group_id=group_id,
                    user_id=user_id,
                    duration=duration
                )
            except Exception as e:
                logger.exception("selfmute ban failed: %s", e)
                yield event.plain_result("禁言失败: 机器人权限不足或平台不支持该操作")
                return

            # 3.7 禁言成功后递增次数
            current_count = used_count + 1
            group_map[user_id] = current_count
            await self.put_kv_data(STATE_KEY, state)

        # 4. 返回成功消息（锁外）
        message = self._build_success_message(user_name, user_id, duration, current_count, is_random)
        yield event.plain_result(message)

    def _calculate_duration(self, seconds_str: str, count: int) -> tuple[int, bool]:
        """计算禁言时长（秒）和是否随机

        Returns:
            (duration, is_random): 禁言秒数和是否为随机禁言
        """
        try:
            if not seconds_str:
                seconds = 0.0
            else:
                seconds = float(seconds_str)
                if not (0 <= seconds < float('inf')):
                    seconds = 0.0
        except (ValueError, OverflowError):
            seconds = 0.0

        if seconds < 1:
            # 随机禁言：随机值 × 当日次数
            duration = random.randint(MIN_RANDOM_SECONDS, MAX_RANDOM_SECONDS) * count
            is_random = True
        else:
            duration = int(seconds)
            is_random = False

        # 限制最大值
        return (min(duration, MAX_MUTE_SECONDS), is_random)

    def _build_success_message(self, user_name: str, user_id: str,
                              duration: int, count: int, is_random: bool) -> str:
        """构建成功消息"""
        time_str = self._format_time(duration)

        if duration >= MAX_MUTE_SECONDS:
            return f"⚠️群友\"{user_name}({user_id})\"已获得30天豪华小黑屋居住资格!({count}/3)"
        elif is_random:
            return f"🥳恭喜群友\"{user_name}({user_id})\"喜提禁言{time_str}!({count}/3)"
        else:
            return f"🎉群友\"{user_name}({user_id})\"选择了自裁{time_str}!({count}/3)"

    def _format_time(self, seconds: int) -> str:
        """格式化时长为可读字符串"""
        if seconds >= 86400:
            days = seconds // 86400
            return f"{days}天"
        elif seconds >= 3600:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours}小时{minutes}分钟"
            return f"{hours}小时"
        elif seconds >= 60:
            minutes = seconds // 60
            secs = seconds % 60
            if secs > 0:
                return f"{minutes}分钟{secs}秒"
            return f"{minutes}分钟"
        else:
            return f"{seconds}秒"
