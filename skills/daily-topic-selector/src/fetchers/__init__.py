"""
fetchers 包初始化
"""

from .base import BaseFetcher, FetchResult, TopicItem
from .rss_fetcher import RSSFetcher
from .api_fetcher import APIFetcher
from .html_fetcher import HTMLFetcher
from .json_extractor import JSONExtractor

__all__ = [
    'BaseFetcher', 'FetchResult', 'TopicItem',
    'RSSFetcher', 'APIFetcher', 'HTMLFetcher', 'JSONExtractor'
]


def create_fetcher(
    method: str,
    source_id: str,
    source_name: str,
    config: dict,
    http_client=None,
    default_tags=None
):
    """
    工厂函数：根据方法类型创建对应的抓取器

    Args:
        method: 抓取方法（rss, api, html, json_extract）
        source_id: 数据源 ID
        source_name: 数据源名称
        config: 抓取配置
        http_client: HTTP 客户端
        default_tags: 默认标签

    Returns:
        BaseFetcher: 抓取器实例
    """
    fetcher_map = {
        'rss': RSSFetcher,
        'api': APIFetcher,
        'html': HTMLFetcher,
        'json_extract': JSONExtractor
    }

    fetcher_class = fetcher_map.get(method)
    if not fetcher_class:
        raise ValueError(f"不支持的抓取方法: {method}")

    return fetcher_class(
        source_id=source_id,
        source_name=source_name,
        config=config,
        http_client=http_client,
        default_tags=default_tags
    )
