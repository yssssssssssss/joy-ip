#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服装信息提取修复验证测试
验证修复后的正则表达式能正确提取完整的服装信息
"""

import re
from content_agent import ContentAgent

def test_fixed_extraction():
    """测试修复后的提取逻辑"""
    print("="*60)
    print("修复后的服装信息提取测试")
    print("="*60)
    
    agent = ContentAgent()
    
    test_cases = [
        {
            "input": "穿着红夹克，牛仔裤的joy",
            "expected": "红夹克，牛仔裤"
        },
        {
            "input": "穿着红夹克，牛仔裤，白鞋的joy",
            "expected": "红夹克，牛仔裤，白鞋"
        },
        {
            "input": "服装：红夹克，牛仔裤",
            "expected": "红夹克，牛仔裤"
        },
        {
            "input": "穿红夹克和牛仔裤的joy",
            "expected": "红夹克和牛仔裤"
        },
        {
            "input": "穿着红夹克、牛仔裤、白鞋的角色",
            "expected": "红夹克、牛仔裤、白鞋"
        },
        {
            "input": "生成一个穿着红夹克，牛仔裤的joy",
            "expected": "红夹克，牛仔裤"
        },
        {
            "input": "穿红夹克，戴帽子，拿气球的joy",
            "expected": "红夹克"
        }
    ]
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: '{case['input']}'")
        
        # 测试直接提取
        direct_fields = agent._extract_direct_fields(case['input'])
        extracted_clothing = direct_fields.get('服装', '')
        
        print(f"期望结果: '{case['expected']}'")
        print(f"提取结果: '{extracted_clothing}'")
        
        if extracted_clothing == case['expected']:
            print("✅ 通过")
            success_count += 1
        else:
            print("❌ 失败")
            
        # 显示完整分析结果
        full_result = agent.analyze_content(case['input'])
        print(f"完整分析服装: '{full_result.get('服装', '')}'")
    
    print(f"\n{'='*60}")
    print(f"测试总结: {success_count}/{total_count} 通过 ({success_count/total_count*100:.1f}%)")
    print(f"{'='*60}")

def test_regex_patterns():
    """测试修复后的正则表达式模式"""
    print("\n" + "="*60)
    print("正则表达式模式验证")
    print("="*60)
    
    # 修复后的正则表达式
    patterns = [
        r"(?:服装|衣服|穿着|穿戴)(?:是|为|:|：)?\s*([^。;；\n]+?)(?:的|，的|的joy|joy|$)",
        r"穿(?:上|着)?\s*([^。;；\n]+?)(?:的|，的|的joy|joy|$)"
    ]
    
    test_inputs = [
        "穿着红夹克，牛仔裤的joy",
        "穿着红夹克，牛仔裤，白鞋的joy",
        "服装：红夹克，牛仔裤",
        "穿红夹克和牛仔裤的joy",
        "穿着红夹克、牛仔裤的角色"
    ]
    
    for test_input in test_inputs:
        print(f"\n测试输入: '{test_input}'")
        
        for i, pattern in enumerate(patterns, 1):
            match = re.search(pattern, test_input)
            if match:
                print(f"  正则{i}匹配: '{match.group(1)}'")
                break
            else:
                print(f"  正则{i}未匹配")

if __name__ == "__main__":
    test_fixed_extraction()
    test_regex_patterns()