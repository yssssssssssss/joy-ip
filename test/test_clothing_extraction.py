#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服装信息提取逻辑测试
分析从用户输入中提取服装信息的完整流程
"""

import re
from content_agent import ContentAgent

def test_direct_extraction():
    """测试直接提取逻辑"""
    print("="*60)
    print("1. 直接提取逻辑测试 (_extract_direct_fields)")
    print("="*60)
    
    agent = ContentAgent()
    
    test_cases = [
        "穿着红夹克，牛仔裤的joy",
        "穿红夹克和牛仔裤的joy",
        "穿着红夹克、牛仔裤的角色",
        "服装：红夹克，牛仔裤",
        "穿红夹克，戴帽子，拿气球的joy",
        "生成一个穿着红夹克，牛仔裤的joy"
    ]
    
    for case in test_cases:
        print(f"\n输入: '{case}'")
        direct_fields = agent._extract_direct_fields(case)
        print(f"直接提取结果: {direct_fields}")
        
        # 分析正则匹配过程
        patterns = {
            "服装": [
                r"(?:服装|衣服|穿着|穿戴)(?:是|为|:|：)?\s*([^\n,，。;；]+)",
                r"穿(?:上|着)?\s*([^\n,，。;；]+)"
            ]
        }
        
        for label, regs in patterns.items():
            for i, reg in enumerate(regs):
                m = re.search(reg, case)
                if m:
                    print(f"  正则{i+1}匹配: '{m.group(1).strip()}'")
                    break
                else:
                    print(f"  正则{i+1}未匹配")

def test_ai_extraction():
    """测试AI提取逻辑"""
    print("\n" + "="*60)
    print("2. AI提取逻辑测试 (_request_ai_fields)")
    print("="*60)
    
    agent = ContentAgent()
    
    test_cases = [
        "穿着红夹克，牛仔裤的joy",
        "穿红夹克和牛仔裤的joy",
        "生成一个穿着红夹克，牛仔裤的开心角色"
    ]
    
    for case in test_cases:
        print(f"\n输入: '{case}'")
        print("调用AI提取服装信息...")
        
        try:
            ai_result = agent._request_ai_fields(case, ["服装"], enforce_guess=False)
            print(f"AI原始返回: '{ai_result}'")
            
            # 解析AI返回结果
            if ai_result:
                lines = ai_result.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('服装：') or line.startswith('服装:'):
                        clothing = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                        print(f"解析出的服装: '{clothing}'")
        except Exception as e:
            print(f"AI提取失败: {e}")

def test_complete_analysis():
    """测试完整分析流程"""
    print("\n" + "="*60)
    print("3. 完整分析流程测试 (analyze_content)")
    print("="*60)
    
    agent = ContentAgent()
    
    test_cases = [
        "穿着红夹克，牛仔裤的joy",
        "穿红夹克和牛仔裤的joy",
        "生成一个穿着红夹克，牛仔裤的开心角色",
        "我想要一个穿红夹克，牛仔裤，戴帽子的joy"
    ]
    
    for case in test_cases:
        print(f"\n输入: '{case}'")
        print("-" * 40)
        
        result = agent.analyze_content(case)
        print(f"最终服装结果: '{result.get('服装', '')}'")
        print(f"完整分析结果: {result}")
        
        # 显示AI原始输出（如果有）
        if result.get('_raw_ai'):
            print(f"AI原始输出: {result['_raw_ai']}")

def analyze_regex_patterns():
    """分析正则表达式模式的问题"""
    print("\n" + "="*60)
    print("4. 正则表达式模式分析")
    print("="*60)
    
    test_input = "穿着红夹克，牛仔裤的joy"
    
    patterns = [
        r"(?:服装|衣服|穿着|穿戴)(?:是|为|:|：)?\s*([^\n,，。;；]+)",
        r"穿(?:上|着)?\s*([^\n,，。;；]+)"
    ]
    
    print(f"测试输入: '{test_input}'")
    print("\n当前正则表达式:")
    
    for i, pattern in enumerate(patterns, 1):
        print(f"\n正则{i}: {pattern}")
        m = re.search(pattern, test_input)
        if m:
            print(f"  匹配结果: '{m.group(1)}'")
            print(f"  匹配范围: {m.span()}")
            print(f"  完整匹配: '{m.group(0)}'")
        else:
            print("  未匹配")
    
    print("\n问题分析:")
    print("当前正则表达式 [^\\n,，。;；]+ 会在遇到逗号时停止匹配")
    print("对于 '穿着红夹克，牛仔裤的joy'，只能匹配到 '红夹克'")
    
    print("\n改进建议:")
    improved_patterns = [
        r"(?:服装|衣服|穿着|穿戴)(?:是|为|:|：)?\s*([^。;；\n]+?)(?:的|，的|的joy|joy|$)",
        r"穿(?:上|着)?\s*([^。;；\n]+?)(?:的|，的|的joy|joy|$)"
    ]
    
    for i, pattern in enumerate(improved_patterns, 1):
        print(f"\n改进正则{i}: {pattern}")
        m = re.search(pattern, test_input)
        if m:
            print(f"  匹配结果: '{m.group(1)}'")
            print(f"  匹配范围: {m.span()}")
        else:
            print("  未匹配")

if __name__ == "__main__":
    test_direct_extraction()
    test_ai_extraction()
    test_complete_analysis()
    analyze_regex_patterns()