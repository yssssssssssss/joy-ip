#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试违规词库系统
"""

from content_agent import ContentAgent

def test_banned_words_system():
    """测试违规词库系统"""
    print("=== 测试违规词库系统 ===")
    
    agent = ContentAgent()
    
    # 测试普通违规词检查
    print("\n1. 测试普通违规词检查:")
    test_cases = [
        "生成一个开心的joy形象",  # 正常内容
        "生成一个暴力的形象",     # 包含违规词
        "生成一个女孩的形象",     # 包含正则表达式匹配的违规词
        "生成一个穿裙子的形象",   # 包含违规词
    ]
    
    for content in test_cases:
        is_compliant, reason = agent.check_compliance(content)
        status = "✓ 合规" if is_compliant else f"✗ 不合规: {reason}"
        print(f"  '{content}' -> {status}")
    
    # 测试动态添加违规词
    print("\n2. 测试动态添加违规词:")
    test_word = "测试违规词"
    success = agent.add_banned_word(test_word)
    print(f"  添加 '{test_word}': {'成功' if success else '失败'}")
    
    # 测试新添加的违规词
    is_compliant, reason = agent.check_compliance("生成一个测试违规词的形象")
    status = "✓ 合规" if is_compliant else f"✗ 不合规: {reason}"
    print(f"  测试新违规词: {status}")
    
    # 测试动态添加正则表达式
    print("\n3. 测试动态添加正则表达式:")
    test_regex = "REGEX:测试\\d+"
    success = agent.add_banned_word(test_regex)
    print(f"  添加正则 '{test_regex}': {'成功' if success else '失败'}")
    
    # 测试新添加的正则表达式
    is_compliant, reason = agent.check_compliance("生成一个测试123的形象")
    status = "✓ 合规" if is_compliant else f"✗ 不合规: {reason}"
    print(f"  测试新正则: {status}")
    
    # 测试移除违规词
    print("\n4. 测试移除违规词:")
    success = agent.remove_banned_word(test_word)
    print(f"  移除 '{test_word}': {'成功' if success else '失败'}")
    
    # 测试移除后的效果
    is_compliant, reason = agent.check_compliance("生成一个测试违规词的形象")
    status = "✓ 合规" if is_compliant else f"✗ 不合规: {reason}"
    print(f"  移除后测试: {status}")
    
    # 测试移除正则表达式
    success = agent.remove_banned_word(test_regex)
    print(f"  移除正则 '{test_regex}': {'成功' if success else '失败'}")
    
    # 显示当前违规词库统计
    print(f"\n5. 当前违规词库统计:")
    print(f"  普通违规词: {len(agent.banned_words)} 个")
    print(f"  正则表达式: {len(agent.banned_patterns)} 个")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_banned_words_system()