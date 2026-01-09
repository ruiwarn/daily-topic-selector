#!/usr/bin/env python3
"""
daily-topic-selector CLI 入口

每日选题抓取工具的命令行接口
"""

import argparse
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_loader import ConfigLoader, SourceConfig
from src.fetchers import create_fetcher, FetchResult
from src.utils.http import create_client
from src.utils.dedupe import Deduplicator
from src.utils.scoring import Scorer
from src.utils.time_utils import get_since_datetime, to_iso_string, is_within_range, parse_datetime
from src.utils.logger import setup_logger, FetchLogger
from src.utils.output_md import generate_markdown
from src.utils.output_json import generate_json, generate_meta


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='每日选题抓取工具 - 从多个内容源获取最新文章并评分排序',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python run.py --days 1
  python run.py --since 2026-01-08T00:00:00Z
  python run.py --only_sources hn,import_ai --limit_per_source 20
        '''
    )

    parser.add_argument(
        '--days', type=int, default=1,
        help='抓取最近 N 天内发布的内容（默认: 1）'
    )
    parser.add_argument(
        '--since', type=str, default=None,
        help='抓取该时间之后的内容（ISO 格式，优先于 --days）'
    )
    parser.add_argument(
        '--output_dir', type=str, default='.',
        help='输出目录（默认: 当前目录）'
    )
    parser.add_argument(
        '--limit_per_source', type=int, default=50,
        help='每个源最大抓取条数（默认: 50）'
    )
    parser.add_argument(
        '--only_sources', type=str, default=None,
        help='只抓取指定来源，逗号分隔（如: hn,tldr）'
    )
    parser.add_argument(
        '--config', type=str, default=None,
        help='配置文件目录路径'
    )
    parser.add_argument(
        '--cache_dir', type=str, default=None,
        help='缓存目录'
    )
    parser.add_argument(
        '--incremental', action='store_true', default=True,
        help='增量模式：只输出相对历史新增的内容'
    )
    parser.add_argument(
        '--no-incremental', action='store_false', dest='incremental',
        help='禁用增量模式'
    )
    parser.add_argument(
        '--history_file', type=str, default=None,
        help='历史存档文件路径'
    )
    parser.add_argument(
        '--timeout', type=int, default=20,
        help='单次请求超时（秒，默认: 20）'
    )
    parser.add_argument(
        '--retries', type=int, default=2,
        help='失败重试次数（默认: 2）'
    )
    parser.add_argument(
        '--concurrency', type=int, default=3,
        help='最大并发抓取数（默认: 3）'
    )
    parser.add_argument(
        '--delay', type=float, default=0.5,
        help='请求间隔（秒，默认: 0.5）'
    )
    parser.add_argument(
        '--log_level', type=str, default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='日志级别（默认: INFO）'
    )
    parser.add_argument(
        '--verbose', action='store_true',
        help='详细日志输出'
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    started_at = datetime.now()

    # 设置日志
    log_level = 'DEBUG' if args.verbose else args.log_level
    logger = setup_logger(level=log_level)

    # 输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 历史文件
    history_file = args.history_file or str(output_dir / 'history.jsonl')

    # 抓取日志
    fetch_log = FetchLogger(str(output_dir / 'fetch_log.txt'))
    fetch_log.start(vars(args))

    logger.info("=" * 50)
    logger.info("开始运行 daily-topic-selector")
    logger.info("=" * 50)

    # 加载配置
    # 优先级: --config 参数 > 用户配置目录 > skill 自带默认配置
    user_config_dir = Path.home() / '.config' / 'daily-topic-selector'
    default_config_dir = project_root / 'config'

    if args.config:
        config_dir = args.config
    elif user_config_dir.exists():
        config_dir = str(user_config_dir)
    else:
        config_dir = str(default_config_dir)

    logger.info(f"加载配置: {config_dir}")

    try:
        config_loader = ConfigLoader(config_dir)
        config = config_loader.load()
    except Exception as e:
        logger.error(f"配置加载失败: {e}")
        fetch_log.end()
        fetch_log.save()
        return 1

    # 确定时间范围
    if args.since:
        since_dt = parse_datetime(args.since)
    else:
        since_dt = get_since_datetime(args.days)
    since_str = to_iso_string(since_dt)
    logger.info(f"时间范围: since {since_str}")

    # 获取要抓取的源
    sources = config_loader.get_enabled_sources()

    # 过滤指定的源
    if args.only_sources:
        source_ids = [s.strip() for s in args.only_sources.split(',')]
        sources = [s for s in sources if s.id in source_ids]

    logger.info(f"将抓取 {len(sources)} 个数据源")

    # 创建 HTTP 客户端
    http_client = create_client(
        timeout=args.timeout,
        retries=args.retries,
        user_agent=config.defaults.user_agent,
        request_delay=args.delay
    )

    # 创建去重器
    deduplicator = Deduplicator(history_file if args.incremental else None)

    # 创建评分器
    scoring_config = config.scoring_config or {}
    scorer = Scorer(
        global_keywords=scoring_config.get('global_keywords', {}),
        normalization=scoring_config.get('normalization', {})
    )

    # 抓取所有源
    all_items = []
    source_stats = {}
    errors = []

    for source in sources:
        logger.info(f"抓取 [{source.name}]...")
        fetch_log.log_source_start(source.name)

        result = fetch_source(
            source=source,
            http_client=http_client,
            limit=args.limit_per_source
        )

        source_stat = {
            'success': result.success,
            'raw_count': result.raw_count,
            'method_used': result.method_used
        }

        if result.success:
            # 时间过滤
            filtered_items = [
                item for item in result.items
                if is_within_range(parse_datetime(item.get('published_at')), since_dt)
            ]

            # 评分
            scored_items = scorer.score_batch(
                filtered_items,
                source.id,
                source.scoring.__dict__ if hasattr(source.scoring, '__dict__') else {}
            )

            source_stat['filtered_count'] = len(scored_items)
            all_items.extend(scored_items)

            logger.info(f"  ✓ 获取 {result.raw_count} 条，过滤后 {len(scored_items)} 条")
            fetch_log.log_source_end(source.name, len(scored_items), True)

        else:
            source_stat['error'] = result.error
            errors.append({
                'source': source.name,
                'error': result.error
            })
            logger.error(f"  ✗ 抓取失败: {result.error}")
            fetch_log.log_source_end(source.name, 0, False, result.error)

        source_stats[source.name] = source_stat

    # 去重
    logger.info("执行去重...")
    deduped_items = deduplicator.dedupe(all_items)
    new_items = [item for item in deduped_items if item.get('is_new', True)]

    logger.info(f"去重后: {len(deduped_items)} 条，新增: {len(new_items)} 条")

    # 统计信息
    stats = {
        'started_at': started_at.isoformat(),
        'raw_count': sum(s.get('raw_count', 0) for s in source_stats.values()),
        'filtered_count': len(all_items),
        'deduped_count': len(deduped_items),
        'new_count': len(new_items),
        'source_stats': source_stats
    }

    fetch_log.log_stats(stats)

    # 生成输出文件
    output_files = []

    # 1. daily_topics.md
    md_path = str(output_dir / 'daily_topics.md')
    generate_markdown(
        items=deduped_items,
        stats=stats,
        output_path=md_path,
        since=since_str,
        config_version=config.version
    )
    output_files.append(md_path)
    logger.info(f"生成: {md_path}")

    # 2. daily_topics.json
    json_path = str(output_dir / 'daily_topics.json')
    generate_json(
        items=deduped_items,
        output_path=json_path
    )
    output_files.append(json_path)
    logger.info(f"生成: {json_path}")

    # 3. run_meta.json
    meta_path = str(output_dir / 'run_meta.json')
    generate_meta(
        stats=stats,
        args=vars(args),
        output_files=output_files,
        errors=errors,
        output_path=meta_path,
        config_version=config.version
    )
    output_files.append(meta_path)
    logger.info(f"生成: {meta_path}")

    # 保存历史记录
    if args.incremental:
        deduplicator.save_history(new_items, to_iso_string(datetime.now()))

    # 保存抓取日志
    fetch_log.log_output(output_files)
    fetch_log.end()
    fetch_log.save()
    output_files.append(str(output_dir / 'fetch_log.txt'))

    # 完成
    logger.info("=" * 50)
    logger.info(f"完成！共获取 {len(new_items)} 条新内容")
    logger.info("=" * 50)

    # 退出码
    if all(s.get('success', False) for s in source_stats.values()):
        return 0
    elif any(s.get('success', False) for s in source_stats.values()):
        return 0  # 部分成功
    else:
        return 1  # 全部失败


def fetch_source(
    source: SourceConfig,
    http_client,
    limit: int = 50
) -> FetchResult:
    """
    抓取单个数据源

    尝试多种方法，按优先级执行

    Args:
        source: 数据源配置
        http_client: HTTP 客户端
        limit: 最大条数

    Returns:
        FetchResult: 抓取结果
    """
    for fetch_method in source.fetch_methods:
        try:
            # 添加 limit 到配置
            config = dict(fetch_method.config)
            config['limit'] = limit

            fetcher = create_fetcher(
                method=fetch_method.method,
                source_id=source.id,
                source_name=source.name,
                config=config,
                http_client=http_client,
                default_tags=source.default_tags
            )

            result = fetcher.fetch()

            if result.success and result.items:
                return result

        except Exception as e:
            # 尝试下一个方法
            continue

    # 所有方法都失败
    return FetchResult(
        success=False,
        error="所有抓取方法都失败"
    )


if __name__ == '__main__':
    sys.exit(main())
