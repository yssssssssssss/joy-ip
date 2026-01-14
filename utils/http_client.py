#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP 客户端模块
提供全局共享的 HTTP Session，复用 TCP 连接
"""

import threading
import logging
from typing import Optional, Dict, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# 全局 Session 实例
_http_session: Optional[requests.Session] = None
_session_lock = threading.Lock()


def get_http_session() -> requests.Session:
    """
    获取全局共享的 HTTP Session
    
    特性：
    - 连接池复用（减少 TCP 握手开销）
    - 自动重试（3次，指数退避）
    - 线程安全
    
    Returns:
        requests.Session: 共享的 Session 实例
    """
    global _http_session
    
    if _http_session is None:
        with _session_lock:
            if _http_session is None:
                _http_session = _create_session()
                logger.info("HTTP Session 初始化完成")
    
    return _http_session


def _create_session() -> requests.Session:
    """创建配置好的 Session"""
    session = requests.Session()
    
    # 配置重试策略（包含429频率限制错误）
    retry_strategy = Retry(
        total=3,
        backoff_factor=1.0,  # 增加退避时间：1s, 2s, 4s
        status_forcelist=[429, 500, 502, 503, 504],  # 添加429
        allowed_methods=["GET", "POST"],
        respect_retry_after_header=True  # 尊重服务器返回的Retry-After头
    )
    
    # 配置连接池
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,  # 连接池大小
        pool_maxsize=20       # 最大连接数
    )
    
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    
    return session


def http_post(
    url: str,
    json: Optional[Dict] = None,
    headers: Optional[Dict] = None,
    timeout: int = 60,
    **kwargs
) -> requests.Response:
    """
    发送 POST 请求（使用共享 Session）
    
    Args:
        url: 请求 URL
        json: JSON 数据
        headers: 请求头
        timeout: 超时时间（秒）
        **kwargs: 其他 requests 参数
        
    Returns:
        requests.Response
    """
    session = get_http_session()
    return session.post(url, json=json, headers=headers, timeout=timeout, **kwargs)


def http_get(
    url: str,
    headers: Optional[Dict] = None,
    timeout: int = 30,
    **kwargs
) -> requests.Response:
    """
    发送 GET 请求（使用共享 Session）
    
    Args:
        url: 请求 URL
        headers: 请求头
        timeout: 超时时间（秒）
        **kwargs: 其他 requests 参数
        
    Returns:
        requests.Response
    """
    session = get_http_session()
    return session.get(url, headers=headers, timeout=timeout, **kwargs)


def parse_ai_response(data: Dict[str, Any]) -> str:
    """
    统一解析 AI API 响应
    
    支持格式：
    - OpenAI 格式 (choices[].message.content)
    - Gemini 格式 (candidates[].content.parts[].text)
    - JD Cloud 格式 (choices[].message.content.text)
    - 直接 output_text 格式
    
    Args:
        data: API 响应 JSON
        
    Returns:
        str: 解析出的文本内容
    """
    result = ""
    
    # 格式1: OpenAI 兼容格式 / JD Cloud 格式
    if isinstance(data, dict) and "choices" in data:
        choices = data.get("choices") or []
        if choices:
            msg = choices[0].get("message") or {}
            content = msg.get("content")
            
            if isinstance(content, str):
                result = content.strip()
            elif isinstance(content, dict):
                # JD Cloud / Gemini 格式: content 是对象，包含 text 字段
                text = content.get("text")
                if isinstance(text, str):
                    result = text.strip()
    
    # 格式2: Gemini candidates 格式
    if not result and isinstance(data, dict) and "candidates" in data:
        candidates = data.get("candidates") or []
        if candidates:
            content_obj = candidates[0].get("content") or {}
            parts = content_obj.get("parts") or []
            texts = []
            for part in parts:
                if isinstance(part, dict):
                    # 跳过思考内容
                    if part.get("thought", False):
                        continue
                    text = part.get("text")
                    if isinstance(text, str):
                        texts.append(text)
            if texts:
                result = "\n".join(texts).strip()
    
    # 格式3: 直接 output_text
    if not result and isinstance(data, dict):
        output = data.get("output_text")
        if isinstance(output, str) and output.strip():
            result = output.strip()
    
    return result


def close_session():
    """关闭全局 Session（通常在应用退出时调用）"""
    global _http_session
    
    with _session_lock:
        if _http_session is not None:
            try:
                _http_session.close()
                logger.info("HTTP Session 已关闭")
            except Exception as e:
                logger.warning(f"关闭 HTTP Session 失败: {e}")
            finally:
                _http_session = None
