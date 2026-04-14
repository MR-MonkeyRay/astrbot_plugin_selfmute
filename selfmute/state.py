from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Awaitable, Callable


KvGetFunc = Callable[[str, dict], Awaitable[dict | None]]
KvPutFunc = Callable[[str, dict], Awaitable[None]]


@dataclass(slots=True)
class SelfMuteStateStore:
    """封装自裁插件的 KV 状态读写与归一化。"""

    get_kv_data: KvGetFunc
    put_kv_data: KvPutFunc
    state_key: str

    async def load_today_state(self) -> dict:
        """读取并归一化状态，必要时执行跨天重置。"""
        raw_state = await self.get_kv_data(self.state_key, {"date": "", "counters": {}})
        state = raw_state if isinstance(raw_state, dict) else {}

        saved_date = state.get("date", "")
        today = date.today().isoformat()
        if saved_date != today:
            state = {"date": today, "counters": {}}
            await self.put_kv_data(self.state_key, state)

        if not isinstance(state.get("counters"), dict):
            state["counters"] = {}

        return state

    def get_used_count(self, state: dict, group_id: str, user_id: str) -> int:
        """获取用户当日次数，保证结构与数值合法。"""
        counters = state.setdefault("counters", {})
        if not isinstance(counters.get(group_id), dict):
            counters[group_id] = {}
        group_map = counters[group_id]

        try:
            used_count = int(group_map.get(user_id, 0))
        except (ValueError, TypeError, OverflowError):
            used_count = 0

        return max(0, used_count)

    async def increment_used_count(self, state: dict, group_id: str, user_id: str, used_count: int) -> int:
        """禁言成功后递增计数并持久化。"""
        counters = state.setdefault("counters", {})
        if not isinstance(counters.get(group_id), dict):
            counters[group_id] = {}
        group_map = counters[group_id]
        current_count = used_count + 1
        group_map[user_id] = current_count
        await self.put_kv_data(self.state_key, state)
        return current_count
