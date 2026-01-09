"""
配置加载器模块
负责加载和验证 sources.yaml 和 scoring.yaml 配置文件
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import yaml


@dataclass
class FetchMethodConfig:
    """抓取方法配置"""
    method: str  # rss, api, html, json_extract
    priority: int
    config: Dict[str, Any]
    limitations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ScoringConfig:
    """评分配置"""
    base_score: float
    formula: Optional[str] = None
    components: Dict[str, float] = field(default_factory=dict)
    keyword_bonus: List[Dict[str, Any]] = field(default_factory=list)
    content_length_bonus: Optional[Dict[str, Any]] = None


@dataclass
class SourceConfig:
    """单个数据源配置"""
    id: str
    enabled: bool
    name: str
    description: str
    fetch_methods: List[FetchMethodConfig]
    field_mapping: Dict[str, str]
    default_tags: List[str]
    scoring: ScoringConfig


@dataclass
class GlobalDefaults:
    """全局默认配置"""
    timeout: int = 20
    retries: int = 2
    user_agent: str = "DailyTopicSelector/1.0"
    request_delay: float = 0.5


@dataclass
class Config:
    """完整配置"""
    version: str
    defaults: GlobalDefaults
    sources: Dict[str, SourceConfig]
    scoring_config: Optional[Dict[str, Any]] = None


class ConfigLoader:
    """
    配置加载器

    负责从 YAML 文件加载配置并进行验证
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置加载器

        Args:
            config_dir: 配置文件目录路径，默认为项目根目录下的 config/
        """
        if config_dir is None:
            # 默认使用项目根目录下的 config 目录
            project_root = Path(__file__).parent.parent
            config_dir = project_root / "config"

        self.config_dir = Path(config_dir)
        self._config: Optional[Config] = None

    def load(self, sources_file: str = "sources.yaml",
             scoring_file: str = "scoring.yaml") -> Config:
        """
        加载配置文件

        Args:
            sources_file: 数据源配置文件名
            scoring_file: 评分配置文件名

        Returns:
            Config: 解析后的配置对象
        """
        # 加载数据源配置
        sources_path = self.config_dir / sources_file
        with open(sources_path, 'r', encoding='utf-8') as f:
            sources_data = yaml.safe_load(f)

        # 加载评分配置
        scoring_path = self.config_dir / scoring_file
        scoring_data = None
        if scoring_path.exists():
            with open(scoring_path, 'r', encoding='utf-8') as f:
                scoring_data = yaml.safe_load(f)

        # 解析配置
        self._config = self._parse_config(sources_data, scoring_data)
        return self._config

    def _parse_config(self, sources_data: Dict,
                      scoring_data: Optional[Dict]) -> Config:
        """
        解析配置数据为配置对象

        Args:
            sources_data: 数据源配置原始数据
            scoring_data: 评分配置原始数据

        Returns:
            Config: 解析后的配置对象
        """
        # 解析全局默认配置
        defaults_data = sources_data.get('defaults', {})
        defaults = GlobalDefaults(
            timeout=defaults_data.get('timeout', 20),
            retries=defaults_data.get('retries', 2),
            user_agent=defaults_data.get('user_agent', "DailyTopicSelector/1.0"),
            request_delay=defaults_data.get('request_delay', 0.5)
        )

        # 解析数据源配置
        sources = {}
        for source_id, source_data in sources_data.get('sources', {}).items():
            sources[source_id] = self._parse_source(source_id, source_data)

        return Config(
            version=sources_data.get('version', '1.0.0'),
            defaults=defaults,
            sources=sources,
            scoring_config=scoring_data
        )

    def _parse_source(self, source_id: str, data: Dict) -> SourceConfig:
        """
        解析单个数据源配置

        Args:
            source_id: 数据源 ID
            data: 数据源配置数据

        Returns:
            SourceConfig: 数据源配置对象
        """
        # 解析抓取方法
        fetch_methods = []
        for method_data in data.get('fetch_methods', []):
            fetch_methods.append(FetchMethodConfig(
                method=method_data['method'],
                priority=method_data.get('priority', 1),
                config=method_data.get('config', {}),
                limitations=method_data.get('limitations', []),
                warnings=method_data.get('warnings', [])
            ))

        # 按优先级排序
        fetch_methods.sort(key=lambda x: x.priority)

        # 解析评分配置
        scoring_data = data.get('scoring', {})
        scoring = ScoringConfig(
            base_score=scoring_data.get('base_score', 30),
            formula=scoring_data.get('formula'),
            components=scoring_data.get('components', {}),
            keyword_bonus=scoring_data.get('keyword_bonus', []),
            content_length_bonus=scoring_data.get('content_length_bonus')
        )

        return SourceConfig(
            id=source_id,
            enabled=data.get('enabled', True),
            name=data.get('name', source_id),
            description=data.get('description', ''),
            fetch_methods=fetch_methods,
            field_mapping=data.get('field_mapping', {}),
            default_tags=data.get('default_tags', []),
            scoring=scoring
        )

    def get_enabled_sources(self) -> List[SourceConfig]:
        """
        获取所有启用的数据源

        Returns:
            List[SourceConfig]: 启用的数据源配置列表
        """
        if self._config is None:
            raise RuntimeError("配置未加载，请先调用 load() 方法")

        return [s for s in self._config.sources.values() if s.enabled]

    def get_source(self, source_id: str) -> Optional[SourceConfig]:
        """
        根据 ID 获取数据源配置

        Args:
            source_id: 数据源 ID

        Returns:
            SourceConfig: 数据源配置，不存在则返回 None
        """
        if self._config is None:
            raise RuntimeError("配置未加载，请先调用 load() 方法")

        return self._config.sources.get(source_id)

    @property
    def config(self) -> Config:
        """获取当前配置"""
        if self._config is None:
            raise RuntimeError("配置未加载，请先调用 load() 方法")
        return self._config


# 便捷函数
def load_config(config_dir: Optional[str] = None) -> Config:
    """
    便捷函数：加载配置

    Args:
        config_dir: 配置目录路径

    Returns:
        Config: 配置对象
    """
    loader = ConfigLoader(config_dir)
    return loader.load()
