"""
Markdown 输出模块
生成人类可读的日报 Markdown 文件
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


def generate_markdown(
    items: List[Dict[str, Any]],
    stats: Dict[str, Any],
    output_path: str,
    since: Optional[str] = None,
    config_version: str = "1.0.0"
) -> str:
    """
    生成 Markdown 日报

    Args:
        items: 条目列表
        stats: 统计信息
        output_path: 输出文件路径
        since: 时间范围起点
        config_version: 配置版本

    Returns:
        str: 生成的 Markdown 内容
    """
    lines = []

    # 标题
    today = datetime.now().strftime('%Y-%m-%d')
    lines.append(f"# 今日选题候选（{today}）")
    lines.append("")

    # 元信息
    lines.append(f"**时间范围**：since {since or '未指定'}")
    lines.append(f"**总计**：raw {stats.get('raw_count', 0)} | "
                 f"filtered {stats.get('filtered_count', 0)} | "
                 f"deduped {stats.get('deduped_count', 0)} | "
                 f"new {stats.get('new_count', 0)}")
    lines.append(f"**配置版本**：sources.yaml v{config_version}")
    lines.append("")

    # 来源统计
    source_stats = stats.get('source_stats', {})
    if source_stats:
        lines.append("**各来源统计**：")
        for source_name, source_stat in source_stats.items():
            count = source_stat.get('filtered_count', source_stat.get('final_count', 0))
            status = "✅" if source_stat.get('success', False) else "❌"
            lines.append(f"- {status} {source_name}: {count} 条")
        lines.append("")

    lines.append("---")
    lines.append("")

    # 按来源分组
    items_by_source = {}
    for item in items:
        source = item.get('source', 'Unknown')
        if source not in items_by_source:
            items_by_source[source] = []
        items_by_source[source].append(item)

    # 按分数排序每个来源的条目
    for source in items_by_source:
        items_by_source[source].sort(key=lambda x: x.get('score', 0), reverse=True)

    # 生成每个来源的内容
    for source_name, source_items in items_by_source.items():
        # 只显示新条目
        new_items = [item for item in source_items if item.get('is_new', True)]

        if not new_items:
            continue

        lines.append(f"## {source_name}（{len(new_items)} 条）")
        lines.append("")

        for i, item in enumerate(new_items, 1):
            lines.extend(_format_item(item, i))
            lines.append("")

        lines.append("---")
        lines.append("")

    # 生成内容
    content = '\n'.join(lines)

    # 写入文件
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(content, encoding='utf-8')

    return content


def _format_item(item: Dict[str, Any], index: int) -> List[str]:
    """
    格式化单个条目

    Args:
        item: 条目数据
        index: 序号

    Returns:
        List[str]: 格式化后的行列表
    """
    lines = []

    title = item.get('title', '无标题')
    url = item.get('url', '#')
    score = item.get('score', 0)
    published_at = item.get('published_at', '时间未知')
    summary = item.get('summary', '')

    # 标题行
    lines.append(f"### {index}. [{title}]({url})")

    # 元信息行
    meta_parts = []
    if published_at and published_at != '时间未知':
        # 格式化时间
        try:
            from dateutil import parser
            dt = parser.parse(published_at)
            time_str = dt.strftime('%Y-%m-%d %H:%M')
        except Exception:
            time_str = published_at
        meta_parts.append(f"**时间**：{time_str}")
    else:
        meta_parts.append("**时间**：未知")

    meta_parts.append(f"**分数**：{score:.1f}")
    lines.append(f"- {' | '.join(meta_parts)}")

    # HN 特有信息
    raw = item.get('raw', {})
    if raw.get('points') is not None or raw.get('comments') is not None:
        points = raw.get('points', 0)
        comments = raw.get('comments', 0)
        lines.append(f"- **Points**: {points} | **Comments**: {comments}")

    # 摘要
    if summary:
        # 截断过长的摘要
        if len(summary) > 300:
            summary = summary[:300] + '...'
        lines.append(f"- **摘要**：{summary}")

    # 标签
    tags = item.get('tags', [])
    if tags:
        tags_str = ', '.join(f"`{tag}`" for tag in tags[:5])
        lines.append(f"- **标签**：{tags_str}")

    return lines
