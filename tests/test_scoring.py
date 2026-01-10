"""
评分模块单元测试
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.scoring import Scorer, ScoreBreakdown


class TestScoreBreakdown:
    """评分拆解测试"""

    def test_total_calculation(self):
        """测试总分计算"""
        breakdown = ScoreBreakdown(
            base=20,
            keyword_bonus=15,
            engagement_bonus=40,
            content_bonus=10
        )
        assert breakdown.total == 85

    def test_to_dict(self):
        """测试转换为字典"""
        breakdown = ScoreBreakdown(
            base=20,
            keyword_bonus=10,
            matched_keywords=['AI', 'LLM']
        )
        result = breakdown.to_dict()

        assert result['base'] == 20
        assert result['keyword_bonus'] == 10
        assert result['matched_keywords'] == ['AI', 'LLM']
        assert 'total' in result


class TestScorer:
    """评分器测试"""

    def test_base_score(self):
        """测试基础分"""
        scorer = Scorer()

        item = {'title': 'Test Article', 'summary': 'A test summary'}
        scoring_config = {'base_score': 30}

        result = scorer.score(item, 'test_source', scoring_config)

        assert result['score'] >= 30

    def test_keyword_bonus(self):
        """测试关键词加权"""
        scorer = Scorer()

        item = {
            'title': 'OpenAI releases new GPT model',
            'summary': 'A new AI model for agents'
        }
        scoring_config = {
            'base_score': 20,
            'keyword_bonus': [
                {'keywords': ['OpenAI', 'GPT'], 'bonus': 15},
                {'keywords': ['agent', 'AGI'], 'bonus': 10}
            ]
        }

        result = scorer.score(item, 'test_source', scoring_config)

        # 应该有关键词加分
        assert result['score'] > 20
        assert len(result['score_detail']['matched_keywords']) > 0

    def test_hn_engagement_scoring(self):
        """测试 Hacker News 互动评分"""
        scorer = Scorer()

        item = {
            'title': 'Show HN: My Project',
            'raw': {
                'points': 100,
                'comments': 50
            }
        }
        scoring_config = {
            'base_score': 20,
            'components': {
                'points_weight': 0.4,
                'comments_weight': 0.6
            }
        }

        result = scorer.score(item, 'hacker_news', scoring_config)

        # 预期: 20 + (100 * 0.4) + (50 * 0.6) = 20 + 40 + 30 = 90
        expected_engagement = 100 * 0.4 + 50 * 0.6
        assert result['score_detail']['engagement_bonus'] == expected_engagement

    def test_score_normalization(self):
        """测试评分归一化（在批量评分中进行 Min-Max 归一化）"""
        scorer = Scorer(normalization={
            'enabled': True,
            'min_score': 0,
            'max_score': 100
        })

        # 创建多个条目以测试批量归一化
        items = [
            {
                'title': 'Low engagement article',
                'raw': {'points': 10, 'comments': 5}
            },
            {
                'title': 'OpenAI GPT Claude Gemini AI LLM',
                'raw': {'points': 1000, 'comments': 500}
            },
            {
                'title': 'Medium engagement',
                'raw': {'points': 100, 'comments': 50}
            }
        ]
        scoring_config = {
            'base_score': 50,
            'components': {'points_weight': 0.4, 'comments_weight': 0.6},
            'keyword_bonus': [
                {'keywords': ['OpenAI', 'GPT', 'Claude', 'Gemini', 'AI', 'LLM'], 'bonus': 20}
            ]
        }

        results = scorer.score_batch(items, 'hacker_news', scoring_config)

        # 所有分数应该被归一化到 0-100 范围
        for item in results:
            assert item['score'] >= 0
            assert item['score'] <= 100

        # 最高分应该是 100，最低分应该是 0
        scores = [item['score'] for item in results]
        assert max(scores) == 100
        assert min(scores) == 0

    def test_batch_scoring(self):
        """测试批量评分"""
        scorer = Scorer()

        items = [
            {'title': 'Article 1', 'summary': 'Test 1'},
            {'title': 'Article 2', 'summary': 'Test 2'},
            {'title': 'Article 3 about AI', 'summary': 'Test 3'},
        ]
        scoring_config = {
            'base_score': 30,
            'keyword_bonus': [{'keywords': ['AI'], 'bonus': 10}]
        }

        results = scorer.score_batch(items, 'test', scoring_config)

        assert len(results) == 3
        for item in results:
            assert 'score' in item
            assert 'raw' in item
            assert 'score_detail' in item['raw']

    def test_global_keywords(self):
        """测试全局关键词"""
        global_keywords = {
            'ai_hot': {
                'keywords': ['OpenAI', 'Claude'],
                'bonus': 15
            }
        }
        scorer = Scorer(global_keywords=global_keywords)

        item = {'title': 'OpenAI news', 'summary': ''}
        result = scorer.score(item, 'test', {'base_score': 20})

        # 应该匹配全局关键词
        assert 'OpenAI' in result['score_detail']['matched_keywords']
        assert result['score'] >= 35  # 20 base + 15 bonus


class TestScoringFormula:
    """评分公式测试"""

    def test_hn_formula(self):
        """测试 HN 评分公式: base + (points * 0.4) + (comments * 0.6)"""
        scorer = Scorer()

        item = {
            'title': 'Test',
            'raw': {
                'points': 234,
                'comments': 89
            }
        }
        scoring_config = {
            'base_score': 20,
            'components': {
                'points_weight': 0.4,
                'comments_weight': 0.6
            }
        }

        result = scorer.score(item, 'hacker_news', scoring_config)

        # 验证公式
        expected_base = 20
        expected_engagement = 234 * 0.4 + 89 * 0.6

        assert result['score_detail']['base'] == expected_base
        assert result['score_detail']['engagement_bonus'] == expected_engagement


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
