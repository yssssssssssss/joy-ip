#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 gate-result.py 是否能被 generation_controller.py 正确加载和调用
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_gate_module_loading():
    """测试 gate-result.py 模块加载"""
    print("=" * 60)
    print("测试1: gate-result.py 模块加载")
    print("=" * 60)
    
    # 启用 Gate 检查
    os.environ["ENABLE_GATE_CHECK"] = "1"
    os.environ["GATE_CHECK_SCOPE"] = "all"
    
    import importlib
    import generation_controller
    importlib.reload(generation_controller)
    
    from generation_controller import GenerationController, ENABLE_GATE_CHECK, GATE_CHECK_SCOPE
    
    print(f"ENABLE_GATE_CHECK: {ENABLE_GATE_CHECK}")
    print(f"GATE_CHECK_SCOPE: {GATE_CHECK_SCOPE}")
    
    controller = GenerationController()
    
    # 检查 gate_check 模块是否加载
    gate_module = getattr(controller, 'gate_check', None)
    
    if gate_module is None:
        print("❌ gate_check 模块未加载")
        return False
    
    print(f"✅ gate_check 模块已加载: {gate_module}")
    
    # 检查关键函数是否存在
    if hasattr(gate_module, 'analyze_image_with_three_models'):
        print("✅ analyze_image_with_three_models 函数存在")
    else:
        print("❌ analyze_image_with_three_models 函数不存在")
        return False
    
    return True


def test_gate_function_signature():
    """测试 gate-result.py 函数签名"""
    print("\n" + "=" * 60)
    print("测试2: analyze_image_with_three_models 函数签名")
    print("=" * 60)
    
    os.environ["ENABLE_GATE_CHECK"] = "1"
    
    import importlib
    import generation_controller
    importlib.reload(generation_controller)
    
    from generation_controller import GenerationController
    
    controller = GenerationController()
    gate_module = getattr(controller, 'gate_check', None)
    
    if gate_module is None:
        print("❌ gate_check 模块未加载")
        return False
    
    func = getattr(gate_module, 'analyze_image_with_three_models', None)
    if func is None:
        print("❌ 函数不存在")
        return False
    
    import inspect
    sig = inspect.signature(func)
    print(f"函数签名: {func.__name__}{sig}")
    print(f"参数列表: {list(sig.parameters.keys())}")
    
    # 检查返回值类型（通过文档或注释）
    if func.__doc__:
        print(f"函数文档: {func.__doc__[:200]}...")
    
    return True


def test_gate_disabled():
    """测试 Gate 检查关闭时的行为"""
    print("\n" + "=" * 60)
    print("测试3: Gate 检查关闭时的行为")
    print("=" * 60)
    
    os.environ["ENABLE_GATE_CHECK"] = "0"
    
    import importlib
    import generation_controller
    importlib.reload(generation_controller)
    
    from generation_controller import GenerationController, ENABLE_GATE_CHECK
    
    print(f"ENABLE_GATE_CHECK: {ENABLE_GATE_CHECK}")
    
    controller = GenerationController()
    gate_module = getattr(controller, 'gate_check', None)
    
    if gate_module is None:
        print("✅ Gate 检查关闭时，gate_check 模块被设为 None（符合预期）")
        return True
    else:
        print("❌ Gate 检查关闭时，gate_check 模块不应该被加载")
        return False


def test_final_gate_check_flow():
    """测试 final_gate_check 流程"""
    print("\n" + "=" * 60)
    print("测试4: final_gate_check 流程（使用真实模块）")
    print("=" * 60)
    
    os.environ["ENABLE_GATE_CHECK"] = "1"
    os.environ["GATE_CHECK_SCOPE"] = "all"
    
    import importlib
    import generation_controller
    importlib.reload(generation_controller)
    
    from generation_controller import GenerationController
    
    controller = GenerationController()
    
    # 检查模块是否加载
    if not getattr(controller, 'gate_check', None):
        print("❌ gate_check 模块未加载")
        return False
    
    print("✅ gate_check 模块已加载")
    print(f"   模块路径: {controller.gate_check.__file__ if hasattr(controller.gate_check, '__file__') else 'N/A'}")
    
    # 检查函数
    if hasattr(controller.gate_check, 'analyze_image_with_three_models'):
        print("✅ analyze_image_with_three_models 函数可用")
    else:
        print("❌ analyze_image_with_three_models 函数不可用")
        return False
    
    # 测试空列表
    result = controller.final_gate_check([])
    print(f"空列表测试: {result}")
    
    return True


if __name__ == "__main__":
    results = []
    
    results.append(("模块加载", test_gate_module_loading()))
    results.append(("函数签名", test_gate_function_signature()))
    results.append(("Gate关闭", test_gate_disabled()))
    results.append(("流程测试", test_final_gate_check_flow()))
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + ("✅ 所有测试通过" if all_passed else "❌ 部分测试失败"))
