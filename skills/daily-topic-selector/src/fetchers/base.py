"""
抓取器基类模块
定义所有抓取器的基础接口和通用功能
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from ..utils.http import HttpClient, create_client
from ..utils.dedupe import generate_stable_id
from ..utils.time_utils import to_iso_string, get_now_utc


@dataclass
class FetchResult:
    """抓取结果"""
    success: bool
    items: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    method_used: Optional[str] = None
    raw_count: int = 0
    fetch_time: Optional[str] = None


@dataclass
class TopicItem:
    """
    话题条目数据结构

    对应需求文档中的标准字段
    """
    id: str
    source: str
    title: str
    url: str
    published_at: Optional[str] = None
    fetched_at: Optional[str] = None
    author: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    score: float = 0.0
    is_new: bool = True
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'source': self.source,
            'title': self.title,
            'url': self.url,
            'published_at': self.published_at,
            'fetched_at': self.fetched_at,
            'author': self.author,
            'summary': self.summary,
            'tags': self.tags,
            'score': self.score,
            'is_new': self.is_new,
            'raw': self.raw
        }


class BaseFetcher(ABC):
    """
    抓取器基类

    所有具体抓取器（RSS、API、HTML、JSON）都需要继承此类
    """

    def __init__(
        self,
        source_id: str,
        source_name: str,
        config: Dict[str, Any],
        http_client: Optional[HttpClient] = None,
        default_tags: Optional[List[str]] = None
    ):
        """
        初始化抓取器

        Args:
            source_id: 数据源 ID
            source_name: 数据源显示名称
            config: 抓取方法配置
            http_client: HTTP 客户端
            default_tags: 默认标签
        """
        self.source_id = source_id
        self.source_name = source_name
        self.config = config
        self.http_client = http_client or create_client()
        self.default_tags = default_tags or []

    @abstractmethod
    def fetch(self) -> FetchResult:
        """
        执行抓取

        Returns:
            FetchResult: 抓取结果
        """
        pass

    def _create_item(
        self,
        title: str,
        url: str,
        published_at: Optional[str] = None,
        author: Optional[str] = None,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        raw: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建标准化的条目

        Args:
            title: 标题
            url: URL
            published_at: 发布时间
            author: 作者
            summary: 摘要
            tags: 标签
            raw: 原始数据

        Returns:
            Dict[str, Any]: 标准化的条目字典
        """
        # 生成稳定 ID
        stable_id = generate_stable_id(
            url=url,
            source=self.source_id,
            title=title,
            published_at=published_at
        )

        # 合并标签
        all_tags = list(self.default_tags)
        if tags:
            for tag in tags:
                if tag not in all_tags:
                    all_tags.append(tag)

        # 获取当前时间
        fetched_at = to_iso_string(get_now_utc())

        return {
            'id': stable_id,
            'source': self.source_name,
            'title': title,
            'url': url,
            'published_at': published_at,
            'fetched_at': fetched_at,
            'author': author,
            'summary': self._truncate_summary(summary),
            'tags': all_tags,
            'score': 0.0,
            'is_new': True,
            'raw': raw or {}
        }

    def _truncate_summary(
        self,
        summary: Optional[str],
        max_length: int = 500
    ) -> Optional[str]:
        """
        截断摘要

        Args:
            summary: 原始摘要
            max_length: 最大长度

        Returns:
            Optional[str]: 截断后的摘要
        """
        if not summary:
            return None

        # 移除 HTML 标签
        import re
        clean_summary = re.sub(r'<[^>]+>', '', summary)

        # 截断
        if len(clean_summary) > max_length:
            return clean_summary[:max_length] + '...'

        return clean_summary

    def _is_valid_item(self, item: Dict[str, Any]) -> bool:
        """
        检查条目是否有效

        Args:
            item: 条目数据

        Returns:
            bool: 是否有效
        """
        # 标题不能为空
        if not item.get('title'):
            return False

        # URL 不能为空
        if not item.get('url'):
            return False

        return True
