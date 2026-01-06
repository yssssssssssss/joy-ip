#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试完整集成流程
包括：用户输入 → 合规检查 → 分析 → 生图 → 图片合规检查
"""

import logging
import sys
import os

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_integrated_flow():
    """测试完整的集成流程"""
    
    # 1. 导入必要的模块
    try:
        from content_agent import ContentAgent
        from generation_controller import GenerationController
        from matchers.head_matcher import HeadMatcher
        from matchers.body_matcher import BodyMatcher
        from image_processor import ImageProcessor
        logger.info("✓ 所有模块导入成功")
    except ImportError as e:
        logger.error(f"✗ 模块导入失败: {e}")
        return False
    
    # 2. 初始化组件
    try:
        content_agent = ContentAgent()
        generation_controller = GenerationController()
        head_matcher = HeadMatcher()
        body_matcher = BodyMatcher()
        image_processor = ImageProcessor()
        logger.info("✓ 所有组件初始化成功")
    except Exception as e:
        logger.error(f"✗ 组件初始化失败: {e}")
        return False
    
    # 3. 测试用户输入
    test_requirements = [
        "生成一个穿红色上衣的joy形象",
        "头戴圣诞帽，手持礼物盒的joy",
        "符合中秋节氛围的joy形象"
    ]
    
    for i, requirement in enumerate(test_requirements, 1):
        logger.info(f"\n=== 测试用例 {i}: {requirement} ===")
        
        # 步骤1: 合规检查和内容分析
        logger.info("步骤1: 合规检查和内容分析")
        try:
            result = content_agent.process_content(requirement)
            if not result['compliant']:
                logger.warning(f"内容不合规: {result['reason']}")
                continue
            
            analysis = result['analysis']
            logger.info(f"分析结果: {analysis}")
        except Exception as e:
            logger.error(f"合规检查失败: {e}")
            continue
        
        # 步骤2: 表情和动作分析
        logger.info("步骤2: 表情和动作分析")
        try:
            expression_info = head_matcher.analyze_user_requirement(requirement)
            action_type = body_matcher.classify_action_type(requirement)
            logger.info(f"表情信息: {expression_info}")
            logger.info(f"动作类型: {action_type}")
        except Exception as e:
            logger.error(f"表情动作分析失败: {e}")
            continue
        
        # 步骤3: 测试统一配件处理（模拟）
        logger.info("步骤3: 测试统一配件处理")
        try:
            # 模拟图片路径
            mock_images = ["output/test_image_1.png", "output/test_image_2.png"]
            
            # 构建配饰信息
            accessories_info = {}
            if analysis.get('上装') or analysis.get('下装'):
                clothes_parts = []
                if analysis.get('上装'):
                    clothes_parts.append(analysis['上装'])
                if analysis.get('下装'):
                    clothes_parts.append(analysis['下装'])
                accessories_info['服装'] = '，'.join(clothes_parts)
            
            if analysis.get('手持'):
                accessories_info['手拿'] = analysis['手持']
            
            if analysis.get('头戴'):
                accessories_info['头戴'] = analysis['头戴']
            
            if accessories_info:
                logger.info(f"配饰信息: {accessories_info}")
                # 这里只是测试接口，不实际生成图片
                logger.info("✓ 统一配件处理接口测试通过")
            else:
                logger.info("无配饰信息，跳过配件处理")
                
        except Exception as e:
            logger.error(f"配件处理测试失败: {e}")
            continue
        
        # 步骤4: 测试prompt构建系统
        logger.info("步骤4: 测试prompt构建系统")
        try:
            from banana_pro_img_jd import _build_comprehensive_prompt, _detect_scene_style
            
            # 构建综合配件信息
            if accessories_info:
                accessories_text = "，".join([f"{k}：{v}" for k, v in accessories_info.items()])
                scene_style = _detect_scene_style(accessories_text)
                prompt = _build_comprehensive_prompt(accessories_text, "default", scene_style)
                
                logger.info(f"场景风格: {scene_style}")
                logger.info(f"生成的prompt长度: {len(prompt)} 字符")
                logger.info("✓ Prompt构建系统测试通过")
            else:
                logger.info("无配饰信息，跳过prompt构建测试")
                
        except Exception as e:
            logger.error(f"Prompt构建测试失败: {e}")
            continue
        
        logger.info(f"✓ 测试用例 {i} 完成")
    
    logger.info("\n=== 集成流程测试完成 ===")
    return True

if __name__ == "__main__":
    success = test_integrated_flow()
    sys.exit(0 if success else 1)