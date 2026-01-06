#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纯 CLIP 表情检索测试 - 不调用 ContentAgent 的 AI
直接使用表情关键词进行 CLIP 检索
"""

import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image
from sentence_transformers import SentenceTransformer, util


class SimpleClipMatcher:
    """简化的 CLIP 匹配器"""
    
    def __init__(self):
        self.clip_model = None
    
    def _ensure_clip_model(self):
        if self.clip_model is None:
            print("加载 CLIP 模型...")
            self.clip_model = SentenceTransformer('clip-ViT-B-32')
            print("CLIP 模型加载完成")
    
    def search_by_expression(self, expression_text: str, folder_path: str, top_k: int = 5):
        """使用表情文本直接进行 CLIP 检索"""
        self._ensure_clip_model()
        
        # 获取文件夹中的所有图片
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif']
        all_images = []
        for ext in image_extensions:
            all_images.extend(glob.glob(os.path.join(folder_path, ext)))
        
        if not all_images:
            print(f"警告: 文件夹 {folder_path} 中没有图片")
            return []
        
        # 文本嵌入
        text_emb = self.clip_model.encode([expression_text], convert_to_tensor=True, normalize_embeddings=True)
        
        # 图片检索评分
        scores = []
        for img_path in all_images:
            img_name = os.path.basename(img_path)
            try:
                image = Image.open(img_path).convert('RGB')
                img_emb = self.clip_model.encode([image], convert_to_tensor=True, normalize_embeddings=True)
                sim = util.cos_sim(img_emb, text_emb)[0][0].item()
                scores.append({
                    "image_name": img_name,
                    "image_path": img_path,
                    "score": float(sim)
                })
            except Exception as e:
                print(f"图片处理失败 {img_name}: {e}")
        
        # 排序
        scores.sort(key=lambda x: x['score'], reverse=True)
        return scores[:top_k]


def test_expressions(expressions: list, folder_path: str = "data/face_front_per", top_k: int = 5):
    """测试不同表情关键词的 CLIP 检索结果"""
    
    matcher = SimpleClipMatcher()
    
    print("=" * 80)
    print("纯 CLIP 表情检索测试")
    print(f"测试文件夹: {folder_path}")
    print(f"返回数量: {top_k}")
    print("=" * 80)
    
    for expr in expressions:
        print(f"\n{'='*60}")
        print(f"表情关键词: {expr}")
        print("-" * 60)
        
        results = matcher.search_by_expression(expr, folder_path, top_k)
        
        print(f"筛选结果 (共 {len(results)} 张):")
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r['image_name']} - 相似度: {r['score']:.4f}")
        
        print("-" * 60)


if __name__ == "__main__":
    # 默认测试的表情关键词
    test_expressions_list = [
        "开心",
        "微笑", 
        "大笑",
        "愤怒",
        "悲伤",
        "惊讶",
        "害羞",
        "冷漠",
    ]
    
    # 命令行参数
    if len(sys.argv) > 1:
        test_expressions_list = sys.argv[1:]
    
    folder = "data/face_front_per"
    if not os.path.exists(folder):
        print(f"错误: 文件夹 {folder} 不存在")
        sys.exit(1)
    
    test_expressions(test_expressions_list, folder_path=folder, top_k=5)
