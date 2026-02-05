#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP 客户端模块
提供全局共享的 HTTP Session，复用 TCP 连接
"""

import threading
import logging
import time
import os
import json as _json
from typing import Optional, Dict, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# 全局 Session 实例
_http_session: Optional[requests.Session] = None
_http_session_no_retry: Optional[requests.Session] = None
_session_lock = threading.Lock()


def _offline_mode_enabled() -> bool:
    return str(os.environ.get("OFFLINE_MODE", "0")).strip().lower() in ("1", "true", "yes")


def _offline_sleep(env_name: str):
    try:
        ms = int(str(os.environ.get(env_name, "")).strip() or "0")
    except Exception:
        ms = 0
    if ms > 0:
        time.sleep(ms / 1000.0)


def _extract_merged_text(payload: Any) -> str:
    try:
        if not isinstance(payload, dict):
            return ""
        contents = payload.get("contents") or []
        if not contents or not isinstance(contents[0], dict):
            return ""
        parts = contents[0].get("parts") or []
        if not parts or not isinstance(parts[0], dict):
            return ""
        text = parts[0].get("text")
        return text if isinstance(text, str) else ""
    except Exception:
        return ""


def _offline_generate_output_text(merged_text: str) -> str:
    t = merged_text or ""

    # 内容合规：返回“合规”
    if "如果内容合规" in t and "回复\"合规\"" in t:
        return "合规"

    # 合并分析：返回可解析的“合规 + 六维度”格式
    if "合规：是/否" in t and "上装" in t and "下装" in t and "头戴" in t and "手持" in t:
        return (
            "合规：是\n"
            "不合规原因：无\n"
            "表情：无\n"
            "上装：白色T恤\n"
            "下装：蓝色休闲长裤\n"
            "头戴：无\n"
            "手持：无"
        )

    # 服装/配件提取
    if "提取角色的装扮信息" in t and "上装" in t and "下装" in t and "头戴" in t and "手持" in t:
        return "上装：无\n下装：无\n头戴：无\n手持：无"

    # 头部特征分析（HeadMatcher）
    if "眼睛形状" in t and "嘴型" in t and "脸部动态" in t and "情感强度" in t:
        return "眼睛形状：正常\n嘴型：微笑\n表情：开心\n脸部动态：自然\n情感强度：中等"

    # 身体姿势分析（BodyMatcher）
    if "手部姿势" in t and "腿部姿势" in t and "整体姿势" in t and "姿势意义" in t:
        return "手部姿势：自然\n腿部姿势：站立\n整体姿势：直立\n姿势意义：休息\n情感偏向：积极"

    # 动作类型分类：只返回一个动作类型
    if "动作类型" in t and ("站姿" in t or "跑动" in t or "跳跃" in t):
        return "站姿"

    # 维度打分：把“XX”替换成 50
    if "请按照以下格式返回每个维度的得分" in t and "：XX" in t:
        out_lines = []
        for line in t.splitlines():
            s = line.strip()
            if not s:
                continue
            if "：XX" in s:
                out_lines.append(s.replace("：XX", "：50"))
            elif ":XX" in s:
                out_lines.append(s.replace(":XX", "：50"))
        if out_lines:
            return "\n".join(out_lines)

    # 兜底：给一个可解析的短输出
    return "合规"


def _build_offline_response(url: str, payload: Any) -> requests.Response:
    merged_text = _extract_merged_text(payload)
    _offline_sleep("OFFLINE_LLM_LATENCY_MS")
    data = {"output_text": _offline_generate_output_text(merged_text)}
    resp = requests.Response()
    resp.status_code = 200
    resp.url = url
    resp.encoding = "utf-8"
    resp._content = _json.dumps(data, ensure_ascii=False).encode("utf-8")
    resp.headers["Content-Type"] = "application/json; charset=utf-8"
    return resp


def _build_offline_get_response(url: str) -> requests.Response:
    _offline_sleep("OFFLINE_HTTP_LATENCY_MS")
    resp = requests.Response()
    resp.status_code = 200
    resp.url = url
    resp.encoding = "utf-8"
    resp._content = b""
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    return resp


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


def get_http_session_no_retry() -> requests.Session:
    """
    获取不带自动重试的共享 Session

    适用场景：
    - 调用方已实现业务重试（避免“多层重试叠加”导致超时雪崩）
    - 需要精准控制超时与重试时机
    """
    global _http_session_no_retry

    if _http_session_no_retry is None:
        with _session_lock:
            if _http_session_no_retry is None:
                _http_session_no_retry = _create_session_no_retry()
                logger.info("HTTP Session(no-retry) 初始化完成")

    return _http_session_no_retry


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


def _create_session_no_retry() -> requests.Session:
    """创建不带自动重试的 Session（仅连接复用）"""
    session = requests.Session()
    adapter = HTTPAdapter(
        max_retries=Retry(total=0),
        pool_connections=10,
        pool_maxsize=20
    )
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session


def http_post(
    url: str,
    json: Optional[Dict] = None,
    headers: Optional[Dict] = None,
    timeout: int = 90,
    use_retry: bool = True,
    deadline_monotonic: float | None = None,
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
    if _offline_mode_enabled():
        return _build_offline_response(url, json)
    if deadline_monotonic is not None:
        remaining = float(deadline_monotonic) - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("请求截止时间已过期")
        # requests 支持 timeout=(connect, read)
        if isinstance(timeout, tuple) and len(timeout) == 2:
            timeout = (timeout[0], min(float(timeout[1]), remaining))
        else:
            timeout = min(float(timeout), remaining)
    session = get_http_session() if use_retry else get_http_session_no_retry()
    return session.post(url, json=json, headers=headers, timeout=timeout, **kwargs)


def http_get(
    url: str,
    headers: Optional[Dict] = None,
    timeout: int = 30,
    use_retry: bool = True,
    deadline_monotonic: float | None = None,
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
    if _offline_mode_enabled():
        return _build_offline_get_response(url)
    if deadline_monotonic is not None:
        remaining = float(deadline_monotonic) - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("请求截止时间已过期")
        if isinstance(timeout, tuple) and len(timeout) == 2:
            timeout = (timeout[0], min(float(timeout[1]), remaining))
        else:
            timeout = min(float(timeout), remaining)
    session = get_http_session() if use_retry else get_http_session_no_retry()
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
    global _http_session_no_retry
    
    with _session_lock:
        if _http_session is not None:
            try:
                _http_session.close()
                logger.info("HTTP Session 已关闭")
            except Exception as e:
                logger.warning(f"关闭 HTTP Session 失败: {e}")
            finally:
                _http_session = None

        if _http_session_no_retry is not None:
            try:
                _http_session_no_retry.close()
                logger.info("HTTP Session(no-retry) 已关闭")
            except Exception as e:
                logger.warning(f"关闭 HTTP Session(no-retry) 失败: {e}")
            finally:
                _http_session_no_retry = None
