#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLIP 嵌入向量缓存管理器
预计算并缓存图片的 CLIP 嵌入向量，加速检索
"""

import os
import glob
import pickle
import hashlib
import logging
import threading
from typing import List, Tuple, Dict, Optional
from pathlib import Path

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# 全局缓存实例
_GLOBAL_CACHE = None
_CACHE_LOCK = threading.Lock()


class CLIPEmbeddingCache:
    """CLIP 嵌入向量缓存"""
    
    def __init__(self, cache_dir: str = "cache/clip_embeddings"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: Dict[str, Tuple[List[str], np.ndarray]] = {}
        self._clip_model = None
        logger.info(f"CLIPEmbeddingCache 初始化，缓存目录: {self.cache_dir}")
    
    def _get_clip_model(self):
        """获取 CLIP 模型（懒加载）"""
        if self._clip_model is None:
            from utils.clip_manager import get_clip_model
            self._clip_model = get_clip_model()
        return self._clip_model
    
    def _get_folder_hash(self, folder_path: str) -> str:
        """生成文件夹内容的哈希值（基于文件列表和修改时间）"""
        image_files = self._get_image_files(folder_path)
        if not image_files:
            return ""
        
        # 基于文件名和修改时间生成哈希
        content = []
        for f in sorted(image_files):
            try:
                mtime = os.path.getmtime(f)
                content.append(f"{f}:{mtime}")
            except:
                content.append(f)
        
        return hashlib.md5("|".join(content).encode()).hexdigest()[:16]
    
    def _get_cache_path(self, folder_path: str) -> Path:
        """获取缓存文件路径"""
        # 使用文件夹路径的哈希作为缓存文件名
        folder_hash = hashlib.md5(folder_path.encode()).hexdigest()[:16]
        return self.cache_dir / f"{folder_hash}.pkl"
    
    def _get_image_files(self, folder_path: str) -> List[str]:
        """获取文件夹中的所有图片文件"""
        extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif']
        all_images = []
        for ext in extensions:
            all_images.extend(glob.glob(os.path.join(folder_path, ext)))
        return sorted(all_images)
    
    def has_cache(self, folder_path: str) -> bool:
        """检查是否存在有效缓存"""
        # 检查内存缓存
        if folder_path in self._memory_cache:
            return True
        
        # 检查磁盘缓存
        cache_path = self._get_cache_path(folder_path)
        if not cache_path.exists():
            return False
        
        # 验证缓存是否过期
        try:
            with open(cache_path, 'rb') as f:
                cached = pickle.load(f)
            stored_hash = cached.get('folder_hash', '')
            current_hash = self._get_folder_hash(folder_path)
            return stored_hash == current_hash
        except Exception:
            return False
    
    def build_cache(self, folder_path: str, force: bool = False) -> bool:
        """
        预计算并保存图片嵌入
        
        Args:
            folder_path: 图片文件夹路径
            force: 是否强制重建缓存
            
        Returns:
            bool: 是否成功
        """
        if not force and self.has_cache(folder_path):
            logger.info(f"缓存已存在，跳过: {folder_path}")
            return True
        
        image_files = self._get_image_files(folder_path)
        if not image_files:
            logger.warning(f"文件夹中无图片: {folder_path}")
            return False
        
        logger.info(f"开始构建 CLIP 缓存: {folder_path} ({len(image_files)} 张图片)")
        
        model = self._get_clip_model()
        embeddings = []
        valid_files = []
        
        for img_path in image_files:
            try:
                image = Image.open(img_path).convert('RGB')
                emb = model.encode([image], convert_to_tensor=False, normalize_embeddings=True)
                embeddings.append(emb[0])
                valid_files.append(img_path)
            except Exception as e:
                logger.warning(f"处理图片失败 {img_path}: {e}")
        
        if not embeddings:
            logger.error(f"无有效嵌入: {folder_path}")
            return False
        
        embeddings_array = np.array(embeddings)
        
        # 保存到磁盘
        cache_data = {
            'folder_path': folder_path,
            'folder_hash': self._get_folder_hash(folder_path),
            'image_files': valid_files,
            'embeddings': embeddings_array
        }
        
        cache_path = self._get_cache_path(folder_path)
        with open(cache_path, 'wb') as f:
            pickle.dump(cache_data, f)
        
        # 保存到内存
        self._memory_cache[folder_path] = (valid_files, embeddings_array)
        
        logger.info(f"✅ 缓存构建完成: {folder_path} ({len(valid_files)} 张)")
        return True
    
    def get_embeddings(self, folder_path: str) -> Tuple[List[str], Optional[np.ndarray]]:
        """
        获取缓存的嵌入向量
        
        Returns:
            Tuple[文件路径列表, 嵌入矩阵] 或 ([], None)
        """
        # 优先从内存获取
        if folder_path in self._memory_cache:
            return self._memory_cache[folder_path]
        
        # 从磁盘加载
        cache_path = self._get_cache_path(folder_path)
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    cached = pickle.load(f)
                
                # 验证哈希
                if cached.get('folder_hash') == self._get_folder_hash(folder_path):
                    files = cached['image_files']
                    embeddings = cached['embeddings']
                    self._memory_cache[folder_path] = (files, embeddings)
                    logger.info(f"从缓存加载: {folder_path} ({len(files)} 张)")
                    return files, embeddings
            except Exception as e:
                logger.warning(f"加载缓存失败: {e}")
        
        return [], None
    
    def search(self, text_embedding: np.ndarray, folder_path: str, 
               top_k: int = 5) -> List[Dict]:
        """
        基于文本嵌入搜索最相似图片
        
        Args:
            text_embedding: 文本嵌入向量 (1, D)
            folder_path: 图片文件夹路径
            top_k: 返回前 k 个结果
            
        Returns:
            List[Dict]: 匹配结果列表
        """
        files, embeddings = self.get_embeddings(folder_path)
        
        if embeddings is None:
            # 无缓存，尝试构建
            if self.build_cache(folder_path):
                files, embeddings = self.get_embeddings(folder_path)
            
            if embeddings is None:
                return []
        
        # 计算余弦相似度
        if len(text_embedding.shape) == 1:
            text_embedding = text_embedding.reshape(1, -1)
        
        # 归一化
        text_norm = text_embedding / (np.linalg.norm(text_embedding, axis=1, keepdims=True) + 1e-8)
        emb_norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)
        
        # 计算相似度
        similarities = np.dot(emb_norm, text_norm.T).flatten()
        
        # 获取 top_k
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append({
                'image_path': files[idx],
                'image_name': os.path.basename(files[idx]),
                'score': float(similarities[idx]),
                'type': 'cached'
            })
        
        return results


def get_clip_cache() -> CLIPEmbeddingCache:
    """获取全局缓存实例（单例）"""
    global _GLOBAL_CACHE
    
    if _GLOBAL_CACHE is None:
        with _CACHE_LOCK:
            if _GLOBAL_CACHE is None:
                _GLOBAL_CACHE = CLIPEmbeddingCache()
    
    return _GLOBAL_CACHE


def prebuild_2d_cache():
    """预构建所有 2D 素材的缓存"""
    cache = get_clip_cache()
    
    # 2D 素材目录列表
    folders = [
        "data/2d/frontview/head",
        "data/2d/upview/head",
    ]
    
    # 添加 body 文件夹
    for perspective in ["frontview", "upview"]:
        base = f"data/2d/{perspective}"
        if os.path.exists(base):
            for folder in os.listdir(base):
                if folder.startswith("body_"):
                    folders.append(os.path.join(base, folder))
    
    logger.info(f"开始预构建 {len(folders)} 个文件夹的缓存...")
    
    for folder in folders:
        if os.path.exists(folder):
            cache.build_cache(folder)
    
    logger.info("✅ 2D 素材缓存预构建完成")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    prebuild_2d_cache()
