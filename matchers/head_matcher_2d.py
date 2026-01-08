#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2D素材头像匹配器类
专门处理2D头像表情分析和匹配，根据视角选择不同的检索路径
"""

import os
import logging
from typing import Dict, List, Optional, Callable

from matchers.head_matcher import HeadMatcher

logger = logging.getLogger(__name__)


class HeadMatcher2D(HeadMatcher):
    """2D素材的头像匹配器"""
    
    # 视角到路径的映射
    PERSPECTIVE_PATHS = {
        "正视角": "data/2d/frontview/head",
        "仰视角": "data/2d/upview/head"
    }
    
    def __init__(self):
        """初始化2D头像匹配器"""
        super().__init__()
        logger.info("HeadMatcher2D 初始化完成")
    
    def get_head_folder_path(self, perspective: str = "正视角") -> str:
        """
        根据视角获取头像检索路径
        
        Args:
            perspective: 视角（正视角/仰视角）
            
        Returns:
            str: 头像文件夹路径
        """
        path = self.PERSPECTIVE_PATHS.get(perspective, self.PERSPECTIVE_PATHS["正视角"])
        logger.info(f"2D头像检索路径: {path} (视角: {perspective})")
        return path
    
    def find_best_matches_2d(self, requirement: str, perspective: str = "正视角",
                              top_k: int = 2, log_callback: Optional[Callable[[str], None]] = None) -> tuple:
        """
        根据视角选择对应路径进行头像匹配（优先使用缓存）
        
        Args:
            requirement: 用户需求描述
            perspective: 视角（正视角/仰视角）
            top_k: 返回top_k个最佳匹配
            log_callback: 日志回调函数
            
        Returns:
            tuple: (匹配结果列表, 处理日志列表)
        """
        processing_logs = []
        folder_path = self.get_head_folder_path(perspective)
        
        # 检查路径是否存在
        if not os.path.exists(folder_path):
            log_msg = f"警告：头像路径不存在: {folder_path}"
            logger.warning(log_msg)
            processing_logs.append(log_msg)
            if log_callback:
                log_callback(log_msg)
            return [], processing_logs
        
        logger.info(f"开始2D头像匹配，视角: {perspective}，路径: {folder_path}")
        
        # 尝试使用 CLIP 缓存
        try:
            from utils.clip_cache import get_clip_cache
            cache = get_clip_cache()
            
            if cache.has_cache(folder_path):
                log_msg = f"使用 CLIP 缓存进行头像检索: {folder_path}"
                logger.info(log_msg)
                processing_logs.append(log_msg)
                if log_callback:
                    log_callback(log_msg)
                
                # 获取文本嵌入
                self._ensure_clip_model()
                expr_text = self._extract_expression_text(requirement)
                expr_text_safe = self._truncate_clip_text(expr_text)
                text_emb = self._clip_model_ref.encode([expr_text_safe], convert_to_tensor=False, normalize_embeddings=True)
                
                # 使用缓存搜索
                results = cache.search(text_emb[0], folder_path, top_k=top_k)
                
                if results:
                    # 补充完整信息
                    requirement_features = self.analyze_user_requirement(requirement)
                    for r in results:
                        r['requirement_features'] = requirement_features
                        r['dimension_scores'] = {dim: r['score'] for dim in self.dimensions}
                        r['features'] = {dim: "CLIP缓存" for dim in self.dimensions}
                        r['type'] = 'head'
                    
                    names = [r.get('image_name') for r in results]
                    processing_logs.append(f"头像缓存匹配完成，选择前{top_k}个: {names}")
                    if log_callback:
                        log_callback(f"头像缓存匹配完成，选择前{top_k}个: {names}")
                    
                    return results, processing_logs
        except Exception as e:
            logger.warning(f"CLIP 缓存不可用，回退到原有逻辑: {e}")
            processing_logs.append(f"CLIP 缓存不可用: {e}")
        
        # 回退到原有逻辑
        return self.find_best_matches_from_folder(
            requirement, folder_path, top_k=top_k, log_callback=log_callback
        )
    
    def find_one_best_match_2d(self, requirement: str, perspective: str = "正视角",
                                top_k: int = 5, num_select: int = 2,
                                log_callback: Optional[Callable[[str], None]] = None) -> tuple:
        """
        从文件夹中找到前top_k排序，并从中随机抽取num_select张返回
        
        Args:
            requirement: 用户需求描述
            perspective: 视角（正视角/仰视角）
            top_k: 候选数量
            num_select: 随机选择的数量（默认2张）
            log_callback: 日志回调函数
            
        Returns:
            tuple: (匹配结果列表（包含num_select个）, 处理日志列表)
        """
        import random
        
        folder_path = self.get_head_folder_path(perspective)
        
        # 检查路径是否存在
        if not os.path.exists(folder_path):
            log_msg = f"警告：头像路径不存在: {folder_path}"
            logger.warning(log_msg)
            if log_callback:
                log_callback(log_msg)
            return [], [log_msg]
        
        # 获取 top_k 个候选
        top_results, logs = self.find_best_matches_from_folder(
            requirement, folder_path, top_k=top_k, log_callback=log_callback
        )
        
        if not top_results:
            return [], logs
        
        # 从 top_k 中随机选择 num_select 个
        actual_select = min(num_select, len(top_results))
        chosen = random.sample(top_results, actual_select)
        
        chosen_names = [c.get('image_name') for c in chosen]
        choose_log = f"从前{top_k}名中随机抽取{actual_select}张图片: {chosen_names}"
        logger.info(choose_log)
        logs.append(choose_log)
        if log_callback:
            log_callback(choose_log)
        
        return chosen, logs


if __name__ == "__main__":
    # 测试代码
    matcher = HeadMatcher2D()
    
    # 测试不同视角的路径
    for perspective in ["正视角", "仰视角"]:
        path = matcher.get_head_folder_path(perspective)
        exists = os.path.exists(path)
        logger.info(f"视角: {perspective}, 路径: {path}, 存在: {exists}")
    
    # 测试匹配（如果路径存在）
    test_requirement = "开心的表情"
    for perspective in ["正视角", "仰视角"]:
        path = matcher.get_head_folder_path(perspective)
        if os.path.exists(path):
            results, logs = matcher.find_best_matches_2d(test_requirement, perspective, top_k=2)
            logger.info(f"视角: {perspective}, 匹配结果数: {len(results)}")
