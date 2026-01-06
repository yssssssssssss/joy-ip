#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试服装信息提取问题：
用户输入"一个开心穿着夏威夷风格的衬衣、夏威夷风格短裤"
期望得到"夏威夷风格的衬衣、夏威夷风格短裤"
实际得到"夏威夷风格"
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_agent import ContentAgent


def test_clothing_extraction_issue():
    """测试具体的服装提取问题"""
    agent = ContentAgent()
    
    # 问题案例
    test_input = "一个开心穿着夏威夷风格的衬衣、夏威夷风格短裤"
    
    print("=== 服装信息提取问题诊断 ===")
    print(f"输入: {test_input}")
    
    # 1. 测试直接字段提取
    print("\n1. 直接字段提取测试:")
    direct_fields = agent._extract_direct_fields(test_input)
    print(f"直接提取结果: {direct_fields}")
    
    # 2. 测试完整内容分析
    print("\n2. 完整内容分析测试:")
    analysis = agent.analyze_content(test_input)
    print(f"最终服装信息: '{analysis.get('服装', '')}'")
    
    # 3. 分析正则表达式匹配
    print("\n3. 正则表达式匹配分析:")
    import re
    patterns = {
        "服装": [
            r"(?:服装|衣服|穿着|穿戴)(?:是|为|:|：)?\s*([^。;；\n]+?)(?:，(?:戴|拿)|的joy|joy|$)",
            r"穿(?:上|着)?\s*([^。;；\n]+?)(?:，(?:戴|拿)|的joy|joy|$)"
        ]
    }
    
    for label, regs in patterns.items():
        for i, reg in enumerate(regs):
            print(f"  模式{i+1}: {reg}")
            match = re.search(reg, test_input)
            if match:
                print(f"    匹配结果: '{match.group(1).strip()}'")
            else:
                print(f"    无匹配")
    
    # 4. 测试其他相似案例
    print("\n4. 其他相似案例测试:")
    similar_cases = [
        "穿着红色夹克、蓝色牛仔裤",
        "穿红色的衬衫、黑色的裤子",
        "穿着夏威夷风格衬衣和短裤",
        "一个joy穿着白色T恤、运动短裤"
    ]
    
    for case in similar_cases:
        direct = agent._extract_direct_fields(case)
        analysis = agent.analyze_content(case)
        print(f"  输入: '{case}'")
        print(f"  直接提取: {direct.get('服装', '无')}")
        print(f"  最终结果: '{analysis.get('服装', '')}'")
        print()


def test_regex_patterns():
    """详细测试正则表达式模式"""
    print("\n=== 正则表达式模式详细测试 ===")
    
    test_input = "一个开心穿着夏威夷风格的衬衣、夏威夷风格短裤"
    
    # 当前使用的模式
    current_patterns = [
        r"(?:服装|衣服|穿着|穿戴)(?:是|为|:|：)?\s*([^。;；\n]+?)(?:，(?:戴|拿)|的joy|joy|$)",
        r"穿(?:上|着)?\s*([^。;；\n]+?)(?:，(?:戴|拿)|的joy|joy|$)"
    ]
    
    # 改进的模式
    improved_patterns = [
        r"(?:服装|衣服|穿着|穿戴)(?:是|为|:|：)?\s*([^。;；\n]+?)(?:的joy|joy|$)",
        r"穿(?:上|着)?\s*([^。;；\n]+?)(?:的joy|joy|$)",
        r"穿着([^。;；\n]+?)(?:的joy|joy|$)"
    ]
    
    import re
    
    print(f"测试输入: {test_input}")
    
    print("\n当前模式测试:")
    for i, pattern in enumerate(current_patterns):
        print(f"  模式{i+1}: {pattern}")
        match = re.search(pattern, test_input)
        if match:
            result = match.group(1).strip()
            print(f"    匹配: '{result}'")
        else:
            print(f"    无匹配")
    
    print("\n改进模式测试:")
    for i, pattern in enumerate(improved_patterns):
        print(f"  改进模式{i+1}: {pattern}")
        match = re.search(pattern, test_input)
        if match:
            result = match.group(1).strip()
            print(f"    匹配: '{result}'")
        else:
            print(f"    无匹配")


def analyze_problem():
    """分析问题根源"""
    print("\n=== 问题根源分析 ===")
    
    test_input = "一个开心穿着夏威夷风格的衬衣、夏威夷风格短裤"
    
    # 分析字符串结构
    print(f"输入字符串: '{test_input}'")
    print(f"字符串长度: {len(test_input)}")
    
    # 查找关键分隔符
    print("\n关键分隔符位置:")
    print(f"  '穿着' 位置: {test_input.find('穿着')}")
    print(f"  '、' 位置: {test_input.find('、')}")
    print(f"  '，' 位置: {test_input.find('，')}")
    print(f"  '的' 位置: {[i for i, c in enumerate(test_input) if c == '的']}")
    
    # 分析当前正则表达式的问题
    import re
    pattern = r"穿(?:上|着)?\s*([^。;；\n]+?)(?:，(?:戴|拿)|的joy|joy|$)"
    print(f"\n当前正则模式: {pattern}")
    
    match = re.search(pattern, test_input)
    if match:
        print(f"匹配的完整内容: '{match.group(0)}'")
        print(f"捕获组内容: '{match.group(1)}'")
        print(f"匹配开始位置: {match.start()}")
        print(f"匹配结束位置: {match.end()}")
    
    # 问题分析
    print("\n问题分析:")
    print("1. 当前正则表达式 '(?:，(?:戴|拿)|的|，的|的joy|joy|$)' 中的 '的' 会匹配到 '夏威夷风格的' 中的 '的'")
    print("2. 这导致匹配在第一个 '的' 字符处停止，只捕获了 '夏威夷风格'")
    print("3. 需要修改正则表达式，避免过早停止匹配")


if __name__ == "__main__":
    test_clothing_extraction_issue()
    test_regex_patterns()
    analyze_problem()