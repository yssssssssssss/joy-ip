#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志配置模块
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logger(
    name: Optional[str] = None,
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    配置并返回logger实例

    Args:
        name: logger名称，None表示root logger
        level: 日志级别
        log_file: 日志文件路径
        max_bytes: 单个日志文件最大大小
        backup_count: 保留的日志文件数量

    Returns:
        logging.Logger: 配置好的logger实例
    """
    logger = logging.getLogger(name)

    # 避免重复配置
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 统一日志格式
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器（如果指定了日志文件）
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的logger

    Args:
        name: logger名称（通常使用 __name__）

    Returns:
        logging.Logger: logger实例
    """
    return logging.getLogger(name)


def init_app_logger():
    """初始化应用级别的logger"""
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    log_file = os.environ.get('LOG_FILE')

    setup_logger(
        name=None,  # root logger
        level=log_level,
        log_file=log_file
    )

    # 屏蔽一些第三方库的冗余日志
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
