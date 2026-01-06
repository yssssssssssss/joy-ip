#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用英文关键词测试 CLIP 表情检索
"""

import os
import glob
from PIL import Image
from sentence_transformers import SentenceTransformer, util

def test_clip_english():
    folder_path = "data/face_front_per"
    top_k = 5
    
    # 英文表情关键词
    expressions = [
        "happy smiling face",
        "laughing face",
        "angry face",
        "sad face",
        "surprised face",
        "shy face",
        "neutral face",
        "crying face",
        "excited face",
    ]
    
    print("=" * 80)
    print("英文 CLIP 表情检索测试")
    print(f"测试文件夹: {folder_path}")
    print(f"返回数量: {top_k}")
    print("=" * 80)
    
    # 获取所有图片
    image_extensions = ['*.png', '*.jpg', '*.jpeg']
    all_images = []
    for ext in image_extensions:
        all_images.extend(glob.glob(os.path.join(folder_path, ext)))
    
    if not all_images:
        print(f"错误：文件夹 {folder_path} 中没有图片")
        return
    
    print(f"\n找到 {len(all_images)} 张图片")
    
    # 加载 CLIP 模型
    print("\n加载 CLIP 模型...")
    model = SentenceTransformer('clip-ViT-B-32')
    print("CLIP 模型加载完成")
    
    # 预计算所有图片的嵌入
    print("\n预计算图片嵌入...")
    image_embeddings = []
    image_names = []
    for img_path in all_images:
        try:
            image = Image.open(img_path).convert('RGB')
            emb = model.encode([image], convert_to_tensor=True, normalize_embeddings=True)
            image_embeddings.append(emb)
            image_names.append(os.path.basename(img_path))
        except Exception as e:
            print(f"  跳过 {img_path}: {e}")
    
    print(f"成功处理 {len(image_embeddings)} 张图片")
    
    # 测试每个英文表情
    for expr in expressions:
        print(f"\n{'=' * 60}")
        print(f"表情关键词: {expr}")
        print("-" * 60)
        
        # 文本嵌入
        text_emb = model.encode([expr], convert_to_tensor=True, normalize_embeddings=True)
        
        # 计算相似度
        scores = []
        for i, img_emb in enumerate(image_embeddings):
            sim = util.cos_sim(img_emb, text_emb)[0][0].item()
            scores.append((image_names[i], sim))
        
        # 排序
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # 输出结果
        print(f"筛选结果 (共 {top_k} 张):")
        for i, (name, score) in enumerate(scores[:top_k]):
            print(f"  {i+1}. {name} - 相似度: {score:.4f}")
        print("-" * 60)
    
    # 对比中英文
    print("\n" + "=" * 80)
    print("中英文对比测试")
    print("=" * 80)
    
    comparisons = [
        ("开心", "happy smiling face"),
        ("大笑", "laughing face"),
        ("愤怒", "angry face"),
        ("悲伤", "sad face"),
    ]
    
    for cn, en in comparisons:
        print(f"\n--- {cn} vs {en} ---")
        
        # 中文
        cn_emb = model.encode([cn], convert_to_tensor=True, normalize_embeddings=True)
        cn_scores = []
        for i, img_emb in enumerate(image_embeddings):
            sim = util.cos_sim(img_emb, cn_emb)[0][0].item()
            cn_scores.append((image_names[i], sim))
        cn_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 英文
        en_emb = model.encode([en], convert_to_tensor=True, normalize_embeddings=True)
        en_scores = []
        for i, img_emb in enumerate(image_embeddings):
            sim = util.cos_sim(img_emb, en_emb)[0][0].item()
            en_scores.append((image_names[i], sim))
        en_scores.sort(key=lambda x: x[1], reverse=True)
        
        print(f"  中文 '{cn}' Top3: {[s[0] for s in cn_scores[:3]]} (分数: {[f'{s[1]:.4f}' for s in cn_scores[:3]]})")
        print(f"  英文 '{en}' Top3: {[s[0] for s in en_scores[:3]]} (分数: {[f'{s[1]:.4f}' for s in en_scores[:3]]})")


if __name__ == "__main__":
    test_clip_english()
