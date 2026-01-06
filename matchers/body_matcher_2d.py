#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2D素材身体匹配器类
专门处理2D身体姿势分析和匹配，根据视角和动作类型选择不同的检索路径
"""

import os
import glob
import random
import logging
from typing import Dict, List, Optional, Callable

from PIL import Image
from sentence_transformers import util

from matchers.body_matcher import BodyMatcher
from utils.clip_manager import get_clip_model, get_clip_tokenizer

logger = logging.getLogger(__name__)


class BodyMatcher2D(BodyMatcher):
    """2D素材的身体姿势匹配器"""
    
    # 视角到基础路径的映射
    PERSPECTIVE_BASE_PATHS = {
        "正视角": "data/2d/frontview",
        "仰视角": "data/2d/upview"
    }
    
    # 动作类型到文件夹名的映射
    ACTION_FOLDER_MAP = {
        "站姿": "body_stand",
        "欢快": "body_happy",
        "坐姿": "body_sit",
        "跳跃": "body_jump",
        "跑动": "body_run"
    }
    
    def __init__(self):
        """初始化2D身体匹配器"""
        super().__init__()
        self._clip_model_ref = None
        logger.info("BodyMatcher2D 初始化完成")
    
    def _ensure_clip_model(self):
        """获取全局共享的 CLIP 模型"""
        if self._clip_model_ref is None:
            self._clip_model_ref = get_clip_model()
    
    def _truncate_clip_text(self, text: str) -> str:
        """将文本安全截断到 CLIP 支持的最大 token 长度"""
        try:
            tokenizer = get_clip_tokenizer()
            if tokenizer is None:
                return text
            max_len = 77
            encoded = tokenizer(text, truncation=True, max_length=max_len, return_tensors=None)
            ids = encoded.get('input_ids')
            if isinstance(ids, list) and len(ids) > 0:
                first = ids[0] if isinstance(ids[0], list) else ids
                truncated_text = tokenizer.decode(first, skip_special_tokens=True)
                return truncated_text.strip()
            return text
        except Exception:
            return text
    
    def get_body_folder_path(self, perspective: str = "正视角", action_type: str = "站姿") -> str:
        """
        根据视角和动作类型获取身体检索路径
        
        Args:
            perspective: 视角（正视角/仰视角）
            action_type: 动作类型（站姿/欢快/坐姿/跳跃/跑动）
            
        Returns:
            str: 身体文件夹路径
        """
        base_path = self.PERSPECTIVE_BASE_PATHS.get(perspective, self.PERSPECTIVE_BASE_PATHS["正视角"])
        folder_name = self.ACTION_FOLDER_MAP.get(action_type, "body_stand")
        path = os.path.join(base_path, folder_name)
        logger.info(f"2D身体检索路径: {path} (视角: {perspective}, 动作: {action_type})")
        return path
    
    def find_best_matches_from_folder_2d(self, requirement: str, folder_path: str,
                                          top_k: int = 2, log_callback: Optional[Callable[[str], None]] = None) -> tuple:
        """
        从指定文件夹中使用CLIP进行身体图片匹配
        
        Args:
            requirement: 用户需求描述
            folder_path: 检索的文件夹路径
            top_k: 返回top_k个最佳匹配
            log_callback: 日志回调函数
            
        Returns:
            tuple: (匹配结果列表, 处理日志列表)
        """
        processing_logs = []
        
        # 获取文件夹中的所有图片文件
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif']
        all_images = []
        
        for extension in image_extensions:
            all_images.extend(glob.glob(os.path.join(folder_path, extension)))
        
        if not all_images:
            log_msg = f"警告：在文件夹 {folder_path} 中没有找到图片文件"
            logger.warning(log_msg)
            processing_logs.append(log_msg)
            if log_callback:
                log_callback(log_msg)
            return [], processing_logs
        
        log_msg = f"开始2D身体CLIP检索，路径: {folder_path}，图片数: {len(all_images)}"
        logger.info(log_msg)
        processing_logs.append(log_msg)
        if log_callback:
            log_callback(log_msg)
        
        # 懒加载 CLIP 模型
        self._ensure_clip_model()
        
        # 动作特征提取
        requirement_features = self.analyze_user_requirement(requirement)
        action_text = requirement_features.get('整体姿势', '') or requirement
        
        # 文本嵌入
        try:
            action_text_safe = self._truncate_clip_text(action_text)
            text_emb = self._clip_model_ref.encode([action_text_safe], convert_to_tensor=True, normalize_embeddings=True)
        except Exception as e:
            err = f"文本向量化失败: {str(e)}"
            logger.error(err)
            processing_logs.append(err)
            if log_callback:
                log_callback(err)
            return [], processing_logs
        
        # 图片检索评分
        scores = []
        for img_path in all_images:
            img_name = os.path.basename(img_path)
            try:
                image = Image.open(img_path).convert('RGB')
                img_emb = self._clip_model_ref.encode([image], convert_to_tensor=True, normalize_embeddings=True)
                sim = util.cos_sim(img_emb, text_emb)[0][0].item()
                total_score = float(sim)
            except Exception as e:
                total_score = 0.0
                err = f"图片向量化失败 {img_name}: {str(e)}"
                logger.error(err)
                processing_logs.append(err)
                if log_callback:
                    log_callback(err)
            
            scores.append({
                "image_name": img_name,
                "image_path": img_path,
                "score": total_score,
                "dimension_scores": {dim: total_score for dim in self.dimensions},
                "features": {dim: "CLIP相似度" for dim in self.dimensions},
                "requirement_features": requirement_features,
                "type": "body"
            })
            
            log_msg = f"身体图片 {img_name} 相似度: {total_score:.4f}"
            logger.info(log_msg)
            processing_logs.append(log_msg)
            if log_callback:
                log_callback(log_msg)
        
        # 按得分排序并去重
        scores.sort(key=lambda x: x['score'], reverse=True)
        unique = []
        seen = set()
        for item in scores:
            p = item.get('image_path')
            if p and p not in seen:
                unique.append(item)
                seen.add(p)
            if len(unique) >= top_k:
                break
        
        names = [u.get('image_name') for u in unique]
        processing_logs.append(f"身体匹配完成，选择前{top_k}个最佳匹配: {names}")
        if log_callback:
            log_callback(f"身体匹配完成，选择前{top_k}个最佳匹配: {names}")
        
        return unique, processing_logs
    
    def find_best_matches_2d(self, requirement: str, perspective: str = "正视角",
                              top_k: int = 2, log_callback: Optional[Callable[[str], None]] = None) -> tuple:
        """
        根据视角和动作类型进行身体匹配
        
        Args:
            requirement: 用户需求描述
            perspective: 视角（正视角/仰视角）
            top_k: 返回top_k个最佳匹配
            log_callback: 日志回调函数
            
        Returns:
            tuple: (匹配结果列表, 处理日志列表)
        """
        # 先分析动作类型
        action_type = self.classify_action_type(requirement)
        logger.info(f"识别到动作类型: {action_type}")
        
        # 获取对应的文件夹路径
        folder_path = self.get_body_folder_path(perspective, action_type)
        
        # 检查路径是否存在
        if not os.path.exists(folder_path):
            log_msg = f"警告：身体路径不存在: {folder_path}"
            logger.warning(log_msg)
            if log_callback:
                log_callback(log_msg)
            return [], [log_msg]
        
        # 使用CLIP进行匹配
        return self.find_best_matches_from_folder_2d(
            requirement, folder_path, top_k=top_k, log_callback=log_callback
        )
    
    def find_one_best_match_2d(self, requirement: str, perspective: str = "正视角",
                                top_k: int = 5, log_callback: Optional[Callable[[str], None]] = None) -> tuple:
        """
        从匹配结果中随机选择一张返回
        
        Args:
            requirement: 用户需求描述
            perspective: 视角（正视角/仰视角）
            top_k: 候选数量
            log_callback: 日志回调函数
            
        Returns:
            tuple: (匹配结果列表（只包含1个）, 处理日志列表)
        """
        top_results, logs = self.find_best_matches_2d(requirement, perspective, top_k=top_k, log_callback=log_callback)
        if not top_results:
            return [], logs
        
        chosen = random.choice(top_results)
        choose_log = f"从前{top_k}名中随机抽取的图片: {chosen.get('image_name')}"
        logger.info(choose_log)
        logs.append(choose_log)
        if log_callback:
            log_callback(choose_log)
        
        return [chosen], logs


if __name__ == "__main__":
    # 测试代码
    matcher = BodyMatcher2D()
    
    # 测试不同视角和动作的路径
    for perspective in ["正视角", "仰视角"]:
        for action in ["站姿", "跳跃", "跑动"]:
            path = matcher.get_body_folder_path(perspective, action)
            exists = os.path.exists(path)
            logger.info(f"视角: {perspective}, 动作: {action}, 路径: {path}, 存在: {exists}")
    
    # 测试匹配（如果路径存在）
    test_requirement = "开心的跳跃动作"
    for perspective in ["正视角", "仰视角"]:
        results, logs = matcher.find_best_matches_2d(test_requirement, perspective, top_k=2)
        logger.info(f"视角: {perspective}, 匹配结果数: {len(results)}")
