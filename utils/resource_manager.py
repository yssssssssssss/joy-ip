#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共享资源管理器
管理全局共享的matcher、processor等实例（线程安全）
"""

import threading
import logging

logger = logging.getLogger(__name__)


class ResourceManager:
    """共享资源管理器（线程安全单例）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._resources = {}
        self._resource_lock = threading.Lock()

        logger.info("ResourceManager 初始化完成")

    def get_head_matcher(self):
        """获取头像匹配器（懒加载）"""
        return self._get_or_create('head_matcher', self._create_head_matcher)

    def get_body_matcher(self):
        """获取身体匹配器（懒加载）"""
        return self._get_or_create('body_matcher', self._create_body_matcher)

    def get_content_agent(self):
        """获取内容代理（懒加载）"""
        return self._get_or_create('content_agent', self._create_content_agent)

    def get_generation_controller(self):
        """获取生成控制器（懒加载）"""
        return self._get_or_create('generation_controller', self._create_generation_controller)

    def get_image_processor(self):
        """获取图片处理器（懒加载）"""
        return self._get_or_create('image_processor', self._create_image_processor)

    def _get_or_create(self, key: str, factory):
        """获取或创建资源"""
        if key not in self._resources:
            with self._resource_lock:
                if key not in self._resources:
                    logger.debug(f"创建共享资源: {key}")
                    self._resources[key] = factory()
        return self._resources[key]

    def _create_head_matcher(self):
        from matchers.head_matcher import HeadMatcher
        return HeadMatcher()

    def _create_body_matcher(self):
        from matchers.body_matcher import BodyMatcher
        return BodyMatcher()

    def _create_content_agent(self):
        from content_agent import ContentAgent
        return ContentAgent()

    def _create_generation_controller(self):
        from generation_controller import GenerationController
        return GenerationController()

    def _create_image_processor(self):
        from image_processor import ImageProcessor
        return ImageProcessor()

    def clear(self):
        """清除所有缓存的资源"""
        with self._resource_lock:
            self._resources.clear()
            logger.info("已清除所有共享资源")


# 全局资源管理器实例
resources = ResourceManager()
