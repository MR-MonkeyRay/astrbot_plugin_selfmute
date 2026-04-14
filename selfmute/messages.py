from .constants import MAX_MUTE_SECONDS


def format_duration(seconds: int) -> str:
    """格式化时长为可读字符串。"""
    if seconds >= 86400:
        days = seconds // 86400
        return f"{days}天"
    if seconds >= 3600:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours}小时{minutes}分钟"
        return f"{hours}小时"
    if seconds >= 60:
        minutes = seconds // 60
        secs = seconds % 60
        if secs > 0:
            return f"{minutes}分钟{secs}秒"
        return f"{minutes}分钟"
    return f"{seconds}秒"


def build_success_message(
    user_name: str,
    user_id: str,
    duration: int,
    count: int,
    max_daily_count: int,
    is_random: bool,
) -> str:
    """构建禁言成功文案，保持与主插件一致。"""
    time_str = format_duration(duration)

    if duration >= MAX_MUTE_SECONDS:
        return (
            f"⚠️群友\"{user_name}({user_id})\"已获得30天豪华小黑屋居住资格!"
            f"({count}/{max_daily_count})"
        )
    if is_random:
        return f"🥳恭喜群友\"{user_name}({user_id})\"喜提禁言{time_str}!({count}/{max_daily_count})"
    return f"🎉群友\"{user_name}({user_id})\"选择了自裁{time_str}!({count}/{max_daily_count})"


__all__ = ["format_duration", "build_success_message"]

