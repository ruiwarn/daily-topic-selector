"""
时间工具模块
处理各种时间格式的解析和转换
"""

import re
from datetime import datetime, timezone
from typing import Optional, Union
from dateutil import parser as dateutil_parser
from dateutil.tz import tzutc


# 月份名称映射（用于解析 "january-9-2026" 格式）
MONTH_NAMES = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
    'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9,
    'oct': 10, 'nov': 11, 'dec': 12
}


def parse_datetime(
    value: Union[str, int, float, datetime, None],
    fallback: Optional[datetime] = None
) -> Optional[datetime]:
    """
    解析各种格式的时间

    支持的格式：
    - ISO 8601 字符串
    - RFC 822 字符串（RSS 格式）
    - Unix timestamp（整数或浮点数）
    - "january-9-2026" 格式（James Clear URL 格式）
    - datetime 对象

    Args:
        value: 待解析的时间值
        fallback: 解析失败时的默认值

    Returns:
        Optional[datetime]: 解析后的 datetime 对象（UTC 时区）
    """
    if value is None:
        return fallback

    # 已经是 datetime
    if isinstance(value, datetime):
        return _ensure_utc(value)

    # Unix timestamp
    if isinstance(value, (int, float)):
        try:
            dt = datetime.fromtimestamp(value, tz=timezone.utc)
            return dt
        except (ValueError, OSError):
            return fallback

    # 字符串格式
    if isinstance(value, str):
        value = value.strip()

        if not value:
            return fallback

        # 尝试解析 "month-day-year" 格式
        month_day_year = _parse_month_day_year(value)
        if month_day_year:
            return month_day_year

        # 尝试使用 dateutil 解析
        try:
            dt = dateutil_parser.parse(value)
            return _ensure_utc(dt)
        except (ValueError, TypeError):
            pass

        # 尝试解析 Unix timestamp 字符串
        try:
            timestamp = float(value)
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            return dt
        except (ValueError, OSError):
            pass

    return fallback


def _parse_month_day_year(value: str) -> Optional[datetime]:
    """
    解析 "month-day-year" 格式（如 "january-9-2026"）

    Args:
        value: 待解析字符串

    Returns:
        Optional[datetime]: 解析后的 datetime
    """
    # 匹配 "month-day-year" 格式
    match = re.match(r'(\w+)-(\d{1,2})-(\d{4})', value.lower())
    if not match:
        return None

    month_name, day_str, year_str = match.groups()

    month = MONTH_NAMES.get(month_name)
    if not month:
        return None

    try:
        day = int(day_str)
        year = int(year_str)
        return datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError:
        return None


def _ensure_utc(dt: datetime) -> datetime:
    """
    确保 datetime 是 UTC 时区

    Args:
        dt: datetime 对象

    Returns:
        datetime: UTC 时区的 datetime
    """
    if dt.tzinfo is None:
        # 假设无时区的时间是 UTC
        return dt.replace(tzinfo=timezone.utc)
    else:
        # 转换为 UTC
        return dt.astimezone(timezone.utc)


def to_iso_string(dt: Optional[datetime]) -> Optional[str]:
    """
    转换为 ISO 8601 格式字符串

    Args:
        dt: datetime 对象

    Returns:
        Optional[str]: ISO 格式字符串（如 "2026-01-09T12:00:00Z"）
    """
    if dt is None:
        return None

    # 确保是 UTC
    dt_utc = _ensure_utc(dt)

    # 格式化为 ISO 格式
    return dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ')


def get_now_utc() -> datetime:
    """
    获取当前 UTC 时间

    Returns:
        datetime: 当前 UTC 时间
    """
    return datetime.now(timezone.utc)


def get_since_datetime(days: int = 1) -> datetime:
    """
    获取 N 天前的时间

    Args:
        days: 天数

    Returns:
        datetime: N 天前的 UTC 时间
    """
    from datetime import timedelta
    now = get_now_utc()
    return now - timedelta(days=days)


def is_within_range(
    dt: Optional[datetime],
    since: Optional[datetime] = None,
    until: Optional[datetime] = None
) -> bool:
    """
    检查时间是否在指定范围内

    Args:
        dt: 待检查的时间
        since: 开始时间（含）
        until: 结束时间（含）

    Returns:
        bool: 是否在范围内
    """
    if dt is None:
        # 时间未知时默认保留
        return True

    dt_utc = _ensure_utc(dt)

    if since and dt_utc < _ensure_utc(since):
        return False

    if until and dt_utc > _ensure_utc(until):
        return False

    return True
