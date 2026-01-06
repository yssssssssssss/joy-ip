#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试不同风格的prompt生成
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.module_loader import ModuleLoader
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_different_styles():
    """测试不同风格的prompt"""
    
    # 加载模块
    banana_unified = ModuleLoader.load('banana-pro-img-jd.py')
    
    if not banana_unified:
        logger.error("无法加载 banana-pro-img-jd.py 模块")
        return
    
    # 测试图片
    image_path = "output/combined_normal_1766633084042_a84ef5_0_0.png"
    
    # 测试不同的配件组合和风格
    test_cases = [
        {
            "name": "运动风格",
            "accessories": "服装：运动服，手拿：篮球，头戴：运动帽",
            "style": "default"
        },
        {
            "name": "正式风格", 
            "accessories": "服装：西装，手拿：公文包，头戴：礼帽",
            "style": "professional"
        },
        {
            "name": "休闲风格",
            "accessories": "服装：T恤，手拿：饮料，头戴：棒球帽",
            "style": "simple"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"测试 {i}: {test_case['name']}")
        print(f"配件: {test_case['accessories']}")
        print(f"风格: {test_case['style']}")
        print('='*60)
        
        try:
            # 调用生成函数（只生成prompt，不实际调用API）
            result = banana_unified.generate_image_with_accessories(
                image_path, 
                test_case['accessories'],
                test_case['style']
            )
            
            print(f"结果: {result}")
            
        except Exception as e:
            print(f"测试失败: {str(e)}")

if __name__ == "__main__":
    test_different_styles()