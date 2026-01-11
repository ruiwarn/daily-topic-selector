"""
HTML 抓取器模块
支持从网页解析内容
"""

import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseFetcher, FetchResult
from ..utils.time_utils import parse_datetime, to_iso_string


class HTMLFetcher(BaseFetcher):
    """
    HTML 抓取器

    使用 BeautifulSoup 解析网页内容
    """

    def fetch(self) -> FetchResult:
        """
        从网页抓取内容

        Returns:
            FetchResult: 抓取结果
        """
        url = self.config.get('url')
        if not url:
            return FetchResult(
                success=False,
                error="URL 未配置"
            )

        try:
            # 获取页面内容
            html = self.http_client.get_text(url, headers=self._get_headers())

            # 解析 HTML
            soup = BeautifulSoup(html, 'lxml')

            # 根据配置提取条目
            items = self._extract_items(soup, url)

            return FetchResult(
                success=True,
                items=items,
                method_used='html',
                raw_count=len(items)
            )

        except Exception as e:
            return FetchResult(
                success=False,
                error=str(e)
            )

    def _extract_items(
        self,
        soup: BeautifulSoup,
        base_url: str
    ) -> List[Dict[str, Any]]:
        """
        从页面提取条目

        Args:
            soup: BeautifulSoup 对象
            base_url: 基础 URL

        Returns:
            List[Dict[str, Any]]: 条目列表
        """
        items = []
        selectors = self.config.get('selectors', {})

        # 提取链接列表
        links_selector = selectors.get('links')
        if links_selector:
            items = self._extract_from_links(soup, links_selector, base_url)
        else:
            # 使用单独的选择器
            items = self._extract_from_selectors(soup, selectors, base_url)

        return items

    def _extract_from_links(
        self,
        soup: BeautifulSoup,
        selector: str,
        base_url: str
    ) -> List[Dict[str, Any]]:
        """
        从链接列表提取条目

        Args:
            soup: BeautifulSoup 对象
            selector: CSS 选择器
            base_url: 基础 URL

        Returns:
            List[Dict[str, Any]]: 条目列表
        """
        items = []
        elements = soup.select(selector)

        date_config = self.config.get('date_from_url', {})

        for elem in elements:
            href = elem.get('href', '')
            if not href:
                continue

            # 构建完整 URL
            full_url = urljoin(base_url, href)

            # 提取标题
            title = elem.get_text(strip=True)
            if not title:
                continue

            # 从 URL 提取日期
            published_at = None
            if date_config:
                published_at = self._extract_date_from_url(href, date_config)

            item = self._create_item(
                title=title,
                url=full_url,
                published_at=published_at
            )

            if self._is_valid_item(item):
                items.append(item)

        return items

    def _extract_from_selectors(
        self,
        soup: BeautifulSoup,
        selectors: Dict[str, str],
        base_url: str
    ) -> List[Dict[str, Any]]:
        """
        使用多个选择器提取条目

        Args:
            soup: BeautifulSoup 对象
            selectors: 选择器配置
            base_url: 基础 URL

        Returns:
            List[Dict[str, Any]]: 条目列表
        """
        items = []

        # 获取各个元素列表
        title_elems = soup.select(selectors.get('title', '')) if selectors.get('title') else []
        link_elems = soup.select(selectors.get('link', '')) if selectors.get('link') else []
        date_elems = soup.select(selectors.get('date', '')) if selectors.get('date') else []

        # 按索引配对
        for i, title_elem in enumerate(title_elems):
            title = title_elem.get_text(strip=True)

            # 获取链接
            url = None
            if i < len(link_elems):
                url = link_elems[i].get('href', '')
                url = urljoin(base_url, url)
            elif title_elem.name == 'a':
                url = title_elem.get('href', '')
                url = urljoin(base_url, url)

            # 获取日期
            published_at = None
            if i < len(date_elems):
                date_text = date_elems[i].get_text(strip=True)
                published = parse_datetime(date_text)
                published_at = to_iso_string(published)

            if title and url:
                item = self._create_item(
                    title=title,
                    url=url,
                    published_at=published_at
                )
                if self._is_valid_item(item):
                    items.append(item)

        return items

    def _extract_date_from_url(
        self,
        url: str,
        config: Dict[str, Any]
    ) -> Optional[str]:
        """
        从 URL 提取日期

        Args:
            url: URL 字符串
            config: 日期提取配置

        Returns:
            Optional[str]: ISO 格式日期字符串
        """
        pattern = config.get('pattern', '')
        date_format = config.get('format', '')

        if not pattern:
            return None

        match = re.search(pattern, url)
        if not match:
            return None

        groups = match.groups()

        try:
            if date_format == '%Y-%m-%d':
                # 直接使用匹配的日期字符串
                date_str = groups[0]
                published = parse_datetime(date_str)
                return to_iso_string(published)

            elif date_format == 'month_name-day-year':
                # 处理 "january-9-2026" 格式
                if len(groups) >= 3:
                    month_name, day, year = groups[:3]
                    date_str = f"{month_name}-{day}-{year}"
                    published = parse_datetime(date_str)
                    return to_iso_string(published)

            elif date_format == 'year/month':
                # 处理 "/2025/11/" 格式
                if len(groups) >= 2:
                    year, month = groups[:2]
                    from datetime import datetime
                    published = datetime(int(year), int(month), 1)
                    return to_iso_string(published)

        except Exception:
            pass

        return None
