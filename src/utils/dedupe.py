"""
去重工具模块
提供 URL 规范化和内容去重功能
"""

import hashlib
import re
from typing import List, Dict, Set, Optional, Any
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from dataclasses import dataclass
import json
from pathlib import Path


# 需要从 URL 中移除的参数
PARAMS_TO_REMOVE = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
    'ref', 'source', 'fbclid', 'gclid', 'mc_cid', 'mc_eid',
    '_ga', '_gid', 'ncid', 'sr_share'
}


def normalize_url(url: str) -> str:
    """
    规范化 URL，用于去重比较

    规范化规则：
    1. 统一使用 https 协议
    2. 移除 utm_* 等追踪参数
    3. 移除 ref、source 参数
    4. 移除末尾斜杠
    5. 移除 URL fragment (#...)

    Args:
        url: 原始 URL

    Returns:
        str: 规范化后的 URL

    Example:
        >>> normalize_url("http://example.com/page?utm_source=twitter&id=123#section")
        'https://example.com/page?id=123'
    """
    if not url:
        return ""

    try:
        parsed = urlparse(url)

        # 统一使用 https
        scheme = 'https'

        # 处理查询参数，移除追踪参数
        query_params = parse_qs(parsed.query, keep_blank_values=False)
        filtered_params = {
            k: v for k, v in query_params.items()
            if k.lower() not in PARAMS_TO_REMOVE and not k.lower().startswith('utm_')
        }

        # 重新构建查询字符串（排序以保证一致性）
        new_query = urlencode(filtered_params, doseq=True) if filtered_params else ''

        # 移除末尾斜杠（但保留根路径）
        path = parsed.path.rstrip('/') if parsed.path != '/' else '/'

        # 重新构建 URL（不包含 fragment）
        normalized = urlunparse((
            scheme,
            parsed.netloc.lower(),
            path,
            parsed.params,
            new_query,
            ''  # 移除 fragment
        ))

        return normalized

    except Exception:
        # 如果解析失败，返回原始 URL 的清理版本
        return url.split('#')[0].rstrip('/')


def generate_stable_id(
    url: Optional[str] = None,
    source: Optional[str] = None,
    title: Optional[str] = None,
    published_at: Optional[str] = None
) -> str:
    """
    生成稳定的唯一 ID

    ID 生成规则：
    1. 如果有 URL，使用规范化 URL 的 SHA256 hash
    2. 如果没有 URL，使用 source + title + published_at 的 hash

    Args:
        url: 文章 URL
        source: 来源名称
        title: 文章标题
        published_at: 发布时间

    Returns:
        str: 稳定的唯一 ID（32 字符的 hex 字符串）
    """
    if url:
        # 优先使用规范化 URL
        normalized = normalize_url(url)
        content = normalized
    else:
        # 使用其他字段组合
        parts = [
            source or '',
            title or '',
            published_at or ''
        ]
        content = '|'.join(parts)

    # 生成 SHA256 hash，取前 32 个字符
    hash_obj = hashlib.sha256(content.encode('utf-8'))
    return hash_obj.hexdigest()[:32]


@dataclass
class HistoryEntry:
    """历史记录条目"""
    id: str
    url: str
    fetched_at: str


class Deduplicator:
    """
    去重器

    支持：
    1. 同次运行内去重（基于 stable_id）
    2. 跨天增量去重（基于历史文件）
    """

    def __init__(self, history_file: Optional[str] = None):
        """
        初始化去重器

        Args:
            history_file: 历史记录文件路径（JSONL 格式）
        """
        self.history_file = Path(history_file) if history_file else None
        self._seen_ids: Set[str] = set()
        self._seen_urls: Set[str] = set()
        self._history_ids: Set[str] = set()

        # 加载历史记录
        if self.history_file and self.history_file.exists():
            self._load_history()

    def _load_history(self):
        """加载历史记录文件"""
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        self._history_ids.add(entry.get('id', ''))
        except Exception as e:
            print(f"警告：加载历史文件失败: {e}")

    def is_duplicate(self, item: Dict[str, Any]) -> bool:
        """
        检查是否为重复内容

        Args:
            item: 内容条目，必须包含 id 字段

        Returns:
            bool: 是否重复
        """
        item_id = item.get('id', '')
        url = item.get('url', '')
        normalized_url = normalize_url(url) if url else ''

        # 检查是否在当前运行中已见过
        if item_id in self._seen_ids:
            return True

        # 检查 URL 是否重复
        if normalized_url and normalized_url in self._seen_urls:
            return True

        return False

    def is_new(self, item: Dict[str, Any]) -> bool:
        """
        检查是否为新内容（相对于历史记录）

        Args:
            item: 内容条目

        Returns:
            bool: 是否为新内容
        """
        item_id = item.get('id', '')
        return item_id not in self._history_ids

    def mark_seen(self, item: Dict[str, Any]):
        """
        标记内容为已见

        Args:
            item: 内容条目
        """
        item_id = item.get('id', '')
        url = item.get('url', '')

        if item_id:
            self._seen_ids.add(item_id)

        if url:
            normalized_url = normalize_url(url)
            self._seen_urls.add(normalized_url)

    def dedupe(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        对列表进行去重

        Args:
            items: 内容条目列表

        Returns:
            List[Dict[str, Any]]: 去重后的列表，并标记 is_new 字段
        """
        result = []

        for item in items:
            if not self.is_duplicate(item):
                # 标记是否为新内容
                item['is_new'] = self.is_new(item)
                self.mark_seen(item)
                result.append(item)

        return result

    def save_history(self, items: List[Dict[str, Any]], fetched_at: str):
        """
        保存历史记录

        Args:
            items: 内容条目列表
            fetched_at: 抓取时间
        """
        if not self.history_file:
            return

        # 确保目录存在
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        # 追加写入
        with open(self.history_file, 'a', encoding='utf-8') as f:
            for item in items:
                entry = {
                    'id': item.get('id', ''),
                    'url': item.get('url', ''),
                    'fetched_at': fetched_at
                }
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def get_stats(self) -> Dict[str, int]:
        """
        获取去重统计

        Returns:
            Dict[str, int]: 统计信息
        """
        return {
            'seen_ids': len(self._seen_ids),
            'seen_urls': len(self._seen_urls),
            'history_ids': len(self._history_ids)
        }
