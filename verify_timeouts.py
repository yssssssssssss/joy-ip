#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证所有 timeout 设置是否已更新为 600 秒
"""

import re
import os

# 需要检查的文件
FILES_TO_CHECK = [
    "content_agent.py",
    "matchers/base_matcher.py",
    "matchers/head_matcher.py",
    "utils/image_uploader.py",
    "utils/ai_client.py",
    "generation_controller.py",
    "utils/async_api.py",
    "generation_controller_2d.py",
    "gate-result.py",
    "banana-pro-img-jd.py",
]

def check_file(filepath):
    """检查文件中的 timeout 设置"""
    if not os.path.exists(filepath):
        return None, []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 查找所有 timeout=数字 的模式
        timeout_values = []
        for line_num, line in enumerate(lines, 1):
            # 跳过注释行
            if line.strip().startswith('#'):
                continue
            # 查找 timeout=数字
            matches = re.findall(r'timeout\s*=\s*(\d+)', line)
            for match in matches:
                timeout_values.append(match)
        
        if not timeout_values:
            return "no_timeout", []
        
        # 检查是否所有 timeout 都是 600
        non_600 = [t for t in timeout_values if t != '600']
        
        if non_600:
            return "has_old", non_600
        else:
            return "all_600", timeout_values
            
    except Exception as e:
        return "error", [str(e)]


def main():
    """主函数"""
    print("\n🔍 验证 timeout 设置...\n")
    
    all_good = True
    total_600 = 0
    
    for filepath in FILES_TO_CHECK:
        status, values = check_file(filepath)
        
        if status == "all_600":
            print(f"✅ {filepath}: {len(values)} 处 timeout=600")
            total_600 += len(values)
        elif status == "has_old":
            print(f"❌ {filepath}: 发现旧的 timeout 值: {values}")
            all_good = False
        elif status == "no_timeout":
            print(f"⏭️  {filepath}: 无 timeout 设置")
        elif status is None:
            print(f"⚠️  {filepath}: 文件不存在")
        else:
            print(f"❌ {filepath}: 检查失败 - {values}")
            all_good = False
    
    print("\n" + "=" * 60)
    if all_good:
        print(f"✅ 验证通过！共 {total_600} 处 timeout 已设置为 600 秒")
    else:
        print("❌ 验证失败！仍有文件使用旧的 timeout 值")
    print("=" * 60 + "\n")
    
    return all_good


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
