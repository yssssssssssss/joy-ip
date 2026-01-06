#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试头像筛选 - 使用 ContentAgent 提取的"表情"关键词进行 CLIP 检索
这是一个可逆的测试脚本，不修改原有代码逻辑
"""

import os
import sys
import glob
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image
from sentence_transformers import SentenceTransformer, util
from content_agent import ContentAgent


# 表情关键词列表（用于从用户输入中直接提取）
EXPRESSION_KEYWORDS = [
    "大笑", "微笑", "开心", "愉快", "高兴", "喜悦", "快乐", "欢乐",
    "愤怒", "生气", "怒视", "发怒", "暴怒",
    "悲伤", "难过", "哭泣", "伤心", "忧伤", "哀伤",
    "惊讶", "震惊", "吃惊", "惊恐", "惊喜",
    "害羞", "脸红", "羞涩",
    "冷漠", "面瘫", "无表情", "淡定", "平静",
    "张嘴", "咧嘴", "闭嘴", "嘟嘴", "撅嘴",
    "眨眼", "闭眼", "睁眼", "瞪眼", "眯眼",
    "皱眉", "挑眉", "蹙眉",
    "得意", "骄傲", "自信", "傲慢",
    "委屈", "无奈", "尴尬", "紧张", "焦虑",
    "思考", "沉思", "疑惑", "困惑",
    "可爱", "呆萌", "卖萌", "撒娇",
]


def extract_expression_from_text(text: str) -> str:
    """从文本中直接提取表情关键词"""
    for kw in EXPRESSION_KEYWORDS:
        if kw in text:
            return kw
    return ""


class SimpleClipMatcher:
    """简化的 CLIP 匹配器，直接使用表情关键词检索"""
    
    def __init__(self):
        self.clip_model = None
    
    def _ensure_clip_model(self):
        if self.clip_model is None:
            print("加载 CLIP 模型...")
            self.clip_model = SentenceTransformer('clip-ViT-B-32')
            print("CLIP 模型加载完成")
    
    def search_by_expression(self, expression_text: str, folder_path: str, top_k: int = 3):
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
        
        print(f"CLIP 检索文本: {expression_text}")
        print(f"图片数量: {len(all_images)}")
        
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


def test_with_content_agent(requirements: list, folder_path: str = "data/face_front_per", top_k: int = 3):
    """使用 ContentAgent 提取表情，然后进行 CLIP 检索"""
    
    agent = ContentAgent()
    matcher = SimpleClipMatcher()
    
    print("=" * 80)
    print("头像筛选测试 (使用 ContentAgent 提取表情)")
    print(f"测试文件夹: {folder_path}")
    print(f"返回数量: {top_k}")
    print("=" * 80)
    
    for req in requirements:
        print(f"\n{'='*60}")
        print(f"原始需求: {req}")
        print("-" * 60)
        
        # 方法1: 直接从文本提取表情关键词
        direct_expression = extract_expression_from_text(req)
        print(f"直接提取的表情关键词: {direct_expression or '(无)'}")
        
        # 方法2: 使用 ContentAgent 分析内容
        analysis = agent.analyze_content(req)
        agent_expression = analysis.get("表情", "")
        
        print(f"ContentAgent 分析结果:")
        print(f"  表情: {agent_expression}")
        print(f"  动作: {analysis.get('动作', '')}")
        print("-" * 60)
        
        # 优先使用直接提取的表情，其次使用 ContentAgent 的结果
        search_text = direct_expression or agent_expression
        if not search_text or search_text == "未识别":
            search_text = req  # 回退到原始需求
        
        print(f"最终用于 CLIP 检索的文本: {search_text}")
        
        results = matcher.search_by_expression(search_text, folder_path, top_k)
        
        print(f"\n筛选结果 (共 {len(results)} 张):")
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r['image_name']} - 相似度: {r['score']:.4f}")
        
        print("-" * 60)


if __name__ == "__main__":
    # 默认测试需求
    test_requirements = [
        "开心的角色",
        "愤怒的表情",
        "悲伤难过",
        "惊讶的样子",
        "微笑",
        "大笑",
    ]
    
    # 命令行参数
    if len(sys.argv) > 1:
        test_requirements = sys.argv[1:]
    
    folder = "data/face_front_per"
    if not os.path.exists(folder):
        print(f"错误: 文件夹 {folder} 不存在")
        sys.exit(1)
    
    test_with_content_agent(test_requirements, folder_path=folder, top_k=3)
