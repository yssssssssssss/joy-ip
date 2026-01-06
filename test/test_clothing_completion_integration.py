#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服装补全功能集成测试
测试ContentAgent中的服装补全逻辑
"""

from content_agent import ContentAgent

def test_clothing_completion():
    """测试服装补全功能"""
    print("="*60)
    print("服装补全功能测试")
    print("="*60)
    
    agent = ContentAgent()
    
    test_cases = [
        {
            "input": "穿红色夹克的joy",
            "description": "只有上装，应该补全下装"
        },
        {
            "input": "穿牛仔裤的joy", 
            "description": "只有下装，应该补全上装"
        },
        {
            "input": "穿白色T恤的角色",
            "description": "只有上装，应该补全下装"
        },
        {
            "input": "穿黑色长裤的人物",
            "description": "只有下装，应该补全上装"
        },
        {
            "input": "穿红色夹克，牛仔裤的joy",
            "description": "完整搭配，不需要补全"
        },
        {
            "input": "穿运动服的joy",
            "description": "通用服装，不需要补全"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {case['description']}")
        print(f"输入: '{case['input']}'")
        print("-" * 40)
        
        try:
            result = agent.analyze_content(case['input'])
            clothing = result.get('服装', '')
            
            print(f"最终服装结果: '{clothing}'")
            
            # 分析补全效果
            analysis = agent._analyze_clothing_type(clothing)
            if analysis['needs_completion']:
                print("⚠️  仍需补全，可能补全失败")
            else:
                print("✅ 服装信息完整")
                
        except Exception as e:
            print(f"❌ 测试失败: {e}")

def test_clothing_analysis_only():
    """仅测试服装分析逻辑"""
    print("\n" + "="*60)
    print("服装分析逻辑测试")
    print("="*60)
    
    agent = ContentAgent()
    
    test_clothing = [
        "红色夹克",
        "牛仔裤", 
        "红色夹克，牛仔裤",
        "白色T恤",
        "黑色长裤",
        "运动服",
        "校服"
    ]
    
    for clothing in test_clothing:
        analysis = agent._analyze_clothing_type(clothing)
        print(f"\n服装: '{clothing}'")
        print(f"  分析结果: {analysis}")

if __name__ == "__main__":
    test_clothing_analysis_only()
    test_clothing_completion()