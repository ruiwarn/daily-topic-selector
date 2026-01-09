"""
JSON 输出模块
生成机器可读的 JSON 数据文件
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid


def generate_json(
    items: List[Dict[str, Any]],
    output_path: str
) -> str:
    """
    生成 JSON 数据文件

    Args:
        items: 条目列表
        output_path: 输出文件路径

    Returns:
        str: JSON 内容
    """
    # 确保所有字段都是可序列化的
    serializable_items = []
    for item in items:
        serializable_items.append(_make_serializable(item))

    # 生成 JSON
    content = json.dumps(
        serializable_items,
        ensure_ascii=False,
        indent=2
    )

    # 写入文件
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(content, encoding='utf-8')

    return content


def generate_meta(
    stats: Dict[str, Any],
    args: Dict[str, Any],
    output_files: List[str],
    errors: List[Dict[str, Any]],
    output_path: str,
    config_version: str = "1.0.0",
    scoring_version: str = "1.0.0"
) -> Dict[str, Any]:
    """
    生成运行元信息文件

    Args:
        stats: 统计信息
        args: 运行参数
        output_files: 输出文件列表
        errors: 错误列表
        output_path: 输出文件路径
        config_version: 配置版本
        scoring_version: 评分版本

    Returns:
        Dict[str, Any]: 元信息
    """
    meta = {
        'run_id': str(uuid.uuid4()),
        'started_at': stats.get('started_at', datetime.now().isoformat()),
        'finished_at': datetime.now().isoformat(),
        'args': _make_serializable(args),
        'config_version': config_version,
        'scoring_version': scoring_version,
        'source_stats': stats.get('source_stats', {}),
        'totals': {
            'raw_count': stats.get('raw_count', 0),
            'filtered_count': stats.get('filtered_count', 0),
            'deduped_count': stats.get('deduped_count', 0),
            'new_count': stats.get('new_count', 0)
        },
        'output_files': output_files,
        'errors': errors if errors else []
    }

    # 生成 JSON
    content = json.dumps(meta, ensure_ascii=False, indent=2)

    # 写入文件
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(content, encoding='utf-8')

    return meta


def _make_serializable(obj: Any) -> Any:
    """
    将对象转换为可 JSON 序列化的格式

    Args:
        obj: 任意对象

    Returns:
        Any: 可序列化的对象
    """
    if obj is None:
        return None

    if isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, datetime):
        return obj.isoformat()

    if isinstance(obj, (list, tuple)):
        return [_make_serializable(item) for item in obj]

    if isinstance(obj, dict):
        return {
            str(key): _make_serializable(value)
            for key, value in obj.items()
        }

    # 其他类型转为字符串
    return str(obj)
