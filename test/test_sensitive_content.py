#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试敏感内容检查系统
"""

from content_agent import ContentAgent
from generation_controller import GenerationController

def test_sensitive_content_detection():
    """测试敏感内容检测功能"""
    print("=== 测试敏感内容检测系统 ===")
    
    agent = ContentAgent()
    controller = GenerationController()
    
    # 测试用例
    test_cases = [
        # 正常内容
        {
            "name": "正常内容",
            "analysis": {
                "表情": "开心",
                "动作": "站姿",
                "服装": "红色上衣",
                "手拿": "气球",
                "头戴": "帽子"
            }
        },
        
        # 违规词库检测
        {
            "name": "违规词库检测 - 包含'裙'",
            "analysis": {
                "表情": "开心",
                "服装": "裙子",
                "手拿": "花束"
            }
        },
        
        # 宗教相关敏感内容
        {
            "name": "宗教敏感内容",
            "analysis": {
                "表情": "虔诚",
                "服装": "僧袍",
                "手拿": "佛珠",
                "头戴": "僧帽"
            }
        },
        
        # 政治相关敏感内容
        {
            "name": "政治敏感内容",
            "analysis": {
                "表情": "严肃",
                "服装": "军装",
                "手拿": "国旗",
                "背景": "天安门"
            }
        },
        
        # 民族相关敏感内容
        {
            "name": "民族敏感内容",
            "analysis": {
                "表情": "传统",
                "服装": "藏族服装",
                "手拿": "哈达",
                "头戴": "民族头饰"
            }
        },
        
        # 国家相关敏感内容
        {
            "name": "国家敏感内容",
            "analysis": {
                "表情": "庄严",
                "服装": "制服",
                "手拿": "国徽",
                "背景": "国旗背景"
            }
        },
        
        # 暴力相关内容
        {
            "name": "暴力相关内容",
            "analysis": {
                "表情": "愤怒",
                "动作": "打斗",
                "手拿": "刀",
                "背景": "战场"
            }
        }
    ]
    
    print(f"\n开始测试 {len(test_cases)} 个用例...")
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{'='*50}")
        print(f"测试用例 {i}: {case['name']}")
        print(f"内容: {case['analysis']}")
        
        # 使用GenerationController进行检查
        result = controller.check_content_compliance(case['analysis'])
        
        print(f"最终结果: {'✓ 通过' if result else '✗ 拒绝'}")
    
    print(f"\n{'='*50}")
    print("测试完成")

def test_direct_content_check():
    """直接测试内容字符串检查"""
    print("\n=== 直接内容字符串检查测试 ===")
    
    agent = ContentAgent()
    
    test_contents = [
        "生成一个开心的joy形象",                    # 正常
        "生成一个穿裙子的形象",                     # 违规词
        "生成一个穿僧袍的和尚形象",                 # 宗教
        "生成一个拿着国旗的政治人物形象",           # 政治
        "生成一个穿藏族服装的形象",                 # 民族
        "生成一个在天安门前的形象",                 # 国家象征
        "生成一个拿刀砍人的暴力形象",               # 暴力
    ]
    
    for content in test_contents:
        print(f"\n检查内容: '{content}'")
        is_compliant, reason = agent.check_compliance(content)
        status = "✓ 合规" if is_compliant else f"✗ 不合规: {reason}"
        print(f"结果: {status}")

if __name__ == "__main__":
    test_sensitive_content_detection()
    test_direct_content_check()