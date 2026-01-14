#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析结果缓存模块
用于缓存AI分析结果，避免重复调用
"""

import hashlib
import json
import os
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AnalysisCache:
    """分析结果缓存"""
    
    def __init__(self, cache_dir: str = "cache/analysis", ttl_hours: int = 24):
        """
        初始化缓存
        
        Args:
            cache_dir: 缓存目录
            ttl_hours: 缓存有效期（小时）
        """
        self.cache_dir = cache_dir
        self.ttl = timedelta(hours=ttl_hours)
        self._ensure_cache_dir()
        
        # 内存缓存（加速访问）
        self._memory_cache: Dict[str, Dict] = {}
        self._memory_cache_max_size = 100
    
    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except Exception as e:
            logger.warning(f"创建缓存目录失败: {e}")
    
    def _get_cache_key(self, requirement: str) -> str:
        """
        生成缓存键
        使用MD5哈希确保键的唯一性和固定长度
        """
        # 规范化输入（去除首尾空格，统一为小写）
        normalized = requirement.strip()
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def _get_cache_path(self, key: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{key}.json")
    
    def get(self, requirement: str) -> Optional[Dict]:
        """
        获取缓存
        
        Args:
            requirement: 用户需求文本
            
        Returns:
            缓存的分析结果，如果不存在或已过期则返回None
        """
        key = self._get_cache_key(requirement)
        
        # 1. 先检查内存缓存
        if key in self._memory_cache:
            data = self._memory_cache[key]
            cached_time = datetime.fromisoformat(data['timestamp'])
            if datetime.now() - cached_time <= self.ttl:
                logger.info(f"[缓存] 内存缓存命中: {key[:8]}...")
                return data['analysis']
            else:
                # 过期，删除内存缓存
                del self._memory_cache[key]
        
        # 2. 检查文件缓存
        path = self._get_cache_path(key)
        
        if not os.path.exists(path):
            return None
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查是否过期
            cached_time = datetime.fromisoformat(data['timestamp'])
            if datetime.now() - cached_time > self.ttl:
                logger.info(f"[缓存] 文件缓存已过期: {key[:8]}...")
                os.remove(path)
                return None
            
            # 加载到内存缓存
            self._add_to_memory_cache(key, data)
            
            logger.info(f"[缓存] 文件缓存命中: {key[:8]}...")
            return data['analysis']
            
        except Exception as e:
            logger.warning(f"[缓存] 读取缓存失败: {e}")
            return None
    
    def set(self, requirement: str, analysis: Dict):
        """
        设置缓存
        
        Args:
            requirement: 用户需求文本
            analysis: 分析结果
        """
        key = self._get_cache_key(requirement)
        path = self._get_cache_path(key)
        
        data = {
            'requirement': requirement,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        }
        
        # 1. 保存到内存缓存
        self._add_to_memory_cache(key, data)
        
        # 2. 保存到文件缓存
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"[缓存] 已缓存分析结果: {key[:8]}...")
        except Exception as e:
            logger.warning(f"[缓存] 保存缓存失败: {e}")
    
    def _add_to_memory_cache(self, key: str, data: Dict):
        """添加到内存缓存（带LRU淘汰）"""
        # 如果超过最大容量，删除最旧的条目
        if len(self._memory_cache) >= self._memory_cache_max_size:
            oldest_key = next(iter(self._memory_cache))
            del self._memory_cache[oldest_key]
        
        self._memory_cache[key] = data
    
    def clear(self):
        """清空所有缓存"""
        # 清空内存缓存
        self._memory_cache.clear()
        
        # 清空文件缓存
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, filename))
            logger.info("[缓存] 已清空所有缓存")
        except Exception as e:
            logger.warning(f"[缓存] 清空缓存失败: {e}")
    
    def get_stats(self) -> Dict:
        """获取缓存统计信息"""
        memory_count = len(self._memory_cache)
        
        file_count = 0
        try:
            file_count = len([f for f in os.listdir(self.cache_dir) if f.endswith('.json')])
        except Exception:
            pass
        
        return {
            'memory_cache_count': memory_count,
            'file_cache_count': file_count,
            'cache_dir': self.cache_dir,
            'ttl_hours': self.ttl.total_seconds() / 3600
        }


# 全局缓存实例
analysis_cache = AnalysisCache()


# 便捷函数
def get_cached_analysis(requirement: str) -> Optional[Dict]:
    """获取缓存的分析结果"""
    return analysis_cache.get(requirement)


def cache_analysis(requirement: str, analysis: Dict):
    """缓存分析结果"""
    analysis_cache.set(requirement, analysis)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    cache = AnalysisCache()
    
    # 测试设置和获取
    test_req = "测试需求：穿红色衣服"
    test_analysis = {'上装': '红色衣服', '下装': '蓝色裤子'}
    
    cache.set(test_req, test_analysis)
    result = cache.get(test_req)
    
    print(f"缓存结果: {result}")
    print(f"缓存统计: {cache.get_stats()}")
