#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服装补全逻辑测试和设计
测试只有上装或只有下装时的补全逻辑
"""

import re
from content_agent import ContentAgent

def analyze_clothing_type(clothing_info: str) -> dict:
    """
    分析服装信息，判断是否只有上装或只有下装
    
    Args:
        clothing_info: 服装信息字符串
        
    Returns:
        dict: 包含分析结果的字典
    """
    if not clothing_info:
        return {"has_top": False, "has_bottom": False, "needs_completion": False}
    
    clothing_lower = clothing_info.lower()
    
    # 上装关键词
    top_keywords = [
        # 中文上装
        "夹克", "外套", "上衣", "衬衫", "T恤", "t恤", "毛衣", "卫衣", "背心", 
        "马甲", "西装", "风衣", "大衣", "棉衣", "羽绒服", "开衫", "针织衫",
        "polo衫", "吊带", "抹胸", "胸衣", "内衣", "文胸",
        # 英文上装
        "jacket", "coat", "shirt", "t-shirt", "tshirt", "sweater", "hoodie", 
        "vest", "blazer", "cardigan", "top", "blouse", "tank"
    ]
    
    # 下装关键词
    bottom_keywords = [
        # 中文下装
        "裤子", "牛仔裤", "长裤", "短裤", "运动裤", "休闲裤", "西裤", "工装裤",
        "打底裤", "紧身裤", "阔腿裤", "直筒裤", "喇叭裤", "哈伦裤", "七分裤",
        "九分裤", "五分裤", "热裤", "裙子", "连衣裙", "短裙", "长裙", "半身裙",
        "百褶裙", "A字裙", "包臀裙", "蓬蓬裙", "牛仔裙", "纱裙",
        # 英文下装
        "pants", "jeans", "trousers", "shorts", "skirt", "dress", "leggings"
    ]
    
    # 检查是否包含上装
    has_top = any(keyword in clothing_lower for keyword in top_keywords)
    
    # 检查是否包含下装
    has_bottom = any(keyword in clothing_lower for keyword in bottom_keywords)
    
    # 判断是否需要补全
    needs_completion = (has_top and not has_bottom) or (has_bottom and not has_top)
    
    return {
        "has_top": has_top,
        "has_bottom": has_bottom,
        "needs_completion": needs_completion,
        "completion_type": "bottom" if has_top and not has_bottom else "top" if has_bottom and not has_top else "none"
    }

def generate_clothing_completion_prompt(clothing_info: str, completion_type: str) -> str:
    """
    生成服装补全的AI提示词
    
    Args:
        clothing_info: 现有服装信息
        completion_type: 补全类型 ("top" 或 "bottom")
        
    Returns:
        str: AI提示词
    """
    if completion_type == "bottom":
        return f"""
        用户描述了上装：{clothing_info}
        
        请根据上装的风格，推荐合适的下装搭配。要求：
        1. 风格协调：下装应与上装风格匹配
        2. 颜色搭配：考虑颜色的和谐搭配
        3. 场合适宜：符合整体穿搭场合
        4. 简洁描述：用简短的词语描述下装
        
        请只返回下装的描述，格式如：牛仔裤、黑色长裤、蓝色短裙等
        """
    elif completion_type == "top":
        return f"""
        用户描述了下装：{clothing_info}
        
        请根据下装的风格，推荐合适的上装搭配。要求：
        1. 风格协调：上装应与下装风格匹配
        2. 颜色搭配：考虑颜色的和谐搭配
        3. 场合适宜：符合整体穿搭场合
        4. 简洁描述：用简短的词语描述上装
        
        请只返回上装的描述，格式如：白色T恤、黑色衬衫、红色夹克等
        """
    else:
        return ""

def test_clothing_analysis():
    """测试服装分析逻辑"""
    print("="*60)
    print("服装分析测试")
    print("="*60)
    
    test_cases = [
        # 只有上装的情况
        "红色夹克",
        "白色T恤",
        "黑色西装外套",
        "蓝色卫衣",
        
        # 只有下装的情况
        "牛仔裤",
        "黑色长裤",
        "蓝色短裙",
        "运动裤",
        
        # 上下装都有的情况
        "红色夹克，牛仔裤",
        "白色T恤和黑色短裤",
        "蓝色衬衫配灰色西裤",
        
        # 没有明确上下装的情况
        "运动服",
        "校服",
        "工作服"
    ]
    
    for clothing in test_cases:
        analysis = analyze_clothing_type(clothing)
        print(f"\n服装: '{clothing}'")
        print(f"  有上装: {analysis['has_top']}")
        print(f"  有下装: {analysis['has_bottom']}")
        print(f"  需要补全: {analysis['needs_completion']}")
        print(f"  补全类型: {analysis['completion_type']}")
        
        if analysis['needs_completion']:
            prompt = generate_clothing_completion_prompt(clothing, analysis['completion_type'])
            print(f"  补全提示: {prompt[:100]}...")

def test_with_content_agent():
    """使用ContentAgent测试服装补全"""
    print("\n" + "="*60)
    print("ContentAgent服装补全测试")
    print("="*60)
    
    agent = ContentAgent()
    
    test_cases = [
        "穿红色夹克的joy",  # 只有上装
        "穿牛仔裤的joy",    # 只有下装
        "穿红色夹克，牛仔裤的joy"  # 完整搭配
    ]
    
    for content in test_cases:
        print(f"\n输入: '{content}'")
        result = agent.analyze_content(content)
        clothing = result.get('服装', '')
        print(f"提取的服装: '{clothing}'")
        
        # 分析是否需要补全
        analysis = analyze_clothing_type(clothing)
        print(f"分析结果: {analysis}")
        
        if analysis['needs_completion']:
            print(f"建议补全{analysis['completion_type']}装")

if __name__ == "__main__":
    test_clothing_analysis()
    test_with_content_agent()