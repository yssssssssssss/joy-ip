#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时日志监控脚本
用于监控后台运行日志
"""

import os
import time
import sys
from datetime import datetime

def monitor_logs(log_file="logs/app.log", lines=50):
    """
    实时监控日志文件
    
    Args:
        log_file: 日志文件路径
        lines: 显示的行数
    """
    if not os.path.exists(log_file):
        print(f"❌ 日志文件不存在: {log_file}")
        return
    
    print(f"📊 开始监控日志文件: {log_file}")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        # 获取文件初始大小
        with open(log_file, 'r', encoding='utf-8') as f:
            f.seek(0, 2)  # 移动到文件末尾
            file_size = f.tell()
        
        # 显示最后几行
        print(f"📋 显示最后 {lines} 行日志:")
        print("-" * 80)
        os.system(f"tail -n {lines} {log_file}")
        print("-" * 80)
        print("🔄 开始实时监控 (按 Ctrl+C 退出)...")
        print()
        
        # 实时监控新增内容
        with open(log_file, 'r', encoding='utf-8') as f:
            f.seek(file_size)  # 从当前位置开始读取
            
            while True:
                line = f.readline()
                if line:
                    # 添加时间戳和颜色
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"[{timestamp}] {line.rstrip()}")
                    sys.stdout.flush()
                else:
                    time.sleep(0.1)  # 短暂休眠
                    
    except KeyboardInterrupt:
        print(f"\n⏹️  监控已停止 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"❌ 监控出错: {str(e)}")

def show_log_summary():
    """显示日志摘要信息"""
    log_file = "logs/app.log"
    
    if not os.path.exists(log_file):
        print(f"❌ 日志文件不存在: {log_file}")
        return
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        file_size = os.path.getsize(log_file)
        
        # 统计不同类型的日志
        error_count = sum(1 for line in lines if '❌' in line or 'ERROR' in line or '✗' in line)
        success_count = sum(1 for line in lines if '✓' in line or 'SUCCESS' in line)
        request_count = sum(1 for line in lines if 'start_generate' in line)
        gate_count = sum(1 for line in lines if 'Gate检查' in line)
        
        print("📊 日志文件摘要")
        print("=" * 50)
        print(f"📁 文件路径: {log_file}")
        print(f"📏 文件大小: {file_size:,} 字节")
        print(f"📄 总行数: {total_lines:,} 行")
        print(f"🔴 错误数量: {error_count}")
        print(f"🟢 成功数量: {success_count}")
        print(f"📨 生成请求: {request_count}")
        print(f"🛡️  Gate检查: {gate_count}")
        
        # 显示最近的几条重要日志
        print("\n📋 最近的重要日志:")
        print("-" * 50)
        important_lines = []
        for line in lines[-100:]:  # 检查最后100行
            if any(keyword in line for keyword in ['start_generate', '✓ 成功', '❌', '✗', 'Gate检查结果']):
                important_lines.append(line.strip())
        
        for line in important_lines[-10:]:  # 显示最后10条重要日志
            print(f"  {line}")
            
    except Exception as e:
        print(f"❌ 读取日志摘要失败: {str(e)}")

def clear_logs():
    """清空日志文件"""
    log_file = "logs/app.log"
    
    try:
        if os.path.exists(log_file):
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("")
            print(f"🧹 日志文件已清空: {log_file}")
        else:
            print(f"❌ 日志文件不存在: {log_file}")
    except Exception as e:
        print(f"❌ 清空日志失败: {str(e)}")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("📖 日志监控工具使用说明:")
        print("=" * 50)
        print("python monitor_logs.py monitor [lines]  - 实时监控日志 (默认显示50行)")
        print("python monitor_logs.py summary          - 显示日志摘要")
        print("python monitor_logs.py clear            - 清空日志文件")
        print("python monitor_logs.py tail [lines]     - 显示最后几行日志")
        print()
        print("示例:")
        print("  python monitor_logs.py monitor 100    - 监控日志，显示最后100行")
        print("  python monitor_logs.py tail 20        - 显示最后20行日志")
        return
    
    command = sys.argv[1].lower()
    
    if command == "monitor":
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        monitor_logs(lines=lines)
    elif command == "summary":
        show_log_summary()
    elif command == "clear":
        clear_logs()
    elif command == "tail":
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        log_file = "logs/app.log"
        if os.path.exists(log_file):
            print(f"📋 显示最后 {lines} 行日志:")
            print("-" * 80)
            os.system(f"tail -n {lines} {log_file}")
        else:
            print(f"❌ 日志文件不存在: {log_file}")
    else:
        print(f"❌ 未知命令: {command}")

if __name__ == "__main__":
    main()