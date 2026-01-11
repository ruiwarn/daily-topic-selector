"""
评分工具模块
根据配置规则对内容进行评分
"""

import math
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ScoreBreakdown:
    """评分拆解"""
    base: float = 0.0
    keyword_bonus: float = 0.0
    engagement_bonus: float = 0.0
    content_bonus: float = 0.0
    matched_keywords: List[str] = None

    def __post_init__(self):
        if self.matched_keywords is None:
            self.matched_keywords = []

    @property
    def total(self) -> float:
        """计算总分"""
        return self.base + self.keyword_bonus + self.engagement_bonus + self.content_bonus

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'base': self.base,
            'keyword_bonus': self.keyword_bonus,
            'engagement_bonus': self.engagement_bonus,
            'content_bonus': self.content_bonus,
            'matched_keywords': self.matched_keywords,
            'total': self.total
        }


class Scorer:
    """
    评分器

    根据配置规则对内容进行评分，支持：
    - 基础分（按来源配置）
    - 关键词加权
    - 互动数据加权（HN points/comments）
    - 内容长度加权
    """

    def __init__(
        self,
        source_config: Optional[Dict[str, Any]] = None,
        global_keywords: Optional[Dict[str, Any]] = None,
        normalization: Optional[Dict[str, Any]] = None
    ):
        """
        初始化评分器

        Args:
            source_config: 数据源评分配置
            global_keywords: 全局关键词配置
            normalization: 评分归一化配置
        """
        self.source_config = source_config or {}
        self.global_keywords = global_keywords or {}
        self.normalization = normalization or {
            'enabled': True,
            'min_score': 0,
            'max_score': 100
        }

    def score(self, item: Dict[str, Any], source_id: str,
              source_scoring: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        对单个内容条目评分

        Args:
            item: 内容条目
            source_id: 数据源 ID
            source_scoring: 数据源评分配置

        Returns:
            Dict[str, Any]: 包含 score 和 score_detail 的字典
        """
        scoring = source_scoring or {}
        breakdown = ScoreBreakdown()

        # 1. 基础分
        breakdown.base = scoring.get('base_score', 30)

        # 2. 关键词加权
        text = self._get_searchable_text(item)
        keyword_bonus, matched = self._calculate_keyword_bonus(text, scoring)
        breakdown.keyword_bonus = keyword_bonus
        breakdown.matched_keywords = matched

        # 3. 互动数据加权（Hacker News 特有）
        if source_id == 'hacker_news':
            breakdown.engagement_bonus = self._calculate_hn_engagement(item, scoring)

        # 4. 内容长度加权
        content_bonus_config = scoring.get('content_length_bonus')
        if content_bonus_config:
            breakdown.content_bonus = self._calculate_content_bonus(item, content_bonus_config)

        # 计算总分
        total = breakdown.total

        # 归一化
        if self.normalization.get('enabled', True):
            min_score = self.normalization.get('min_score', 0)
            max_score = self.normalization.get('max_score', 100)
            total = max(min_score, min(max_score, total))

        return {
            'score': round(total, 2),
            'score_detail': breakdown.to_dict()
        }

    def _get_searchable_text(self, item: Dict[str, Any]) -> str:
        """
        获取用于关键词匹配的文本

        Args:
            item: 内容条目

        Returns:
            str: 合并后的文本
        """
        parts = [
            item.get('title', ''),
            item.get('summary', ''),
        ]
        # 包含标签
        tags = item.get('tags', [])
        if tags:
            parts.extend(tags)

        return ' '.join(str(p) for p in parts if p)

    def _calculate_keyword_bonus(
        self,
        text: str,
        scoring: Dict[str, Any]
    ) -> tuple[float, List[str]]:
        """
        计算关键词加权分

        Args:
            text: 待匹配文本
            scoring: 评分配置

        Returns:
            tuple[float, List[str]]: (加权分, 匹配到的关键词列表)
        """
        total_bonus = 0.0
        matched_keywords = []

        text_lower = text.lower()

        # 来源特定关键词
        for bonus_config in scoring.get('keyword_bonus', []):
            keywords = bonus_config.get('keywords', [])
            bonus = bonus_config.get('bonus', 0)

            for keyword in keywords:
                if keyword.lower() in text_lower:
                    total_bonus += bonus
                    matched_keywords.append(keyword)
                    break  # 每组只加一次

        # 全局关键词
        for group_name, group_config in self.global_keywords.items():
            keywords = group_config.get('keywords', [])
            bonus = group_config.get('bonus', 0)

            for keyword in keywords:
                if keyword.lower() in text_lower:
                    # 避免与来源关键词重复计分
                    if keyword not in matched_keywords:
                        total_bonus += bonus
                        matched_keywords.append(keyword)
                    break

        return total_bonus, matched_keywords

    def _calculate_hn_engagement(
        self,
        item: Dict[str, Any],
        scoring: Dict[str, Any]
    ) -> float:
        """
        计算 Hacker News 互动数据加权分

        公式：points * points_weight + comments * comments_weight

        Args:
            item: 内容条目
            scoring: 评分配置

        Returns:
            float: 互动加权分
        """
        raw = item.get('raw', {})
        points = raw.get('points', 0) or 0
        comments = raw.get('comments', 0) or 0

        engagement_config = scoring.get('engagement', {})
        if engagement_config:
            points_weight = engagement_config.get('points_weight', 0.4)
            comments_weight = engagement_config.get('comments_weight', 0.6)
            transform = str(engagement_config.get('transform', '')).lower()
            scale = engagement_config.get('scale', 1.0)
        else:
            components = scoring.get('components', {})
            points_weight = components.get('points_weight', 0.4)
            comments_weight = components.get('comments_weight', 0.6)
            transform = ''
            scale = 1.0

        def apply_transform(value: float) -> float:
            if transform == 'log1p':
                return math.log1p(max(value, 0))
            if transform == 'sqrt':
                return math.sqrt(max(value, 0))
            return value

        transformed_points = apply_transform(points)
        transformed_comments = apply_transform(comments)

        return (transformed_points * points_weight + transformed_comments * comments_weight) * scale

    def _calculate_content_bonus(
        self,
        item: Dict[str, Any],
        config: Dict[str, Any]
    ) -> float:
        """
        计算内容长度加权分

        Args:
            item: 内容条目
            config: 内容长度加权配置

        Returns:
            float: 内容长度加权分
        """
        raw = item.get('raw', {})
        full_content = raw.get('full_content', '') or item.get('summary', '')

        if not full_content:
            return 0.0

        threshold = config.get('threshold', 5000)
        bonus = config.get('bonus', 20)

        if len(full_content) >= threshold:
            return bonus

        return 0.0

    def score_batch(
        self,
        items: List[Dict[str, Any]],
        source_id: str,
        source_scoring: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        批量评分

        Args:
            items: 内容条目列表
            source_id: 数据源 ID
            source_scoring: 评分配置

        Returns:
            List[Dict[str, Any]]: 带评分的条目列表
        """
        result = []

        for item in items:
            score_result = self.score(item, source_id, source_scoring)
            item['score'] = score_result['score']
            item['raw'] = item.get('raw', {})
            item['raw']['score_detail'] = score_result['score_detail']
            result.append(item)

        return result
