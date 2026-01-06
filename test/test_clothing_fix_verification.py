#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证服装信息提取修复效果
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_agent import ContentAgent


def test_clothing_fix():
    """验证修复效果"""
    agent = ContentAgent()
    
    # 原问题案例
    test_case = "一个开心穿着夏威夷风格的衬衣、夏威夷风格短裤"
    
    print("=== 服装信息提取修复验证 ===")
    print(f"输入: {test_case}")
    
    # 测试直接提取
    direct_result = agent._extract_direct_fields(test_case)
    print(f"直接提取结果: {direct_result.get('服装', '无')}")
    
    # 测试完整分析
    analysis = agent.analyze_content(test_case)
    final_clothing = analysis.get('服装', '')
    print(f"最终服装信息: {final_clothing}")
    
    # 验证结果
    expected_keywords = ["夏威夷风格", "衬衣", "短裤"]
    success = all(keyword in final_clothing for keyword in expected_keywords)
    
    print(f"\n验证结果: {'✅ 修复成功' if success else '❌ 仍有问题'}")
    
    if success:
        print("✓ 成功提取完整的服装描述")
        print("✓ 包含所有关键信息：夏威夷风格、衬衣、短裤")
    else:
        print("✗ 服装信息提取不完整")
        missing = [kw for kw in expected_keywords if kw not in final_clothing]
        print(f"✗ 缺失关键词: {missing}")
    
    return success


def test_additional_cases():
    """测试其他相关案例"""
    agent = ContentAgent()
    
    test_cases = [
        {
            "input": "穿着红色的夹克、蓝色的牛仔裤",
            "expected": ["红色", "夹克", "蓝色", "牛仔裤"]
        },
        {
            "input": "一个joy穿着白色的T恤、黑色的运动短裤",
            "expected": ["白色", "T恤", "黑色", "运动短裤"]
        },
        {
            "input": "穿绿色的衬衫、棕色的长裤",
            "expected": ["绿色", "衬衫", "棕色", "长裤"]
        }
    ]
    
    print("\n=== 其他案例验证 ===")
    all_passed = True
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. 测试: {case['input']}")
        
        direct_result = agent._extract_direct_fields(case['input'])
        clothing = direct_result.get('服装', '')
        
        print(f"   提取结果: {clothing}")
        
        # 检查是否包含所有期望的关键词
        missing = [kw for kw in case['expected'] if kw not in clothing]
        if missing:
            print(f"   ❌ 缺失: {missing}")
            all_passed = False
        else:
            print(f"   ✅ 完整提取")
    
    print(f"\n其他案例测试结果: {'✅ 全部通过' if all_passed else '❌ 部分失败'}")
    return all_passed


if __name__ == "__main__":
    print("开始验证服装信息提取修复...")
    
    # 测试主要问题
    main_fix = test_clothing_fix()
    
    # 测试其他案例
    other_cases = test_additional_cases()
    
    # 总结
    print(f"\n=== 总体验证结果 ===")
    if main_fix and other_cases:
        print("🎉 所有测试通过！服装信息提取问题已完全修复")
    elif main_fix:
        print("✅ 主要问题已修复，但其他案例需要进一步优化")
    else:
        print("❌ 主要问题仍未解决，需要继续调试")