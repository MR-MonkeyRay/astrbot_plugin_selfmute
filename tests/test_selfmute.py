"""SelfMute 插件核心功能测试"""
import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from main import MAX_DAILY_COUNT, MAX_MUTE_SECONDS, MIN_RANDOM_SECONDS, MAX_RANDOM_SECONDS


# ──────────────────────────── 辅助函数 ────────────────────────────

async def _invoke(plugin, event, seconds=""):
    """调用 selfmute 并收集 yield 出的所有结果"""
    results = []
    async for item in plugin.selfmute(event, seconds):
        results.append(item)
    return results


# ──────────────────────────── 基础功能测试 ────────────────────────────


class TestBasicFunction:
    """基础功能：随机禁言、指定时长、上限截断、时间格式化"""

    @pytest.mark.asyncio
    async def test_random_mute_no_param(self, plugin, mock_event):
        """随机禁言（无参数）— 应成功禁言，消息包含 '喜提禁言'"""
        results = await _invoke(plugin, mock_event)
        assert len(results) == 1
        assert "喜提禁言" in results[0]

    @pytest.mark.asyncio
    async def test_specified_duration(self, plugin, mock_event):
        """指定时长禁言 — 传入 300（5 分钟），消息包含 '选择了自裁'"""
        results = await _invoke(plugin, mock_event, "300")
        assert len(results) == 1
        assert "选择了自裁" in results[0]
        assert "5分钟" in results[0]

    @pytest.mark.asyncio
    async def test_max_duration_cap(self, plugin, mock_event):
        """超过 30 天自动截断到 2592000 秒，消息包含 '30天豪华小黑屋'"""
        huge = str(MAX_MUTE_SECONDS + 100000)
        results = await _invoke(plugin, mock_event, huge)
        assert len(results) == 1
        assert "30天豪华小黑屋" in results[0]

    def test_time_format_seconds(self, plugin):
        """时长格式化 — 纯秒数"""
        assert plugin._format_time(30) == "30秒"

    def test_time_format_minutes(self, plugin):
        """时长格式化 — 纯分钟"""
        assert plugin._format_time(120) == "2分钟"

    def test_time_format_minutes_and_seconds(self, plugin):
        """时长格式化 — 分钟+秒"""
        assert plugin._format_time(90) == "1分钟30秒"

    def test_time_format_hours(self, plugin):
        """时长格式化 — 纯小时"""
        assert plugin._format_time(7200) == "2小时"

    def test_time_format_hours_and_minutes(self, plugin):
        """时长格式化 — 小时+分钟"""
        assert plugin._format_time(5400) == "1小时30分钟"

    def test_time_format_days(self, plugin):
        """时长格式化 — 天"""
        assert plugin._format_time(172800) == "2天"


# ──────────────────────────── 权限检查测试 ────────────────────────────


class TestPermission:
    """权限检查：非群聊拒绝、管理员免疫、群主免疫、Bot 无权限"""

    @pytest.mark.asyncio
    async def test_reject_non_group(self, plugin, make_event):
        """非群聊拒绝 — group_id 为 None"""
        event = make_event(group_id=None)
        results = await _invoke(plugin, event)
        assert len(results) == 1
        assert "只能在群聊中使用" in results[0]

    @pytest.mark.asyncio
    async def test_admin_immunity(self, plugin, make_event):
        """管理员免疫 — role=admin"""
        event = make_event(role="admin")
        results = await _invoke(plugin, event)
        assert len(results) == 1
        assert "免疫" in results[0]

    @pytest.mark.asyncio
    async def test_owner_immunity(self, plugin, make_event):
        """群主免疫 — role=owner"""
        event = make_event(role="owner")
        results = await _invoke(plugin, event)
        assert len(results) == 1
        assert "免疫" in results[0]

    @pytest.mark.asyncio
    async def test_is_admin_immunity(self, plugin, make_event):
        """is_admin 返回 True 时也免疫"""
        event = make_event(is_admin=True)
        results = await _invoke(plugin, event)
        assert len(results) == 1
        assert "免疫" in results[0]

    @pytest.mark.asyncio
    async def test_bot_no_permission(self, plugin, make_event):
        """Bot 无权限拒绝 — Bot 角色为 member"""
        event = make_event(bot_role="member")
        results = await _invoke(plugin, event)
        assert len(results) == 1
        assert "机器人权限不足" in results[0]


# ──────────────────────────── 每日限制测试 ────────────────────────────


class TestDailyLimit:
    """每日限制：前 3 次成功，第 4 次拒绝，跨天重置"""

    @pytest.mark.asyncio
    async def test_first_use_success(self, plugin, mock_event):
        """第 1 次使用成功"""
        results = await _invoke(plugin, mock_event)
        assert len(results) == 1
        assert "(1/3)" in results[0]

    @pytest.mark.asyncio
    async def test_second_use_success(self, plugin, mock_event):
        """第 2 次使用成功"""
        today = date.today().isoformat()
        plugin.get_kv_data = AsyncMock(
            return_value={
                "date": today,
                "counters": {"123456": {"789012": 1}},
            }
        )
        results = await _invoke(plugin, mock_event)
        assert len(results) == 1
        assert "(2/3)" in results[0]

    @pytest.mark.asyncio
    async def test_third_use_success(self, plugin, mock_event):
        """第 3 次使用成功"""
        today = date.today().isoformat()
        plugin.get_kv_data = AsyncMock(
            return_value={
                "date": today,
                "counters": {"123456": {"789012": 2}},
            }
        )
        results = await _invoke(plugin, mock_event)
        assert len(results) == 1
        assert "(3/3)" in results[0]

    @pytest.mark.asyncio
    async def test_fourth_use_rejected(self, plugin, mock_event):
        """第 4 次使用被拒绝"""
        today = date.today().isoformat()
        plugin.get_kv_data = AsyncMock(
            return_value={
                "date": today,
                "counters": {"123456": {"789012": 3}},
            }
        )
        results = await _invoke(plugin, mock_event)
        assert len(results) == 1
        assert "次数达到上限" in results[0]

    @pytest.mark.asyncio
    async def test_daily_reset(self, plugin, mock_event):
        """跨天重置 — KV 中日期为昨天，今天应视为第 1 次"""
        from datetime import timedelta

        yesterday = (date.today() - timedelta(days=1)).isoformat()
        plugin.get_kv_data = AsyncMock(
            return_value={
                "date": yesterday,
                "counters": {"123456": {"789012": 3}},
            }
        )
        results = await _invoke(plugin, mock_event)
        assert len(results) == 1
        assert "(1/3)" in results[0]


# ──────────────────────────── 随机倍率测试 ────────────────────────────


class TestRandomMultiplier:
    """随机倍率：第 N 次随机禁言 = random × N"""

    def test_random_multiplier_first(self, plugin):
        """第 1 次：duration = random × 1"""
        with patch("main.random.randint", return_value=100):
            duration, is_random = plugin._calculate_duration("", 1)
            assert duration == 100
            assert is_random is True

    def test_random_multiplier_second(self, plugin):
        """第 2 次：duration = random × 2"""
        with patch("main.random.randint", return_value=100):
            duration, is_random = plugin._calculate_duration("", 2)
            assert duration == 200
            assert is_random is True

    def test_random_multiplier_third(self, plugin):
        """第 3 次：duration = random × 3"""
        with patch("main.random.randint", return_value=100):
            duration, is_random = plugin._calculate_duration("", 3)
            assert duration == 300
            assert is_random is True


# ──────────────────────────── 错误处理测试 ────────────────────────────


class TestErrorHandling:
    """错误处理：非法参数、禁言失败不消耗次数、特殊浮点数"""

    @pytest.mark.asyncio
    async def test_invalid_param_fallback_random(self, plugin, mock_event):
        """非数字参数（如 'abc'）应回退为随机禁言"""
        results = await _invoke(plugin, mock_event, "abc")
        assert len(results) == 1
        assert "喜提禁言" in results[0]

    @pytest.mark.asyncio
    async def test_ban_failure_no_consume(self, plugin, make_event):
        """禁言失败时不消耗次数 — set_group_ban 抛异常，次数不增加"""
        event = make_event()
        # 让 KV 返回今天的日期，避免触发日期重置写入
        today = date.today().isoformat()
        plugin.get_kv_data = AsyncMock(
            return_value={"date": today, "counters": {"123456": {}}}
        )
        # 第 1 次 call_action 返回 bot 权限信息，第 2 次抛异常
        event.bot.call_action = AsyncMock(
            side_effect=[
                {"role": "admin"},
                RuntimeError("ban failed"),
            ]
        )
        results = await _invoke(plugin, event)
        assert len(results) == 1
        assert "禁言失败" in results[0]
        # put_kv_data 不应被调用（次数未更新）
        plugin.put_kv_data.assert_not_called()

    def test_special_float_nan(self, plugin):
        """float('nan') 应被归零，返回随机禁言"""
        duration, is_random = plugin._calculate_duration("nan", 1)
        assert is_random is True
        assert MIN_RANDOM_SECONDS <= duration <= MAX_MUTE_SECONDS

    def test_special_float_inf(self, plugin):
        """float('inf') 应被归零，返回随机禁言"""
        duration, is_random = plugin._calculate_duration("inf", 1)
        assert is_random is True
        assert MIN_RANDOM_SECONDS <= duration <= MAX_MUTE_SECONDS
