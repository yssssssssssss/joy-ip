#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Gate 检查执行次数
验证 Gate 检查只在最终展示前执行一次（final_gate_check）
各步骤（clothes/hands/hats）不再执行 Gate 检查
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置环境变量启用 Gate 检查
os.environ["ENABLE_GATE_CHECK"] = "1"
os.environ["GATE_CHECK_SCOPE"] = "all"


class GateCheckCounter:
    """用于统计 Gate 检查调用次数的 Mock 类"""
    
    def __init__(self):
        self.call_count = 0
        self.checked_images = []
    
    def analyze_image_with_three_models(self, image_path: str):
        """模拟 Gate 检查，记录调用次数"""
        self.call_count += 1
        self.checked_images.append(image_path)
        print(f"  [Mock Gate] 第 {self.call_count} 次检查: {image_path}")
        # 模拟：奇数次通过，偶数次不通过
        is_pass = (self.call_count % 2 == 1)
        return is_pass, {"mock": "result"}


class MockBananaModule:
    """模拟 banana-* 模块"""
    
    def __init__(self, name: str):
        self.name = name
        self.call_count = 0
    
    def generate_image_with_accessories(self, image_path: str, info: str):
        self.call_count += 1
        # 返回模拟的输出路径
        return f"output/mock_{self.name}_{self.call_count}.png"


def test_step_no_gate_check():
    """测试各步骤不再执行 Gate 检查"""
    
    import importlib
    import generation_controller
    importlib.reload(generation_controller)
    
    from generation_controller import GenerationController, ENABLE_GATE_CHECK, GATE_CHECK_SCOPE
    
    print("=" * 60)
    print("测试1: 各步骤不再执行 Gate 检查")
    print("=" * 60)
    print(f"ENABLE_GATE_CHECK: {ENABLE_GATE_CHECK}")
    print(f"GATE_CHECK_SCOPE: {GATE_CHECK_SCOPE}")
    print("-" * 60)
    
    controller = GenerationController()
    
    # 替换为 Mock 对象
    gate_counter = GateCheckCounter()
    mock_clothes = MockBananaModule("clothes")
    mock_hands = MockBananaModule("hands")
    mock_hats = MockBananaModule("hats")
    
    controller.gate_check = gate_counter
    controller.banana_clothes = mock_clothes
    controller.banana_hands = mock_hands
    controller.banana_hats = mock_hats
    
    input_images = ["output/test_1.png", "output/test_2.png"]
    
    print(f"\n输入图片数量: {len(input_images)}")
    
    # 测试 process_clothes
    print("\n--- 执行 process_clothes ---")
    result1 = controller.process_clothes(input_images, "红色上衣", "output")
    clothes_gate_count = gate_counter.call_count
    print(f"process_clothes 后 Gate 检查次数: {clothes_gate_count}")
    
    # 测试 process_hands
    print("\n--- 执行 process_hands ---")
    result2 = controller.process_hands(result1, "气球", "output")
    hands_gate_count = gate_counter.call_count - clothes_gate_count
    print(f"process_hands 后 Gate 检查次数: {hands_gate_count}")
    
    # 测试 process_hats
    print("\n--- 执行 process_hats ---")
    result3 = controller.process_hats(result2, "圣诞帽", "output")
    hats_gate_count = gate_counter.call_count - clothes_gate_count - hands_gate_count
    print(f"process_hats 后 Gate 检查次数: {hats_gate_count}")
    
    print("-" * 60)
    print("\n测试结果:")
    print(f"  总 Gate 检查次数: {gate_counter.call_count}")
    print(f"  clothes 步骤检查次数: {clothes_gate_count}")
    print(f"  hands 步骤检查次数: {hands_gate_count}")
    print(f"  hats 步骤检查次数: {hats_gate_count}")
    
    # 验证：各步骤都不应该执行 Gate 检查
    all_zero = (clothes_gate_count == 0 and hands_gate_count == 0 and hats_gate_count == 0)
    
    if all_zero:
        print("  ✅ 各步骤均未执行 Gate 检查")
    else:
        print("  ❌ 某些步骤仍在执行 Gate 检查")
    
    return all_zero


def test_final_gate_check():
    """测试最终 Gate 检查"""
    
    import importlib
    import generation_controller
    importlib.reload(generation_controller)
    
    from generation_controller import GenerationController, ENABLE_GATE_CHECK
    
    print("\n" + "=" * 60)
    print("测试2: 最终 Gate 检查 (final_gate_check)")
    print("=" * 60)
    print(f"ENABLE_GATE_CHECK: {ENABLE_GATE_CHECK}")
    print("-" * 60)
    
    controller = GenerationController()
    
    gate_counter = GateCheckCounter()
    controller.gate_check = gate_counter
    
    input_images = [
        "output/final_1.png",
        "output/final_2.png",
        "output/final_3.png",
        "output/final_4.png",
    ]
    
    print(f"\n输入图片数量: {len(input_images)}")
    print("执行 final_gate_check...")
    print("-" * 60)
    
    result_images = controller.final_gate_check(input_images)
    
    print("-" * 60)
    print("\n测试结果:")
    print(f"  输入图片数: {len(input_images)}")
    print(f"  Gate 检查次数: {gate_counter.call_count}")
    print(f"  输出图片数: {len(result_images)}")
    print(f"  检查的图片: {gate_counter.checked_images}")
    print(f"  输出的图片: {result_images}")
    
    # 验证
    print("\n验证:")
    
    # 1. Gate 检查次数应该等于输入图片数
    expected_count = len(input_images)
    count_ok = (gate_counter.call_count == expected_count)
    if count_ok:
        print(f"  ✅ Gate 检查次数正确: {gate_counter.call_count} == {expected_count}")
    else:
        print(f"  ❌ Gate 检查次数错误: {gate_counter.call_count} != {expected_count}")
    
    # 2. 不通过的图片不应该出现在结果中
    # Mock 中奇数次通过，偶数次不通过，所以应该有 2 张图片通过
    expected_pass = 2  # 第1、3次通过
    filter_ok = (len(result_images) == expected_pass)
    if filter_ok:
        print(f"  ✅ 输出图片数正确: {len(result_images)} == {expected_pass} (不通过的已过滤)")
    else:
        print(f"  ❌ 输出图片数错误: {len(result_images)} != {expected_pass}")
    
    return count_ok and filter_ok


def test_gate_disabled():
    """测试 Gate 检查关闭时的行为"""
    
    os.environ["ENABLE_GATE_CHECK"] = "0"
    
    import importlib
    import generation_controller
    importlib.reload(generation_controller)
    
    from generation_controller import GenerationController, ENABLE_GATE_CHECK
    
    print("\n" + "=" * 60)
    print("测试3: Gate 检查关闭")
    print("=" * 60)
    print(f"ENABLE_GATE_CHECK: {ENABLE_GATE_CHECK}")
    print("-" * 60)
    
    controller = GenerationController()
    
    gate_counter = GateCheckCounter()
    controller.gate_check = gate_counter
    
    input_images = ["output/test_1.png", "output/test_2.png"]
    
    result_images = controller.final_gate_check(input_images)
    
    print(f"\n测试结果:")
    print(f"  Gate 检查次数: {gate_counter.call_count}")
    print(f"  输出图片数: {len(result_images)}")
    
    # 验证：Gate 关闭时不应该执行检查，所有图片都应该通过
    skip_ok = (gate_counter.call_count == 0)
    all_pass = (len(result_images) == len(input_images))
    
    if skip_ok:
        print("  ✅ Gate 检查已跳过（关闭状态）")
    else:
        print("  ❌ Gate 检查不应该执行")
    
    if all_pass:
        print("  ✅ 所有图片都通过（未过滤）")
    else:
        print("  ❌ 图片不应该被过滤")
    
    # 恢复环境变量
    os.environ["ENABLE_GATE_CHECK"] = "1"
    
    return skip_ok and all_pass


if __name__ == "__main__":
    test1_pass = test_step_no_gate_check()
    test2_pass = test_final_gate_check()
    test3_pass = test_gate_disabled()
    
    print("\n" + "=" * 60)
    print("总结:")
    print(f"  测试1 (各步骤无Gate检查): {'✅ 通过' if test1_pass else '❌ 失败'}")
    print(f"  测试2 (最终Gate检查): {'✅ 通过' if test2_pass else '❌ 失败'}")
    print(f"  测试3 (Gate关闭): {'✅ 通过' if test3_pass else '❌ 失败'}")
    print("=" * 60)
