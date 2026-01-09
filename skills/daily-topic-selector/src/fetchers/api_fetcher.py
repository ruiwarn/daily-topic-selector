"""
API 抓取器模块
支持从 REST API 抓取内容（主要用于 Hacker News）
"""

import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base import BaseFetcher, FetchResult
from ..utils.time_utils import parse_datetime, to_iso_string


class APIFetcher(BaseFetcher):
    """
    API 抓取器

    主要用于 Hacker News Firebase API
    """

    def fetch(self) -> FetchResult:
        """
        从 API 抓取内容

        Returns:
            FetchResult: 抓取结果
        """
        endpoints = self.config.get('endpoints', {})
        default_list = self.config.get('default_list', 'topstories')
        batch_concurrency = self.config.get('batch_concurrency', 10)

        # 获取故事 ID 列表的 URL
        list_url = endpoints.get(default_list)
        item_url_template = endpoints.get('item')

        if not list_url or not item_url_template:
            return FetchResult(
                success=False,
                error="API endpoints 未正确配置"
            )

        try:
            # 获取故事 ID 列表
            story_ids = self.http_client.get_json(list_url)

            if not isinstance(story_ids, list):
                return FetchResult(
                    success=False,
                    error="API 返回格式错误"
                )

            # 限制数量
            limit = self.config.get('limit', 50)
            story_ids = story_ids[:limit]

            # 并发获取详情
            items = self._fetch_items_parallel(
                story_ids,
                item_url_template,
                batch_concurrency
            )

            return FetchResult(
                success=True,
                items=items,
                method_used='api',
                raw_count=len(story_ids)
            )

        except Exception as e:
            return FetchResult(
                success=False,
                error=str(e)
            )

    def _fetch_items_parallel(
        self,
        item_ids: List[int],
        url_template: str,
        concurrency: int
    ) -> List[Dict[str, Any]]:
        """
        并发获取条目详情

        Args:
            item_ids: 条目 ID 列表
            url_template: URL 模板
            concurrency: 并发数

        Returns:
            List[Dict[str, Any]]: 条目列表
        """
        items = []

        def fetch_item(item_id: int) -> Optional[Dict[str, Any]]:
            """获取单个条目"""
            try:
                url = url_template.format(id=item_id)
                data = self.http_client.get_json(url)

                if data and data.get('type') == 'story':
                    return self._parse_hn_item(data)
            except Exception:
                pass
            return None

        # 使用线程池并发获取
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {
                executor.submit(fetch_item, item_id): item_id
                for item_id in item_ids
            }

            for future in as_completed(futures):
                result = future.result()
                if result and self._is_valid_item(result):
                    items.append(result)

        return items

    def _parse_hn_item(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析 Hacker News 条目

        Args:
            data: API 返回的原始数据

        Returns:
            Optional[Dict[str, Any]]: 标准化的条目
        """
        try:
            item_id = data.get('id')
            title = data.get('title', '').strip()

            # URL：如果没有外部链接，使用 HN 讨论页
            url = data.get('url', '')
            if not url:
                url = f"https://news.ycombinator.com/item?id={item_id}"

            # 发布时间
            time_val = data.get('time')
            published = parse_datetime(time_val) if time_val else None
            published_at = to_iso_string(published)

            # 作者
            author = data.get('by', '')

            # HN 特有字段
            points = data.get('score', 0)
            comments = data.get('descendants', 0)

            # 原始数据
            raw = {
                'hn_item_id': item_id,
                'points': points,
                'comments': comments,
                'type': data.get('type', 'story')
            }

            return self._create_item(
                title=title,
                url=url,
                published_at=published_at,
                author=author,
                summary=None,  # HN 没有摘要
                raw=raw
            )

        except Exception:
            return None
