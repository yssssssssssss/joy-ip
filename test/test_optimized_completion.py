#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试优化后的服装补全功能
"""

from content_agent import ContentAgent

def test_optimized_completion():
    """测试优化后的服装补全"""
    print("="*60)
    print("优化后的服装补全测试")
    print("="*60)
    
    agent = ContentAgent()
    
    test_cases = [
        "穿牛仔裤的joy",  # 之前结果过长的案例
        "穿红色夹克的joy",
        "穿黑色长裤的角色"
    ]
    
    for content in test_cases:
        print(f"\n输入: '{content}'")
        print("-" * 40)
        
        result = agent.analyze_content(content)
        clothing = result.get('服装', '')
        
        print(f"最终服装: '{clothing}'")

if __name__ == "__main__":
    test_optimized_completion()