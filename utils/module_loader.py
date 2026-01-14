#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一模块加载器
用于加载不符合Python命名规范的模块文件
"""

import os
import sys
import importlib.util
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class ModuleLoader:
    """模块加载器"""

    _cache = {}  # 模块缓存

    @classmethod
    def load(
        cls,
        file_name: str,
        module_name: Optional[str] = None,
        base_dir: Optional[str] = None
    ) -> Optional[Any]:
        """
        加载Python模块文件

        Args:
            file_name: 文件名（如 'banana-clothes.py'）
            module_name: 模块名（默认从文件名生成）
            base_dir: 基础目录（默认为项目根目录）

        Returns:
            加载的模块对象，失败返回None
        """
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        if module_name is None:
            # 将文件名转换为有效的模块名
            module_name = file_name.replace('.py', '').replace('-', '_')

        # 检查缓存
        cache_key = f"{base_dir}/{file_name}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        module_path = os.path.join(base_dir, file_name)

        if not os.path.exists(module_path):
            logger.warning(f"模块文件不存在: {module_path}")
            return None

        try:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                logger.error(f"无法创建模块规范: {module_path}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # 缓存模块
            cls._cache[cache_key] = module
            logger.debug(f"成功加载模块: {file_name} -> {module_name}")

            return module

        except Exception as e:
            logger.error(f"加载模块失败 {file_name}: {str(e)}")
            return None

    @classmethod
    def get_function(
        cls,
        file_name: str,
        function_name: str,
        base_dir: Optional[str] = None
    ) -> Optional[callable]:
        """
        从模块中获取指定函数

        Args:
            file_name: 文件名
            function_name: 函数名
            base_dir: 基础目录

        Returns:
            函数对象，失败返回None
        """
        module = cls.load(file_name, base_dir=base_dir)
        if module is None:
            return None

        func = getattr(module, function_name, None)
        if func is None:
            logger.warning(f"模块 {file_name} 中未找到函数 {function_name}")

        return func

    @classmethod
    def clear_cache(cls):
        """清除模块缓存"""
        cls._cache.clear()
        logger.debug("模块缓存已清除")
