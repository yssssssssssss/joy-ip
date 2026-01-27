#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 CLIP 模型是否正确安装和加载
"""

import os
import sys

def check_model_files():
    """检查模型文件是否存在"""
    print("=" * 60)
    print("检查模型文件...")
    print("=" * 60)
    
    base_path = "/data/joy-ip/models"
    
    # 检查 CLIP 模型
    clip_model_path = os.path.join(base_path, "clip-ViT-B-32")
    if os.path.exists(clip_model_path):
        size = os.popen(f"du -sh {clip_model_path}").read().split()[0]
        print(f"✅ CLIP 模型存在: {clip_model_path}")
        print(f"   大小: {size}")
    else:
        print(f"❌ CLIP 模型不存在: {clip_model_path}")
        return False
    
    # 检查分词器
    tokenizer_path = os.path.join(base_path, "clip-vit-base-patch32")
    if os.path.exists(tokenizer_path):
        size = os.popen(f"du -sh {tokenizer_path}").read().split()[0]
        print(f"✅ 分词器存在: {tokenizer_path}")
        print(f"   大小: {size}")
    else:
        print(f"⚠️  分词器不存在（可选）: {tokenizer_path}")
    
    print()
    return True


def test_model_loading():
    """测试模型加载"""
    print("=" * 60)
    print("测试模型加载...")
    print("=" * 60)
    
    try:
        from utils.clip_manager import get_clip_model, get_clip_tokenizer
        
        # 测试 CLIP 模型
        print("正在加载 CLIP 模型...")
        model = get_clip_model()
        print("✅ CLIP 模型加载成功")
        print(f"   模型类型: {type(model).__name__}")
        
        # 测试分词器
        print("\n正在加载分词器...")
        tokenizer = get_clip_tokenizer()
        if tokenizer:
            print("✅ 分词器加载成功")
            print(f"   分词器类型: {type(tokenizer).__name__}")
        else:
            print("⚠️  分词器加载失败（可选，不影响主要功能）")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_model_inference():
    """测试模型推理"""
    print("=" * 60)
    print("测试模型推理...")
    print("=" * 60)
    
    try:
        from utils.clip_manager import get_clip_model
        
        model = get_clip_model()
        
        # 测试文本编码
        test_texts = ["一个开心的joy", "穿着红色衣服的角色"]
        print(f"测试文本: {test_texts}")
        
        embeddings = model.encode(test_texts)
        print(f"✅ 文本编码成功")
        print(f"   输出形状: {embeddings.shape}")
        print(f"   输出类型: {type(embeddings)}")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ 模型推理失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n🔍 CLIP 模型验证工具\n")
    
    # 1. 检查文件
    if not check_model_files():
        print("\n❌ 模型文件检查失败")
        sys.exit(1)
    
    # 2. 测试加载
    if not test_model_loading():
        print("\n❌ 模型加载测试失败")
        sys.exit(1)
    
    # 3. 测试推理
    if not test_model_inference():
        print("\n❌ 模型推理测试失败")
        sys.exit(1)
    
    # 总结
    print("=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    print("\n模型路径:")
    print("  - CLIP 模型: /data/joy-ip/models/clip-ViT-B-32/")
    print("  - 分词器:    /data/joy-ip/models/clip-vit-base-patch32/")
    print("\n现在可以重启应用，系统将自动使用本地模型。")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
