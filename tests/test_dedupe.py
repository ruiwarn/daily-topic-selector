"""
去重模块单元测试
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.dedupe import normalize_url, generate_stable_id, Deduplicator


class TestNormalizeUrl:
    """URL 规范化测试"""

    def test_remove_utm_params(self):
        """测试移除 utm 参数"""
        url = "https://example.com/article?utm_source=twitter&utm_medium=social&id=123"
        expected = "https://example.com/article?id=123"
        assert normalize_url(url) == expected

    def test_remove_ref_param(self):
        """测试移除 ref 参数"""
        url = "https://example.com/page?ref=homepage&id=456"
        expected = "https://example.com/page?id=456"
        assert normalize_url(url) == expected

    def test_remove_trailing_slash(self):
        """测试移除末尾斜杠"""
        url = "https://example.com/article/"
        expected = "https://example.com/article"
        assert normalize_url(url) == expected

    def test_keep_root_slash(self):
        """测试保留根路径斜杠"""
        url = "https://example.com/"
        expected = "https://example.com/"
        assert normalize_url(url) == expected

    def test_remove_fragment(self):
        """测试移除 URL fragment"""
        url = "https://example.com/article#section1"
        expected = "https://example.com/article"
        assert normalize_url(url) == expected

    def test_upgrade_http_to_https(self):
        """测试 HTTP 升级为 HTTPS"""
        url = "http://example.com/article"
        expected = "https://example.com/article"
        assert normalize_url(url) == expected

    def test_lowercase_domain(self):
        """测试域名转为小写"""
        url = "https://Example.COM/Article"
        result = normalize_url(url)
        assert "example.com" in result

    def test_complex_url(self):
        """测试复杂 URL"""
        url = "http://Example.COM/page?utm_source=x&ref=y&id=1#section"
        expected = "https://example.com/page?id=1"
        assert normalize_url(url) == expected

    def test_empty_url(self):
        """测试空 URL"""
        assert normalize_url("") == ""
        assert normalize_url(None) == ""

    def test_url_without_params(self):
        """测试无参数 URL"""
        url = "https://example.com/article"
        expected = "https://example.com/article"
        assert normalize_url(url) == expected


class TestGenerateStableId:
    """stable_id 生成测试"""

    def test_same_url_same_id(self):
        """测试相同 URL 生成相同 ID"""
        url = "https://example.com/article?id=123"
        id1 = generate_stable_id(url=url)
        id2 = generate_stable_id(url=url)
        assert id1 == id2

    def test_normalized_urls_same_id(self):
        """测试规范化后相同的 URL 生成相同 ID"""
        url1 = "http://example.com/article?utm_source=x"
        url2 = "https://example.com/article"
        id1 = generate_stable_id(url=url1)
        id2 = generate_stable_id(url=url2)
        assert id1 == id2

    def test_different_urls_different_id(self):
        """测试不同 URL 生成不同 ID"""
        id1 = generate_stable_id(url="https://example.com/article1")
        id2 = generate_stable_id(url="https://example.com/article2")
        assert id1 != id2

    def test_id_without_url(self):
        """测试无 URL 时使用其他字段生成 ID"""
        id1 = generate_stable_id(
            source="HN",
            title="Test Article",
            published_at="2026-01-09"
        )
        id2 = generate_stable_id(
            source="HN",
            title="Test Article",
            published_at="2026-01-09"
        )
        assert id1 == id2
        assert len(id1) == 32  # SHA256 前 32 个字符

    def test_id_length(self):
        """测试 ID 长度"""
        stable_id = generate_stable_id(url="https://example.com/test")
        assert len(stable_id) == 32


class TestDeduplicator:
    """去重器测试"""

    def test_dedupe_same_id(self):
        """测试相同 ID 去重"""
        dedup = Deduplicator()

        items = [
            {'id': 'abc123', 'title': 'Article 1', 'url': 'https://example.com/1'},
            {'id': 'abc123', 'title': 'Article 1 duplicate', 'url': 'https://example.com/1'},
            {'id': 'def456', 'title': 'Article 2', 'url': 'https://example.com/2'},
        ]

        result = dedup.dedupe(items)

        assert len(result) == 2
        assert result[0]['id'] == 'abc123'
        assert result[1]['id'] == 'def456'

    def test_dedupe_same_url(self):
        """测试相同规范化 URL 去重"""
        dedup = Deduplicator()

        items = [
            {'id': 'abc', 'title': 'Article 1', 'url': 'https://example.com/page?id=1'},
            {'id': 'def', 'title': 'Article 1', 'url': 'https://example.com/page?id=1&utm_source=x'},
        ]

        result = dedup.dedupe(items)

        # 第二个应该被去重（规范化后 URL 相同）
        assert len(result) == 1

    def test_is_new_flag(self):
        """测试 is_new 标记"""
        dedup = Deduplicator()

        items = [
            {'id': 'new_item', 'title': 'New Article', 'url': 'https://example.com/new'},
        ]

        result = dedup.dedupe(items)

        assert len(result) == 1
        assert result[0]['is_new'] == True

    def test_stats(self):
        """测试统计信息"""
        dedup = Deduplicator()

        items = [
            {'id': 'a', 'url': 'https://example.com/1'},
            {'id': 'b', 'url': 'https://example.com/2'},
        ]

        dedup.dedupe(items)
        stats = dedup.get_stats()

        assert stats['seen_ids'] == 2
        assert stats['seen_urls'] == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
