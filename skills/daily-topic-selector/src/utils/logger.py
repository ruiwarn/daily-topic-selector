"""
日志工具模块
提供统一的日志配置和管理
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


# 日志格式
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def setup_logger(
    name: str = 'daily-topic-selector',
    level: str = 'INFO',
    log_file: Optional[str] = None,
    console: bool = True
) -> logging.Logger:
    """
    设置日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别（DEBUG, INFO, WARNING, ERROR）
        log_file: 日志文件路径
        console: 是否输出到控制台

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    logger = logging.getLogger(name)

    # 避免重复配置
    if logger.handlers:
        return logger

    # 设置日志级别
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR
    }
    logger.setLevel(level_map.get(level.upper(), logging.INFO))

    # 创建格式化器
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    # 控制台处理器
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 文件处理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = 'daily-topic-selector') -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        logging.Logger: 日志记录器
    """
    return logging.getLogger(name)


class FetchLogger:
    """
    抓取日志记录器

    专门用于记录抓取过程，支持结构化日志和文件输出
    """

    def __init__(self, log_file: Optional[str] = None):
        """
        初始化抓取日志记录器

        Args:
            log_file: 日志文件路径
        """
        self.log_file = Path(log_file) if log_file else None
        self.entries = []
        self._start_time = None

    def start(self, args: dict):
        """
        记录运行开始

        Args:
            args: 运行参数
        """
        self._start_time = datetime.now()
        self._log(f"========== 开始运行 ==========")
        self._log(f"时间: {self._start_time.isoformat()}")
        self._log(f"参数: {args}")
        self._log("")

    def log_source_start(self, source_name: str):
        """记录源抓取开始"""
        self._log(f"[{source_name}] 开始抓取...")

    def log_source_end(self, source_name: str, count: int, success: bool, error: str = None):
        """
        记录源抓取结束

        Args:
            source_name: 源名称
            count: 抓取数量
            success: 是否成功
            error: 错误信息
        """
        status = "成功" if success else "失败"
        self._log(f"[{source_name}] 抓取{status}，获取 {count} 条")
        if error:
            self._log(f"[{source_name}] 错误: {error}")
        self._log("")

    def log_stats(self, stats: dict):
        """
        记录统计信息

        Args:
            stats: 统计数据
        """
        self._log("========== 统计信息 ==========")
        for key, value in stats.items():
            self._log(f"  {key}: {value}")
        self._log("")

    def log_output(self, files: list):
        """
        记录输出文件

        Args:
            files: 输出文件列表
        """
        self._log("========== 输出文件 ==========")
        for f in files:
            self._log(f"  - {f}")
        self._log("")

    def end(self):
        """记录运行结束"""
        end_time = datetime.now()
        duration = (end_time - self._start_time).total_seconds() if self._start_time else 0
        self._log(f"========== 运行结束 ==========")
        self._log(f"结束时间: {end_time.isoformat()}")
        self._log(f"耗时: {duration:.2f} 秒")

    def _log(self, message: str):
        """添加日志条目"""
        self.entries.append(message)

    def save(self):
        """保存日志到文件"""
        if not self.log_file:
            return

        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.entries))

    def get_content(self) -> str:
        """获取日志内容"""
        return '\n'.join(self.entries)
