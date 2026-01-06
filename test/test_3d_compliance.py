#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3D编辑器违规词检查测试
验证3D生图流程的违规词审核功能
"""

import requests
import json
from content_agent import ContentAgent

def test_3d_compliance_api():
    """测试3D生图API的违规词检查功能"""
    
    print("="*60)
    print("3D编辑器违规词检查测试")
    print("="*60)
    
    # 测试用例
    test_cases = [
        # 应该被拦截的违规内容
        {
            "description": "女装违规词",
            "promptText": "生成一个穿裙子的角色",
            "expected_blocked": True
        },
        {
            "description": "暴力违规词", 
            "promptText": "生成一个拿刀的角色",
            "expected_blocked": True
        },
        {
            "description": "政治违规词",
            "promptText": "生成一个政治人物的形象",
            "expected_blocked": True
        },
        {
            "description": "宗教违规词",
            "promptText": "生成一个和尚的形象", 
            "expected_blocked": True
        },
        
        # 应该通过的正常内容
        {
            "description": "正常描述1",
            "promptText": "生成一个开心的角色",
            "expected_blocked": False
        },
        {
            "description": "正常描述2", 
            "promptText": "生成一个穿红色上衣的角色",
            "expected_blocked": False
        },
        {
            "description": "正常描述3",
            "promptText": "生成一个拿气球的角色",
            "expected_blocked": False
        }
    ]
    
    # 测试API端点
    api_url = "http://localhost:5000/api/run-3d-banana"
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {case['description']}")
        print(f"输入: '{case['promptText']}'")
        print(f"期望: {'应被拦截' if case['expected_blocked'] else '应通过'}")
        
        # 构造请求数据
        payload = {
            "imagePath": "/tmp/test_image.png",  # 模拟图片路径
            "promptText": case['promptText']
        }
        
        try:
            response = requests.post(api_url, json=payload, timeout=30)
            data = response.json()
            
            # 判断是否被拦截
            is_blocked = not data.get('success', False) and data.get('code') == 'COMPLIANCE'
            
            print(f"实际: {'被拦截' if is_blocked else '通过'}")
            
            if is_blocked:
                print(f"拦截原因: {data.get('error', '')}")
            
            # 验证结果
            if case['expected_blocked'] == is_blocked:
                print("✅ 测试通过")
                passed += 1
            else:
                print("❌ 测试失败")
                failed += 1
                
        except Exception as e:
            print(f"❌ 请求失败: {str(e)}")
            failed += 1
    
    # 输出测试结果
    print(f"\n{'='*60}")
    print("测试结果汇总")
    print(f"{'='*60}")
    print(f"总测试数: {len(test_cases)}")
    print(f"通过数: {passed}")
    print(f"失败数: {failed}")
    print(f"通过率: {passed/len(test_cases)*100:.1f}%")
    
    if failed == 0:
        print("🎉 所有测试通过！3D违规词检查功能正常")
    else:
        print("⚠️ 部分测试失败，请检查违规词检查逻辑")


def test_content_agent_directly():
    """直接测试ContentAgent的违规词检查功能"""
    
    print("\n" + "="*60)
    print("ContentAgent直接测试")
    print("="*60)
    
    agent = ContentAgent()
    
    test_cases = [
        "生成一个穿裙子的角色",
        "生成一个拿刀的角色", 
        "生成一个开心的角色",
        "生成一个穿红色上衣的角色"
    ]
    
    for case in test_cases:
        print(f"\n测试: '{case}'")
        is_compliant, reason = agent.check_compliance(case)
        print(f"结果: {'✅ 合规' if is_compliant else '❌ 不合规'}")
        if not is_compliant:
            print(f"原因: {reason}")


if __name__ == "__main__":
    # 先测试ContentAgent
    test_content_agent_directly()
    
    # 再测试API（需要服务器运行）
    print("\n" + "="*80)
    print("注意：API测试需要服务器运行在 localhost:5000")
    print("如果服务器未运行，API测试将失败")
    print("="*80)
    
    try:
        test_3d_compliance_api()
    except Exception as e:
        print(f"API测试失败: {str(e)}")
        print("请确保服务器正在运行")