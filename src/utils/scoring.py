"""
评分工具模块
根据配置规则对内容进行评分
"""

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

        # 计算总分（归一化在批量评分时进行）
        total = breakdown.total

        return {
            'score': round(total, 2),
            'score_detail': breakdown.to_dict()
        }

    def _get_searchable_text(self, item: Dict[str, Any]) -> str:
        """
        获取用于关键词匹配的文本

        注意：只匹配 title 和 summary，不匹配 tags。
        因为 tags 可能包含 default_tags（由配置添加），
        如果匹配 tags 会导致所有条目都命中相同关键词。

        Args:
            item: 内容条目

        Returns:
            str: 合并后的文本
        """
        parts = [
            item.get('title', ''),
            item.get('summary', ''),
        ]

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

        components = scoring.get('components', {})
        points_weight = components.get('points_weight', 0.4)
        comments_weight = components.get('comments_weight', 0.6)

        return points * points_weight + comments * comments_weight

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

        # 第一遍：计算原始分数
        for item in items:
            score_result = self.score(item, source_id, source_scoring)
            item['score'] = score_result['score']
            item['raw'] = item.get('raw', {})
            item['raw']['score_detail'] = score_result['score_detail']
            result.append(item)

        # 第二遍：归一化（基于批次内的实际分数范围）
        if self.normalization.get('enabled', True) and len(result) > 1:
            scores = [item['score'] for item in result]
            raw_min = min(scores)
            raw_max = max(scores)

            # 只有当分数有差异时才归一化
            if raw_max > raw_min:
                target_min = self.normalization.get('min_score', 0)
                target_max = self.normalization.get('max_score', 100)

                for item in result:
                    raw_score = item['score']
                    # Min-Max 归一化
                    normalized = target_min + (raw_score - raw_min) / (raw_max - raw_min) * (target_max - target_min)
                    item['score'] = round(normalized, 1)

        return result
