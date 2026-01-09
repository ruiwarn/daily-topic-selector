"""
RSS 抓取器模块
支持从 RSS/Atom feed 抓取内容
"""

import feedparser
from typing import List, Dict, Any, Optional

from .base import BaseFetcher, FetchResult
from ..utils.time_utils import parse_datetime, to_iso_string


class RSSFetcher(BaseFetcher):
    """
    RSS/Atom 抓取器

    使用 feedparser 库解析 RSS/Atom feed
    """

    def fetch(self) -> FetchResult:
        """
        从 RSS feed 抓取内容

        Returns:
            FetchResult: 抓取结果
        """
        url = self.config.get('url')
        if not url:
            return FetchResult(
                success=False,
                error="RSS URL 未配置"
            )

        try:
            # 获取 RSS 内容
            response = self.http_client.get_text(url)

            # 解析 RSS
            feed = feedparser.parse(response)

            if feed.bozo and not feed.entries:
                return FetchResult(
                    success=False,
                    error=f"RSS 解析失败: {feed.bozo_exception}"
                )

            # 转换条目
            items = []
            for entry in feed.entries:
                item = self._parse_entry(entry)
                if item and self._is_valid_item(item):
                    items.append(item)

            return FetchResult(
                success=True,
                items=items,
                method_used='rss',
                raw_count=len(feed.entries)
            )

        except Exception as e:
            return FetchResult(
                success=False,
                error=str(e)
            )

    def _parse_entry(self, entry: Any) -> Optional[Dict[str, Any]]:
        """
        解析单个 RSS 条目

        Args:
            entry: feedparser 条目对象

        Returns:
            Optional[Dict[str, Any]]: 标准化的条目
        """
        try:
            # 提取标题
            title = entry.get('title', '').strip()

            # 提取链接
            url = entry.get('link', '')
            if not url and entry.get('links'):
                for link in entry.links:
                    if link.get('rel') == 'alternate':
                        url = link.get('href', '')
                        break

            # 提取发布时间
            published = None
            if entry.get('published_parsed'):
                from datetime import datetime
                import time
                published = datetime(*entry.published_parsed[:6])
            elif entry.get('updated_parsed'):
                from datetime import datetime
                published = datetime(*entry.updated_parsed[:6])
            elif entry.get('published'):
                published = parse_datetime(entry.published)
            elif entry.get('updated'):
                published = parse_datetime(entry.updated)

            published_at = to_iso_string(published) if published else None

            # 提取作者
            author = entry.get('author')
            if not author and entry.get('authors'):
                author = entry.authors[0].get('name', '')
            # Dublin Core 作者
            if not author:
                author = entry.get('dc_creator')

            # 提取摘要
            summary = entry.get('summary', '')
            if not summary and entry.get('description'):
                summary = entry.description

            # 提取完整内容
            full_content = None
            if entry.get('content'):
                for content in entry.content:
                    if content.get('type') == 'text/html':
                        full_content = content.get('value', '')
                        break
                if not full_content and entry.content:
                    full_content = entry.content[0].get('value', '')

            # 提取标签/分类
            tags = []
            if entry.get('tags'):
                for tag in entry.tags:
                    term = tag.get('term', '')
                    if term:
                        tags.append(term)

            # 提取评论数
            comments_count = None
            if entry.get('slash_comments'):
                try:
                    comments_count = int(entry.slash_comments)
                except (ValueError, TypeError):
                    pass

            # 构建原始数据
            raw = {}
            if full_content:
                raw['full_content'] = full_content
            if comments_count is not None:
                raw['comments'] = comments_count
            if entry.get('id'):
                raw['feed_id'] = entry.id

            # 检查是否缺少发布时间
            if not published_at:
                raw['missing_published_at'] = True

            return self._create_item(
                title=title,
                url=url,
                published_at=published_at,
                author=author,
                summary=summary,
                tags=tags,
                raw=raw
            )

        except Exception as e:
            # 解析失败，跳过该条目
            return None
