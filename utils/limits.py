#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并发与速率限制工具

目标：
- 为外部服务调用提供统一的并发上限与速率控制，避免高并发下的超时雪崩/429风暴
- 尽量保持实现简单、无额外依赖，便于通过环境变量快速调参与回滚
"""

from __future__ import annotations

import os
import random
import threading
import time
from contextlib import contextmanager
from typing import Iterator, Optional


def _env_int(name: str, default: int, min_value: int = 1, max_value: int | None = None) -> int:
    raw = os.environ.get(name)
    try:
        value = int(str(raw).strip()) if raw is not None and str(raw).strip() else int(default)
    except Exception:
        value = int(default)
    if max_value is not None:
        value = min(int(max_value), value)
    return max(int(min_value), value)


def _env_float(name: str, default: float, min_value: float = 0.0, max_value: float | None = None) -> float:
    raw = os.environ.get(name)
    try:
        value = float(str(raw).strip()) if raw is not None and str(raw).strip() else float(default)
    except Exception:
        value = float(default)
    if max_value is not None:
        value = min(float(max_value), value)
    return max(float(min_value), value)


class ConcurrencyLimiter:
    """简单并发限制器（Semaphore 包装）。"""

    def __init__(self, name: str, max_concurrent: int):
        self.name = str(name)
        self.max_concurrent = max(1, int(max_concurrent))
        self._sem = threading.BoundedSemaphore(self.max_concurrent)

    @contextmanager
    def acquire(self, timeout_s: float | None = None) -> Iterator[None]:
        if timeout_s is None:
            ok = self._sem.acquire()
        else:
            ok = self._sem.acquire(timeout=max(0.0, float(timeout_s)))
        if not ok:
            raise TimeoutError(f"{self.name} 并发配额获取超时")
        try:
            yield
        finally:
            try:
                self._sem.release()
            except Exception:
                pass


class RateLimiter:
    """最小间隔限速（进程内全局）。"""

    def __init__(self, name: str, min_interval_s: float):
        self.name = str(name)
        self.min_interval_s = max(0.0, float(min_interval_s))
        self._lock = threading.Lock()
        self._last_at = 0.0

    def sleep_if_needed(self):
        if self.min_interval_s <= 0:
            return
        with self._lock:
            now = time.monotonic()
            delta = now - self._last_at
            if delta < self.min_interval_s:
                sleep_s = self.min_interval_s - delta
                # 加少量抖动，避免多线程同步撞击上游
                sleep_s += random.uniform(0.0, min(0.05, self.min_interval_s * 0.2))
                time.sleep(max(0.0, sleep_s))
            self._last_at = time.monotonic()


def _deadline_timeout_s(deadline_monotonic: float | None) -> Optional[float]:
    if deadline_monotonic is None:
        return None
    try:
        remaining = float(deadline_monotonic) - time.monotonic()
    except Exception:
        return None
    return max(0.0, remaining)


# =========================
# 预置的全局限流器（按类别）
# =========================

TEXT_MAX_CONCURRENT = _env_int("LLM_TEXT_MAX_CONCURRENT", 4, min_value=1)
IMAGE_MAX_CONCURRENT = _env_int("LLM_IMAGE_MAX_CONCURRENT", 4, min_value=1)
GATE_MAX_CONCURRENT = _env_int("GATE_MAX_CONCURRENT", 4, min_value=1)

IMAGE_MIN_INTERVAL_S = _env_float("LLM_IMAGE_MIN_INTERVAL_S", 0.2, min_value=0.0)
GATE_MIN_INTERVAL_S = _env_float("GATE_MIN_INTERVAL_S", 0.0, min_value=0.0)

text_limiter = ConcurrencyLimiter("llm_text", TEXT_MAX_CONCURRENT)
image_limiter = ConcurrencyLimiter("llm_image", IMAGE_MAX_CONCURRENT)
gate_limiter = ConcurrencyLimiter("gate", GATE_MAX_CONCURRENT)

image_rate_limiter = RateLimiter("llm_image_rate", IMAGE_MIN_INTERVAL_S)
gate_rate_limiter = RateLimiter("gate_rate", GATE_MIN_INTERVAL_S)


@contextmanager
def limit_text(deadline_monotonic: float | None = None) -> Iterator[None]:
    with text_limiter.acquire(timeout_s=_deadline_timeout_s(deadline_monotonic)):
        yield


@contextmanager
def limit_image(deadline_monotonic: float | None = None) -> Iterator[None]:
    image_rate_limiter.sleep_if_needed()
    with image_limiter.acquire(timeout_s=_deadline_timeout_s(deadline_monotonic)):
        yield


@contextmanager
def limit_gate(deadline_monotonic: float | None = None) -> Iterator[None]:
    gate_rate_limiter.sleep_if_needed()
    with gate_limiter.acquire(timeout_s=_deadline_timeout_s(deadline_monotonic)):
        yield
