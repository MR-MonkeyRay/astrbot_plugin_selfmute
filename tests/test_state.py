"""SelfMute 状态存储测试"""

from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest

from selfmute.state import SelfMuteStateStore


@pytest.fixture
def state_store():
    get_kv_data = AsyncMock(return_value={"date": "", "counters": {}})
    put_kv_data = AsyncMock()
    return SelfMuteStateStore(
        get_kv_data=get_kv_data,
        put_kv_data=put_kv_data,
        state_key="selfmute_state",
    )


class TestLoadTodayState:
    """状态读取与跨天重置"""

    @pytest.mark.asyncio
    async def test_load_today_state_keeps_today_state(self, state_store):
        today = date.today().isoformat()
        state_store.get_kv_data.return_value = {
            "date": today,
            "counters": {"123": {"456": 1}},
        }

        state = await state_store.load_today_state()

        assert state == {"date": today, "counters": {"123": {"456": 1}}}
        state_store.put_kv_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_load_today_state_resets_previous_day(self, state_store):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        today = date.today().isoformat()
        state_store.get_kv_data.return_value = {
            "date": yesterday,
            "counters": {"123": {"456": 9}},
        }

        state = await state_store.load_today_state()

        assert state == {"date": today, "counters": {}}
        state_store.put_kv_data.assert_awaited_once_with(
            "selfmute_state",
            {"date": today, "counters": {}},
        )

    @pytest.mark.asyncio
    async def test_load_today_state_normalizes_invalid_payload(self, state_store):
        today = date.today().isoformat()
        state_store.get_kv_data.return_value = {"date": today, "counters": []}

        state = await state_store.load_today_state()

        assert state == {"date": today, "counters": {}}


class TestGetUsedCount:
    """计数读取与归一化"""

    def test_get_used_count_initializes_missing_group(self, state_store):
        state = {"date": date.today().isoformat(), "counters": {}}

        count = state_store.get_used_count(state, "123", "456")

        assert count == 0
        assert state["counters"] == {"123": {}}

    def test_get_used_count_normalizes_invalid_value(self, state_store):
        state = {"date": date.today().isoformat(), "counters": {"123": {"456": "x"}}}

        count = state_store.get_used_count(state, "123", "456")

        assert count == 0

    def test_get_used_count_clamps_negative_value(self, state_store):
        state = {"date": date.today().isoformat(), "counters": {"123": {"456": -3}}}

        count = state_store.get_used_count(state, "123", "456")

        assert count == 0


class TestIncrementUsedCount:
    """成功后计数递增与写回"""

    @pytest.mark.asyncio
    async def test_increment_used_count_updates_state_and_persists(self, state_store):
        today = date.today().isoformat()
        state = {"date": today, "counters": {"123": {"456": 1}}}

        current_count = await state_store.increment_used_count(state, "123", "456", 1)

        assert current_count == 2
        assert state["counters"]["123"]["456"] == 2
        state_store.put_kv_data.assert_awaited_once_with("selfmute_state", state)
