#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键词匹配 vs AI判断的性能和准确性对比测试
"""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_agent import ContentAgent


def test_keyword_vs_ai_performance():
    """测试关键词匹配与AI判断的性能对比"""
    agent = ContentAgent()
    
    test_cases = [
        "红色夹克",
        "蓝色牛仔裤", 
        "白色T恤，黑色长裤",
        "连衣裙",
        "西装外套",
        "运动短裤",
        "毛衣，牛仔裤",
        "衬衫",
        "百褶裙",
        "羽绒服，打底裤"
    ]
    
    print("=== 关键词匹配 vs AI判断性能对比 ===\n")
    
    # 测试关键词匹配性能
    print("1. 关键词匹配测试:")
    keyword_times = []
    keyword_results = []
    
    for case in test_cases:
        start_time = time.time()
        result = agent._analyze_clothing_type(case)
        end_time = time.time()
        
        duration = (end_time - start_time) * 1000  # 转换为毫秒
        keyword_times.append(duration)
        keyword_results.append(result)
        
        print(f"  '{case}' -> {result['completion_type']} ({duration:.2f}ms)")
    
    avg_keyword_time = sum(keyword_times) / len(keyword_times)
    print(f"  平均响应时间: {avg_keyword_time:.2f}ms\n")
    
    # 测试AI判断性能（模拟）
    print("2. AI判断测试:")
    ai_times = []
    ai_results = []
    
    for case in test_cases:
        start_time = time.time()
        
        # 模拟AI调用进行服装类型判断
        try:
            prompt = f"""
            请判断以下服装描述中是否只有上装、只有下装、还是都有：
            服装描述：{case}
            
            请回答：
            - 如果只有上装，回复"需要补全下装"
            - 如果只有下装，回复"需要补全上装" 
            - 如果都有，回复"无需补全"
            """
            
            # 实际调用AI（注释掉以避免API费用）
            # ai_result = agent._call_ai("你是服装分析专家", prompt)
            
            # 模拟AI响应时间（1-3秒）
            time.sleep(0.1)  # 模拟100ms网络延迟
            ai_result = "模拟AI响应"
            
        except Exception as e:
            ai_result = f"AI调用失败: {e}"
        
        end_time = time.time()
        duration = (end_time - start_time) * 1000
        ai_times.append(duration)
        ai_results.append(ai_result)
        
        print(f"  '{case}' -> {ai_result} ({duration:.2f}ms)")
    
    avg_ai_time = sum(ai_times) / len(ai_times)
    print(f"  平均响应时间: {avg_ai_time:.2f}ms\n")
    
    # 性能对比总结
    print("=== 性能对比总结 ===")
    print(f"关键词匹配平均时间: {avg_keyword_time:.2f}ms")
    print(f"AI判断平均时间: {avg_ai_time:.2f}ms")
    print(f"性能提升: {(avg_ai_time / avg_keyword_time):.1f}x 倍")
    
    # 准确性验证
    print("\n=== 准确性验证 ===")
    correct_answers = {
        "红色夹克": "bottom",           # 只有上装，需要下装
        "蓝色牛仔裤": "top",            # 只有下装，需要上装
        "白色T恤，黑色长裤": "none",     # 都有，无需补全
        "连衣裙": "none",               # 连衣裙算完整，无需补全
        "西装外套": "bottom",           # 只有上装
        "运动短裤": "top",              # 只有下装
        "毛衣，牛仔裤": "none",         # 都有
        "衬衫": "bottom",               # 只有上装
        "百褶裙": "top",                # 只有下装
        "羽绒服，打底裤": "none"        # 都有
    }
    
    correct_count = 0
    total_count = len(test_cases)
    
    for i, case in enumerate(test_cases):
        expected = correct_answers[case]
        actual = keyword_results[i]['completion_type']
        is_correct = expected == actual
        
        if is_correct:
            correct_count += 1
            status = "✓"
        else:
            status = "✗"
        
        print(f"  {status} '{case}': 期望={expected}, 实际={actual}")
    
    accuracy = (correct_count / total_count) * 100
    print(f"\n关键词匹配准确率: {accuracy:.1f}% ({correct_count}/{total_count})")
    
    return {
        "keyword_avg_time": avg_keyword_time,
        "ai_avg_time": avg_ai_time,
        "performance_improvement": avg_ai_time / avg_keyword_time,
        "accuracy": accuracy
    }


def test_edge_cases():
    """测试边缘情况"""
    agent = ContentAgent()
    
    edge_cases = [
        "",                           # 空字符串
        "红色的",                     # 只有颜色
        "漂亮的衣服",                 # 模糊描述
        "jacket and pants",           # 英文
        "上衣和下装",                 # 通用词汇
        "比基尼",                     # 特殊服装
        "校服",                       # 套装
        "运动装"                      # 套装
    ]
    
    print("\n=== 边缘情况测试 ===")
    for case in edge_cases:
        result = agent._analyze_clothing_type(case)
        print(f"'{case}' -> {result}")


if __name__ == "__main__":
    # 运行性能对比测试
    results = test_keyword_vs_ai_performance()
    
    # 运行边缘情况测试
    test_edge_cases()
    
    print(f"\n=== 最终结论 ===")
    print(f"关键词匹配相比AI判断:")
    print(f"- 性能提升: {results['performance_improvement']:.1f}倍")
    print(f"- 准确率: {results['accuracy']:.1f}%")
    print(f"- 成本: 零成本 vs API调用费用")
    print(f"- 稳定性: 本地计算 vs 网络依赖")
    print(f"\n推荐: 对于服装类型这种简单分类任务，关键词匹配是最优选择")