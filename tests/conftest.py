import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# 将项目根目录加入 sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Mock astrbot 模块，避免导入时找不到依赖
astrbot_mock = MagicMock()

# filter.command 必须是 identity 装饰器，保留原方法
filter_mock = MagicMock()
filter_mock.command = lambda *a, **kw: lambda fn: fn
filter_mock.regex = lambda *a, **kw: lambda fn: fn

api_mock = MagicMock()
api_mock.event = MagicMock()
api_mock.event.filter = filter_mock
api_mock.event.AstrMessageEvent = MagicMock()


# Star 需要是真实基类，让子类正常继承方法
class _FakeStar:
    def __init__(self, context, config=None):
        self.context = context
        self.config = config


api_mock.star = MagicMock()
api_mock.star.Context = MagicMock
api_mock.star.Star = _FakeStar
api_mock.star.register = lambda *a, **kw: lambda cls: cls
api_mock.logger = MagicMock()
sys.modules["astrbot"] = astrbot_mock
sys.modules["astrbot.api"] = api_mock
sys.modules["astrbot.api.event"] = api_mock.event
sys.modules["astrbot.api.star"] = api_mock.star
sys.modules["astrbot.api.star.config"] = api_mock.star.config

from main import SelfMutePlugin, MAX_DAILY_COUNT, MAX_MUTE_SECONDS, STATE_KEY


def _make_mock_event(
    group_id="123456",
    sender_id="789012",
    sender_name="测试用户",
    sender_role="member",
    bot_role="admin",
):
    """构造一个完整的 mock AstrMessageEvent"""
    event = MagicMock()
    event.get_group_id.return_value = group_id
    event.get_sender_id.return_value = sender_id
    event.get_sender_name.return_value = sender_name

    # Bot mock — bot.call_action 是异步的
    event.bot = MagicMock()
    event.bot.call_action = AsyncMock(
        side_effect=[
            {"role": sender_role},  # get_group_member_info(sender)
            {"role": bot_role},  # get_group_member_info(bot)
            None,  # set_group_ban
        ]
    )
    event.bot.self_id = "999888777"

    # Mock event.get_self_id() 方法
    event.get_self_id = MagicMock(return_value="999888777")
    event.is_at_or_wake_command = False
    event.get_message_str = MagicMock(return_value="")

    # plain_result 直接返回传入的文本，方便断言
    event.plain_result = MagicMock(side_effect=lambda x: x)

    return event


@pytest.fixture
def mock_context():
    """Mock Context 对象"""
    return MagicMock()


@pytest.fixture
def plugin(mock_context):
    """创建 SelfMutePlugin 实例，并 mock 掉 KV 存储"""
    p = SelfMutePlugin(mock_context)
    p.get_kv_data = AsyncMock(return_value={"date": "", "counters": {}})
    p.put_kv_data = AsyncMock()
    return p


@pytest.fixture
def mock_event():
    """默认 mock AstrMessageEvent（群聊、普通成员、Bot 是管理员）"""
    return _make_mock_event()


@pytest.fixture
def mock_kv_storage():
    """返回一个干净的 KV 存储初始状态"""
    return {"date": "", "counters": {}}


@pytest.fixture
def make_event():
    """工厂 fixture，用于按需构造自定义 mock event"""
    return _make_mock_event
