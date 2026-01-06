#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速验证修复后的功能是否正常
"""

from content_agent import ContentAgent

def test_basic_functionality():
    """测试基本功能是否正常"""
    print("="*60)
    print("快速功能验证测试")
    print("="*60)
    
    agent = ContentAgent()
    
    # 测试合规检查
    print("\n1. 合规检查测试:")
    test_cases = [
        ("生成一个穿红夹克的joy", True),  # 应该通过
        ("生成一个穿裙子的形象", False),   # 应该被拦截
    ]
    
    for content, should_pass in test_cases:
        is_compliant, reason = agent.check_compliance(content)
        status = "✅ 通过" if (is_compliant == should_pass) else "❌ 失败"
        print(f"  输入: '{content}'")
        print(f"  期望: {'通过' if should_pass else '拦截'}, 实际: {'通过' if is_compliant else '拦截'}")
        print(f"  状态: {status}")
        if not is_compliant:
            print(f"  原因: {reason}")
        print()
    
    # 测试服装提取
    print("2. 服装信息提取测试:")
    clothing_tests = [
        "穿着红夹克，牛仔裤的joy",
        "穿红夹克和白T恤的角色",
        "服装：蓝色外套，黑色裤子"
    ]
    
    for content in clothing_tests:
        result = agent.analyze_content(content)
        print(f"  输入: '{content}'")
        print(f"  服装提取: '{result.get('服装', '')}'")
        print()

if __name__ == "__main__":
    test_basic_functionality()