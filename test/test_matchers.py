#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试匹配器修复效果
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from matchers.body_matcher import BodyMatcher
from matchers.head_matcher import HeadMatcher

def test_body_matcher():
    """测试身体匹配器"""
    print("=== 测试身体匹配器 ===")
    
    body_matcher = BodyMatcher()
    
    # 测试用例
    test_cases = [
        "跑动",
        "大笑",
        "站立",
        "跳跃",
        "坐着"
    ]
    
    for case in test_cases:
        print(f"\n测试用例: '{case}'")
        
        # 测试动作分类
        action_type = body_matcher.classify_action_type(case)
        print(f"动作分类结果: {action_type}")
        
        # 测试需求分析
        analysis = body_matcher.analyze_user_requirement(case)
        print(f"需求分析结果: {analysis}")

def test_head_matcher():
    """测试头像匹配器"""
    print("\n=== 测试头像匹配器 ===")
    
    head_matcher = HeadMatcher()
    
    # 测试用例
    test_cases = [
        "大笑",
        "开心",
        "惊讶",
        "愤怒",
        "平静"
    ]
    
    for case in test_cases:
        print(f"\n测试用例: '{case}'")
        
        # 测试需求分析
        analysis = head_matcher.analyze_user_requirement(case)
        print(f"需求分析结果: {analysis}")

if __name__ == "__main__":
    test_body_matcher()
    test_head_matcher()