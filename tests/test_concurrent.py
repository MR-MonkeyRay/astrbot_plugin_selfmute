"""SelfMute 插件并发安全测试"""
import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from main import MAX_DAILY_COUNT, STATE_KEY


async def _invoke(plugin, event, seconds=""):
    """调用 selfmute_command 并收集 yield 出的所有结果"""
    results = []
    async for item in plugin.selfmute_command(event, seconds):
        results.append(item)
    return results


def _make_event(**overrides):
    """构造 mock event（同步 MagicMock + 异步 call_action）"""
    defaults = {
        "group_id": "123456",
        "sender_id": "789012",
        "sender_name": "测试用户",
        "role": "member",
        "is_admin": False,
        "bot_role": "admin",
    }
    defaults.update(overrides)
    d = defaults

    event = MagicMock()
    event.get_group_id.return_value = d["group_id"]
    event.get_sender_id.return_value = d["sender_id"]
    event.get_sender_name.return_value = d["sender_name"]
    event.role = d["role"]
    event.is_admin.return_value = d["is_admin"]

    event.bot = MagicMock()
    event.bot.call_action = AsyncMock(
        side_effect=[{"role": d["bot_role"]}, None]
    )
    event.plain_result = MagicMock(side_effect=lambda x: x)

    # Mock event.get_self_id() 方法
    event.get_self_id = MagicMock(return_value="999888777")

    return event


class TestConcurrency:
    """并发安全：多请求同时到达时，锁保证次数统计正确"""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, plugin):
        """10 个并发请求，只有前 3 个成功禁言"""
        today = date.today().isoformat()

        # 使用真实锁 + 可变 state 来模拟真实并发场景
        real_state = {"date": today, "counters": {}}

        async def mock_get_kv(*args, **kwargs):
            group_map = real_state["counters"].get("123456", {})
            return {
                "date": real_state["date"],
                "counters": {"123456": dict(group_map)},
            }

        async def mock_put_kv(*args, **kwargs):
            new_state = args[1]
            real_state["date"] = new_state["date"]
            real_state["counters"] = {
                k: dict(v) for k, v in new_state["counters"].items()
            }

        plugin.get_kv_data = AsyncMock(side_effect=mock_get_kv)
        plugin.put_kv_data = AsyncMock(side_effect=mock_put_kv)

        events = [_make_event() for _ in range(10)]
        tasks = [_invoke(plugin, e) for e in events]
        all_results = await asyncio.gather(*tasks)

        success_count = sum(
            1 for results in all_results
            if results and "/3)" in results[0] and "次数达到上限" not in results[0]
        )
        reject_count = sum(
            1 for results in all_results
            if results and "次数达到上限" in results[0]
        )

        assert success_count == MAX_DAILY_COUNT
        assert reject_count == 10 - MAX_DAILY_COUNT

    @pytest.mark.asyncio
    async def test_counter_accuracy(self, plugin):
        """并发后计数器值准确"""
        today = date.today().isoformat()
        real_state = {"date": today, "counters": {}}

        async def mock_get_kv(*args, **kwargs):
            group_map = real_state["counters"].get("123456", {})
            return {
                "date": real_state["date"],
                "counters": {"123456": dict(group_map)},
            }

        async def mock_put_kv(*args, **kwargs):
            new_state = args[1]
            real_state["date"] = new_state["date"]
            real_state["counters"] = {
                k: dict(v) for k, v in new_state["counters"].items()
            }

        plugin.get_kv_data = AsyncMock(side_effect=mock_get_kv)
        plugin.put_kv_data = AsyncMock(side_effect=mock_put_kv)

        events = [_make_event() for _ in range(5)]
        tasks = [_invoke(plugin, e) for e in events]
        await asyncio.gather(*tasks)

        # 最终计数器应为 3
        final_count = real_state["counters"].get("123456", {}).get("789012", 0)
        assert final_count == MAX_DAILY_COUNT
