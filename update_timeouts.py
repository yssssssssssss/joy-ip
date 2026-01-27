#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量更新项目中的 timeout 设置为 600 秒（10分钟）
"""

import re
import os
from pathlib import Path

# 需要修改的文件列表
FILES_TO_UPDATE = [
    "matchers/base_matcher.py",
    "matchers/head_matcher.py",
    "utils/image_uploader.py",
    "utils/ai_client.py",
    "generation_controller.py",
    "utils/async_api.py",
    "generation_controller_2d.py",
    "gate-result.py",
    "banana-pro-img-jd.py",
    "content_agent_2d.py",
]

# timeout 替换规则
TIMEOUT_REPLACEMENTS = [
    (r'(timeout\s*=\s*)(30|60|120)\b', r'\g<1>600'),
]


def update_file(filepath):
    """更新单个文件的 timeout 设置"""
    if not os.path.exists(filepath):
        print(f"⚠️  文件不存在: {filepath}")
        return False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = 0
        
        # 应用所有替换规则
        for pattern, replacement in TIMEOUT_REPLACEMENTS:
            matches = re.findall(pattern, content)
            if matches:
                content = re.sub(pattern, replacement, content)
                changes_made += len(matches)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ {filepath}: 更新了 {changes_made} 处 timeout")
            return True
        else:
            print(f"⏭️  {filepath}: 无需更新")
            return False
            
    except Exception as e:
        print(f"❌ {filepath}: 更新失败 - {e}")
        return False


def main():
    """主函数"""
    print("\n🔧 开始批量更新 timeout 设置...\n")
    
    updated_count = 0
    skipped_count = 0
    failed_count = 0
    
    for filepath in FILES_TO_UPDATE:
        result = update_file(filepath)
        if result is True:
            updated_count += 1
        elif result is False:
            skipped_count += 1
        else:
            failed_count += 1
    
    print("\n" + "=" * 60)
    print("📊 更新统计:")
    print(f"  ✅ 已更新: {updated_count} 个文件")
    print(f"  ⏭️  跳过: {skipped_count} 个文件")
    print(f"  ❌ 失败: {failed_count} 个文件")
    print("=" * 60)
    print("\n✨ 所有 timeout 已更新为 600 秒（10分钟）\n")


if __name__ == "__main__":
    main()
