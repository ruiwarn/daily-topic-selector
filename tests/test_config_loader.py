"""
配置加载器单元测试
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_loader import ConfigLoader, Config, SourceConfig


class TestConfigLoader:
    """配置加载器测试"""

    @pytest.fixture
    def config_loader(self):
        """创建配置加载器实例"""
        config_dir = project_root / 'skills' / 'daily-topic-selector' / 'config'
        return ConfigLoader(str(config_dir))

    def test_load_config(self, config_loader):
        """测试加载配置"""
        config = config_loader.load()

        assert config is not None
        assert config.version == '1.0.0'
        assert config.defaults is not None

    def test_defaults(self, config_loader):
        """测试默认配置"""
        config = config_loader.load()

        assert config.defaults.timeout == 20
        assert config.defaults.retries == 2
        assert 'DailyTopicSelector' in config.defaults.user_agent

    def test_sources_loaded(self, config_loader):
        """测试数据源加载"""
        config = config_loader.load()

        assert len(config.sources) >= 5
        assert 'hacker_news' in config.sources
        assert 'import_ai' in config.sources
        assert 'tldr_ai' in config.sources

    def test_source_config(self, config_loader):
        """测试单个数据源配置"""
        config = config_loader.load()
        hn = config.sources.get('hacker_news')

        assert hn is not None
        assert hn.name == 'Hacker News'
        assert hn.enabled == True
        assert len(hn.fetch_methods) > 0
        assert len(hn.default_tags) > 0

    def test_fetch_methods_priority(self, config_loader):
        """测试抓取方法优先级排序"""
        config = config_loader.load()
        hn = config.sources.get('hacker_news')

        # 方法应该按优先级排序
        priorities = [m.priority for m in hn.fetch_methods]
        assert priorities == sorted(priorities)

    def test_get_enabled_sources(self, config_loader):
        """测试获取启用的数据源"""
        config_loader.load()
        enabled = config_loader.get_enabled_sources()

        assert len(enabled) > 0
        for source in enabled:
            assert source.enabled == True

    def test_get_source(self, config_loader):
        """测试根据 ID 获取数据源"""
        config_loader.load()

        hn = config_loader.get_source('hacker_news')
        assert hn is not None
        assert hn.id == 'hacker_news'

        nonexistent = config_loader.get_source('nonexistent')
        assert nonexistent is None

    def test_scoring_config(self, config_loader):
        """测试评分配置"""
        config = config_loader.load()
        hn = config.sources.get('hacker_news')

        assert hn.scoring is not None
        assert hn.scoring.base_score == 20
        assert len(hn.scoring.keyword_bonus) > 0


class TestSourceConfig:
    """数据源配置测试"""

    @pytest.fixture
    def config_loader(self):
        config_dir = project_root / 'skills' / 'daily-topic-selector' / 'config'
        loader = ConfigLoader(str(config_dir))
        loader.load()
        return loader

    def test_hacker_news_config(self, config_loader):
        """测试 Hacker News 配置"""
        hn = config_loader.get_source('hacker_news')

        # 应该有 API 方法
        api_method = next(
            (m for m in hn.fetch_methods if m.method == 'api'),
            None
        )
        assert api_method is not None
        assert 'endpoints' in api_method.config

    def test_import_ai_config(self, config_loader):
        """测试 Import AI 配置"""
        import_ai = config_loader.get_source('import_ai')

        # 应该有 RSS 方法
        rss_method = next(
            (m for m in import_ai.fetch_methods if m.method == 'rss'),
            None
        )
        assert rss_method is not None
        assert 'url' in rss_method.config

    def test_tldr_ai_config(self, config_loader):
        """测试 TLDR AI 配置"""
        tldr = config_loader.get_source('tldr_ai')

        # 应该有 json_extract 方法
        json_method = next(
            (m for m in tldr.fetch_methods if m.method == 'json_extract'),
            None
        )
        assert json_method is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
