#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试统一配件处理流程
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from generation_controller import GenerationController
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_unified_accessories():
    """测试统一配件处理"""
    
    # 创建控制器
    controller = GenerationController()
    
    # 模拟输入图片
    test_images = [
        "output/combined_normal_1766633084042_a84ef5_0_0.png"
    ]
    
    # 模拟分析结果
    analysis = {
        '表情': '开心',
        '动作': '站姿',
        '服装': '红色卫衣',
        '手拿': '气球',
        '头戴': '棒球帽'
    }
    
    logger.info("开始测试统一配件处理流程")
    logger.info(f"输入图片: {test_images}")
    logger.info(f"分析结果: {analysis}")
    
    # 测试统一配件处理
    result_images = controller.process_accessories_unified(test_images, analysis)
    
    logger.info(f"处理结果: {result_images}")
    
    return result_images

def test_banana_pro_directly():
    """直接测试 banana-pro-img-jd.py 模块"""
    
    try:
        from utils.module_loader import ModuleLoader
        
        # 加载模块
        banana_unified = ModuleLoader.load('banana-pro-img-jd.py')
        
        if not banana_unified:
            logger.error("无法加载 banana-pro-img-jd.py 模块")
            return None
        
        # 测试参数
        image_path = "output/combined_normal_1766633084042_a84ef5_0_0.png"
        accessories_info = "服装：红色卫衣，手拿：气球，头戴：棒球帽"
        
        logger.info(f"直接测试 banana-pro-img-jd 模块")
        logger.info(f"输入图片: {image_path}")
        logger.info(f"配件信息: {accessories_info}")
        
        # 调用生成函数
        result = banana_unified.generate_image_with_accessories(image_path, accessories_info)
        
        logger.info(f"生成结果: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        return None

if __name__ == "__main__":
    print("=== 测试1: 直接测试 banana-pro-img-jd 模块 ===")
    test_banana_pro_directly()
    
    print("\n=== 测试2: 测试统一配件处理流程 ===")
    test_unified_accessories()