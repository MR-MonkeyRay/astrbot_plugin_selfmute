"""SelfMute 参数解析测试"""

import math

from selfmute.parser import extract_seconds_argument, parse_seconds_input


class TestExtractSecondsArgument:
    """消息参数提取应与主插件监听规则一致"""

    def test_extract_empty_argument(self):
        assert extract_seconds_argument("自裁") == ""

    def test_extract_numeric_argument(self):
        assert extract_seconds_argument("自裁 300") == "300"

    def test_extract_multiline_argument(self):
        assert extract_seconds_argument("selfmute   12\n34") == "12\n34"

    def test_extract_non_matching_message_returns_empty(self):
        assert extract_seconds_argument("其他消息") == ""


class TestParseSecondsInput:
    """秒数字符串解析应保持旧行为"""

    def test_empty_string_returns_zero(self):
        assert parse_seconds_input("") == 0.0

    def test_numeric_string_returns_float(self):
        assert parse_seconds_input("300") == 300.0

    def test_negative_number_falls_back_to_zero(self):
        assert parse_seconds_input("-1") == 0.0

    def test_invalid_string_falls_back_to_zero(self):
        assert parse_seconds_input("abc") == 0.0

    def test_nan_falls_back_to_zero(self):
        assert parse_seconds_input("nan") == 0.0

    def test_inf_falls_back_to_zero(self):
        assert parse_seconds_input("inf") == 0.0

    def test_fractional_number_is_preserved(self):
        assert math.isclose(parse_seconds_input("1.5"), 1.5)
