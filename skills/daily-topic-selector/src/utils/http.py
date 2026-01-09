"""
HTTP 请求工具模块
提供统一的 HTTP 请求封装，支持重试、超时、User-Agent 设置
"""

import time
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


class HttpClient:
    """
    HTTP 客户端

    提供统一的 HTTP 请求接口，支持：
    - 自动重试（指数退避）
    - 超时配置
    - User-Agent 设置
    - 请求间隔控制
    - 失败日志记录
    """

    def __init__(
        self,
        timeout: int = 20,
        retries: int = 2,
        user_agent: str = "DailyTopicSelector/1.0",
        request_delay: float = 0.5
    ):
        """
        初始化 HTTP 客户端

        Args:
            timeout: 请求超时时间（秒）
            retries: 失败重试次数
            user_agent: User-Agent 字符串
            request_delay: 请求间隔（秒）
        """
        self.timeout = timeout
        self.retries = retries
        self.user_agent = user_agent
        self.request_delay = request_delay
        self._last_request_time = 0

        # 创建带重试机制的 session
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """
        创建带重试机制的 Session

        Returns:
            requests.Session: 配置好的 Session 对象
        """
        session = requests.Session()

        # 配置重试策略
        retry_strategy = Retry(
            total=self.retries,
            backoff_factor=1,  # 指数退避：1s, 2s, 4s...
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # 设置默认请求头
        session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })

        return session

    def _wait_for_delay(self):
        """
        等待请求间隔时间
        避免请求过于频繁被封禁
        """
        if self.request_delay > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.request_delay:
                time.sleep(self.request_delay - elapsed)

    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> requests.Response:
        """
        发送 GET 请求

        Args:
            url: 请求 URL
            headers: 额外的请求头
            params: URL 参数
            timeout: 超时时间（覆盖默认值）

        Returns:
            requests.Response: 响应对象

        Raises:
            requests.RequestException: 请求失败时抛出
        """
        self._wait_for_delay()

        try:
            logger.debug(f"GET {url}")
            response = self.session.get(
                url,
                headers=headers,
                params=params,
                timeout=timeout or self.timeout
            )
            self._last_request_time = time.time()

            response.raise_for_status()
            return response

        except requests.RequestException as e:
            logger.error(f"请求失败: {url}, 错误: {e}")
            raise

    def get_json(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> Any:
        """
        发送 GET 请求并解析 JSON 响应

        Args:
            url: 请求 URL
            headers: 额外的请求头
            params: URL 参数
            timeout: 超时时间

        Returns:
            Any: 解析后的 JSON 数据
        """
        response = self.get(url, headers, params, timeout)
        return response.json()

    def get_text(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        encoding: Optional[str] = None
    ) -> str:
        """
        发送 GET 请求并返回文本内容

        Args:
            url: 请求 URL
            headers: 额外的请求头
            params: URL 参数
            timeout: 超时时间
            encoding: 强制指定编码

        Returns:
            str: 响应文本
        """
        response = self.get(url, headers, params, timeout)

        if encoding:
            response.encoding = encoding

        return response.text

    def close(self):
        """关闭 Session"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 创建默认客户端实例
_default_client: Optional[HttpClient] = None


def get_client(
    timeout: int = 20,
    retries: int = 2,
    user_agent: str = "DailyTopicSelector/1.0",
    request_delay: float = 0.5
) -> HttpClient:
    """
    获取或创建 HTTP 客户端

    Args:
        timeout: 请求超时时间
        retries: 重试次数
        user_agent: User-Agent 字符串
        request_delay: 请求间隔

    Returns:
        HttpClient: HTTP 客户端实例
    """
    global _default_client

    if _default_client is None:
        _default_client = HttpClient(
            timeout=timeout,
            retries=retries,
            user_agent=user_agent,
            request_delay=request_delay
        )

    return _default_client


def create_client(
    timeout: int = 20,
    retries: int = 2,
    user_agent: str = "DailyTopicSelector/1.0",
    request_delay: float = 0.5
) -> HttpClient:
    """
    创建新的 HTTP 客户端实例

    Args:
        timeout: 请求超时时间
        retries: 重试次数
        user_agent: User-Agent 字符串
        request_delay: 请求间隔

    Returns:
        HttpClient: 新的 HTTP 客户端实例
    """
    return HttpClient(
        timeout=timeout,
        retries=retries,
        user_agent=user_agent,
        request_delay=request_delay
    )
