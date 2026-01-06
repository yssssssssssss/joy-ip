#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试头像筛选逻辑
验证不同表情关键词会筛选出哪些头像
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from matchers.head_matcher import HeadMatcher

def test_head_selection(requirements: list, folder_path: str = "data/face_front_per", top_k: int = 3):
    """测试不同需求的头像筛选结果"""
    
    matcher = HeadMatcher()
    
    print("=" * 80)
    print("头像筛选测试")
    print(f"测试文件夹: {folder_path}")
    print(f"返回数量: {top_k}")
    print("=" * 80)
    
    for req in requirements:
        print(f"\n{'='*60}")
        print(f"测试需求: {req}")
        print("-" * 60)
        
        results, logs = matcher.find_best_matches_from_folder(
            requirement=req,
            folder_path=folder_path,
            top_k=top_k
        )
        
        print(f"\n筛选结果 (共 {len(results)} 张):")
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r['image_name']} - 相似度: {r['score']:.4f}")
        
        print("-" * 60)


if __name__ == "__main__":
    # 默认测试的表情关键词列表
    test_requirements = [
        "开心",
        "微笑",
        "大笑",
        "愤怒",
        "悲伤",
        "惊讶",
        "害羞",
        "冷漠",
    ]
    
    # 可以通过命令行参数指定测试关键词
    if len(sys.argv) > 1:
        test_requirements = sys.argv[1:]
    
    # 检查文件夹是否存在
    folder = "data/face_front_per"
    if not os.path.exists(folder):
        print(f"警告: 文件夹 {folder} 不存在，请检查路径")
        # 尝试列出 data 目录下的文件夹
        if os.path.exists("data"):
            print("data 目录下的文件夹:")
            for item in os.listdir("data"):
                if os.path.isdir(os.path.join("data", item)):
                    print(f"  - {item}")
        sys.exit(1)
    
    test_head_selection(test_requirements, folder_path=folder, top_k=3)
