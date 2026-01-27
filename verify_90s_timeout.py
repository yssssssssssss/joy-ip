#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证90秒超时设置脚本
检查所有Python文件中的超时配置是否正确
"""

import os
import re
from pathlib import Path

def check_timeout_settings():
    """检查超时设置"""
    print("=" * 60)
    print("验证90秒超时设置")
    print("=" * 60)
    
    # 需要检查的文件列表
    files_to_check = [
        'utils/http_client.py',
        'content_agent.py',
        'banana-pro-img-jd.py',
        'matchers/base_matcher.py',
        'matchers/head_matcher.py',
        'generation_controller.py',
        'generation_controller_2d.py',
        'gate-result.py',
        'utils/ai_client.py',
        'utils/async_api.py',
        'utils/image_uploader.py',
    ]
    
    total_90s = 0
    total_600s = 0
    issues = []
    
    for filepath in files_to_check:
        if not os.path.exists(filepath):
            issues.append(f"❌ 文件不存在: {filepath}")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找timeout=90
        timeout_90_matches = re.findall(r'timeout\s*=\s*90', content)
        count_90 = len(timeout_90_matches)
        
        # 查找timeout=600（排除注释中的）
        timeout_600_matches = re.findall(r'timeout\s*=\s*600(?!\s*#)', content)
        count_600 = len(timeout_600_matches)
        
        if count_600 > 0:
            issues.append(f"⚠️  {filepath}: 发现 {count_600} 处 timeout=600（应该改为90）")
        
        if count_90 > 0:
            print(f"✅ {filepath}: {count_90} 处 timeout=90")
            total_90s += count_90
        
        total_600s += count_600
    
    print("\n" + "=" * 60)
    print("检查结果")
    print("=" * 60)
    print(f"✅ 找到 {total_90s} 处 timeout=90 设置")
    print(f"{'⚠️ ' if total_600s > 0 else '✅'} 找到 {total_600s} 处 timeout=600 设置")
    
    if issues:
        print("\n问题列表:")
        for issue in issues:
            print(f"  {issue}")
    
    # 检查前端配置
    print("\n" + "=" * 60)
    print("检查前端配置")
    print("=" * 60)
    
    frontend_file = 'frontend/src/components/ChatInterface.tsx'
    if os.path.exists(frontend_file):
        with open(frontend_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找timeout: 0
        timeout_0_matches = re.findall(r'timeout:\s*0', content)
        count_0 = len(timeout_0_matches)
        
        if count_0 >= 5:  # 应该有5个API端点设置为timeout: 0
            print(f"✅ 前端: {count_0} 处 timeout: 0（无限等待）")
        else:
            print(f"⚠️  前端: 只找到 {count_0} 处 timeout: 0（预期至少5处）")
    else:
        print(f"❌ 前端文件不存在: {frontend_file}")
    
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    
    if total_600s == 0 and total_90s >= 20 and not issues:
        print("✅ 所有超时设置已正确配置！")
        print("   - 后端: 90秒超时（自动重连）")
        print("   - 前端: 无限等待（不会超时报错）")
        return True
    else:
        print("⚠️  发现配置问题，请检查上述问题列表")
        return False

if __name__ == "__main__":
    success = check_timeout_settings()
    exit(0 if success else 1)
