"""
JSON 提取器模块
从页面内嵌的 JSON 数据中提取内容（主要用于 TLDR AI）
"""

import re
import json
from typing import List, Dict, Any, Optional

from .base import BaseFetcher, FetchResult
from ..utils.time_utils import parse_datetime, to_iso_string
from ..utils.dedupe import normalize_url


class JSONExtractor(BaseFetcher):
    """
    JSON 提取器

    从网页内嵌的 JSON 数据（如 Next.js RSC 数据）中提取内容
    主要用于 TLDR AI 等现代 JS 框架网站
    """

    def fetch(self) -> FetchResult:
        """
        从页面内嵌 JSON 抓取内容

        Returns:
            FetchResult: 抓取结果
        """
        archive_url = self.config.get('archive_url')
        if not archive_url:
            return FetchResult(
                success=False,
                error="archive_url 未配置"
            )

        try:
            # 第一步：获取 newsletter 列表
            html = self.http_client.get_text(archive_url, headers=self._get_headers())

            # 提取 campaigns 数据
            campaigns = self._extract_campaigns(html)

            if not campaigns:
                return FetchResult(
                    success=False,
                    error="未能提取 campaigns 数据"
                )

            # 第二步：获取最新几期的详细内容
            items = []
            newsletter_url_template = self.config.get('newsletter_url_template')

            # 只获取最近几期
            limit = self.config.get('limit', 3)
            for campaign in campaigns[:limit]:
                date = campaign.get('date')
                if not date:
                    continue

                # 构建 newsletter URL
                newsletter_url = newsletter_url_template.format(date=date)

                # 获取 newsletter 内容
                try:
                    newsletter_html = self.http_client.get_text(
                        newsletter_url,
                        headers=self._get_headers()
                    )
                    articles = self._extract_articles(newsletter_html, date)
                    items.extend(articles)
                except Exception:
                    # 单个 newsletter 失败不影响整体
                    continue

            return FetchResult(
                success=True,
                items=items,
                method_used='json_extract',
                raw_count=len(items)
            )

        except Exception as e:
            return FetchResult(
                success=False,
                error=str(e)
            )

    def _extract_campaigns(self, html: str) -> List[Dict[str, Any]]:
        """
        从 archives 页面提取 campaigns 数据

        Args:
            html: 页面 HTML

        Returns:
            List[Dict[str, Any]]: campaigns 列表
        """
        json_pattern = self.config.get('json_pattern', r'"campaigns":\s*(\[.*?\])')

        try:
            match = re.search(json_pattern, html, re.DOTALL)
            if match:
                campaigns_json = match.group(1)
                # 处理可能的 JSON 格式问题
                campaigns = json.loads(campaigns_json)
                return campaigns
        except (json.JSONDecodeError, AttributeError):
            pass

        return []

    def _extract_articles(
        self,
        html: str,
        date: str
    ) -> List[Dict[str, Any]]:
        """
        从 newsletter 页面提取文章

        Args:
            html: newsletter 页面 HTML
            date: 日期字符串

        Returns:
            List[Dict[str, Any]]: 文章列表
        """
        items = []
        article_patterns = self.config.get('article_patterns', {})

        # 提取标题
        title_pattern = article_patterns.get('title', r'"children":\s*"([^"]+)"')
        url_pattern = article_patterns.get('url', r'"href":\s*"([^"]+)"')
        summary_pattern = article_patterns.get('summary', r'"__html":\s*"([^"]+)"')

        # 使用简化的提取逻辑
        # 查找所有 href 链接
        href_matches = re.findall(r'"href":\s*"(https?://[^"]+)"', html)
        title_matches = re.findall(r'"children":\s*"([^"]{10,200})"', html)

        # 过滤并配对
        seen_urls = set()
        for i, url in enumerate(href_matches):
            # 跳过内部链接和重复链接
            if 'tldr.tech' in url or url in seen_urls:
                continue

            # 规范化 URL（移除 utm 参数）
            clean_url = normalize_url(url)
            if clean_url in seen_urls:
                continue

            seen_urls.add(clean_url)

            # 尝试找到对应的标题
            title = None
            if i < len(title_matches):
                title = title_matches[i]
            else:
                # 从 URL 提取可能的标题
                title = self._extract_title_from_url(url)

            if not title:
                continue

            # 清理标题
            title = self._clean_text(title)

            # 解析日期
            published = parse_datetime(date)
            published_at = to_iso_string(published)

            item = self._create_item(
                title=title,
                url=clean_url,
                published_at=published_at,
                raw={'original_url': url, 'newsletter_date': date}
            )

            if self._is_valid_item(item):
                items.append(item)

        return items

    def _extract_title_from_url(self, url: str) -> Optional[str]:
        """
        从 URL 提取可能的标题

        Args:
            url: URL 字符串

        Returns:
            Optional[str]: 提取的标题
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)
        path = parsed.path.strip('/')

        if path:
            # 取最后一段作为标题
            slug = path.split('/')[-1]
            # 移除文件扩展名
            slug = re.sub(r'\.(html?|php|aspx?)$', '', slug)
            # 将连字符转为空格
            title = slug.replace('-', ' ').replace('_', ' ')
            return title.title()

        return None

    def _clean_text(self, text: str) -> str:
        """
        清理文本

        Args:
            text: 原始文本

        Returns:
            str: 清理后的文本
        """
        # 解码 Unicode 转义
        try:
            text = text.encode().decode('unicode_escape')
        except Exception:
            pass

        # 移除多余空白
        text = re.sub(r'\s+', ' ', text).strip()

        return text
