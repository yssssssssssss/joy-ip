#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片生成流程控制器
负责协调整个图片生成流程：
1. 调用per-data.py生成基础图片
2. 依次处理服装、手拿、头戴
3. 每步都进行gate检查
4. 失败则重试
"""

import os
import importlib.util
import sys
from typing import List, Dict, Optional
from pathlib import Path
import re
from content_agent import ContentAgent

# ==========================
# Gate 检查开关与范围（集中控制）
# ==========================
# - ENABLE_GATE_CHECK: 是否开启 gate-result.py 检查（默认关闭）
#   设置为 1 或 true 开启；其他值关闭
# - GATE_CHECK_SCOPE: 检查范围，支持：
#   - 'hats' 仅在头戴步骤进行检查（默认）
#   - 'all'  在服装、手拿、头戴、背景步骤都进行检查
#   - 'none' 不进行任何 gate 检查（等价于关闭）
ENABLE_GATE_CHECK = str(os.environ.get("ENABLE_GATE_CHECK", "1")).strip().lower() in ("1", "true")
GATE_CHECK_SCOPE = str(os.environ.get("GATE_CHECK_SCOPE", "hats")).strip().lower()


class GenerationController:
    """图片生成流程控制器"""
    
    def __init__(self):
        """初始化控制器"""
        self.max_retries = 1  # 最大重试次数
        
        # 初始化内容合规检查器
        self.content_agent = ContentAgent()
        
        # 动态加载模块
        self._load_modules()
    
    def _load_modules(self):
        """动态加载所需的Python模块"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 加载banana模块
        modules = {
            'banana_clothes': 'banana-clothes.py',
            'banana_hands': 'banana-hands.py',
            'banana_hats': 'banana-hats.py',
            'banana_background': 'banana-background.py',
            'gate_check': 'gate-result.py',
            'per_data': 'per-data.py'
        }
        
        for module_name, file_name in modules.items():
            module_path = os.path.join(base_dir, file_name)
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                setattr(self, module_name, module)
            else:
                print(f"警告：无法加载模块 {file_name}")
                setattr(self, module_name, None)

        # 根据开关控制 gate-result.py 的使用：关闭则不使用该模块
        if not ENABLE_GATE_CHECK or GATE_CHECK_SCOPE == 'none':
            if hasattr(self, 'gate_check'):
                self.gate_check = None
            print("Gate检查已禁用（ENABLE_GATE_CHECK=0 或 GATE_CHECK_SCOPE=none），跳过使用 gate-result.py")

    
    def generate_step1_images(self, head_matches: List[Dict], body_matches: List[Dict], 
                             output_dir: str = "output") -> List[str]:
        """
        步骤1：使用per-data.py生成基础组合图片
        
        Args:
            head_matches: 头像匹配结果列表
            body_matches: 身体匹配结果列表
            output_dir: 输出目录
            
        Returns:
            List[str]: 生成的图片路径列表
        """
        print("\n=== 步骤1: 生成基础组合图片 ===")
        
        if not self.per_data:
            print("错误：per-data模块未加载")
            return []
        
        generated_images = []
        os.makedirs(output_dir, exist_ok=True)
        
        # 遍历所有body和head的组合
        for i, body_match in enumerate(body_matches):
            for j, head_match in enumerate(head_matches):
                body_path = body_match.get('image_path')
                head_path = head_match.get('image_path')
                
                if not body_path or not head_path:
                    continue
                
                # 生成输出路径
                import time
                timestamp = int(time.time() * 1000)
                output_path = os.path.join(output_dir, f"step1_{timestamp}_{i}_{j}.png")
                
                try:
                    # 调用per-data.py的compose_images_new_logic函数
                    result = self.per_data.compose_images_new_logic(
                        body_path, head_path, output_path
                    )
                    
                    if result and os.path.exists(output_path):
                        print(f"✓ 成功生成图片: {output_path}")
                        generated_images.append(output_path)
                    elif isinstance(result, str) and os.path.exists(result):
                        print(f"✓ 成功生成图片: {result}")
                        generated_images.append(result)
                    else:
                        print(f"✗ 生成图片失败: body={body_path}, head={head_path}")
                        
                except Exception as e:
                    print(f"✗ 生成图片时发生错误: {str(e)}")
        
        print(f"步骤1完成，共生成 {len(generated_images)} 张图片")
        return generated_images
    
    def check_image_quality(self, image_path: str, check_type: str) -> bool:
        """
        检查图片质量
        - 按集中开关与范围决定是否进行 gate 检查
        - 当关闭或不在范围内时，直接通过检查
        
        Args:
            image_path: 图片路径
            check_type: 检查类型 ('clothes', 'hands', 'hats', 'background')
            
        Returns:
            bool: 是否通过检查
        """
        print(f"检查图片质量: {image_path} (类型: {check_type})")

        # 若开关关闭或范围为 none：所有类型直接通过
        if not ENABLE_GATE_CHECK or GATE_CHECK_SCOPE == 'none':
            print(f"✓ {check_type} 类型图片直接通过检查（Gate检查关闭）")
            return True

        # 计算检查范围
        if GATE_CHECK_SCOPE == 'all':
            scope_types = ['clothes', 'hands', 'hats', 'background']
        else:  # 默认或 'hats'
            scope_types = ['hats']

        # 在范围内且 gate 模块可用时进行检查
        if check_type in scope_types and getattr(self, 'gate_check', None):
            try:
                print(f"使用 Gate 模块检查图片: {image_path}")
                # 仅使用 gate-result.py 的统一接口
                if hasattr(self.gate_check, 'analyze_image_with_three_models'):
                    ok, analysis_results = self.gate_check.analyze_image_with_three_models(image_path)
                    print(f"Gate检查结果: {'正常' if ok else '异常'}")
                    if not ok:
                        # 可选：简单打印一个模型摘要，避免过长日志
                        try:
                            models = list(analysis_results.keys())
                            print(f"异常详情模型摘要: {', '.join(models[:3])} ...")
                        except Exception:
                            pass
                    return bool(ok)
                else:
                    print("Gate模块未提供 analyze_image_with_three_models，跳过检查")
                    return True

            except Exception as e:
                print(f"Gate检查过程中发生错误: {str(e)}")
                # 检查失败时，为了安全起见，返回False
                return False

        # 不在范围内或 gate 模块不可用：直接通过
        print(f"✓ {check_type} 类型图片直接通过检查（未启用Gate或不在范围）")
        return True
    
    def process_clothes(self, image_paths: List[str], clothes_info: str, 
                       output_dir: str = "output") -> List[str]:
        """
        步骤4: 处理服装
        
        Args:
            image_paths: 输入图片路径列表
            clothes_info: 服装信息
            output_dir: 输出目录
            
        Returns:
            List[str]: 处理后的图片路径列表
        """
        if not clothes_info:
            print("跳过服装处理（无服装信息）")
            return image_paths
        
        print(f"\n=== 步骤4: 处理服装 (信息: {clothes_info}) ===")
        
        if not self.banana_clothes:
            print("错误：banana-clothes模块未加载")
            return image_paths
        
        processed_images = []
        
        for image_path in image_paths:
            try:
                # 调用banana-clothes生成图片
                result_url = self.banana_clothes.generate_image_with_accessories(
                    image_path, clothes_info
                )
                
                if result_url:
                    # 转换URL为本地路径
                    if result_url.startswith('/'):
                        result_path = result_url.lstrip('/')
                    else:
                        result_path = result_url
                    
                    print(f"✓ 成功处理服装: {result_path}")
                    processed_images.append(result_path)
                else:
                    print(f"✗ 生成服装图片失败: {image_path}")
                    # 失败时保留原图片
                    processed_images.append(image_path)
                    
            except Exception as e:
                print(f"✗ 处理服装时发生错误: {str(e)}")
                # 失败时保留原图片
                processed_images.append(image_path)
        
        return processed_images
    
    def process_hands(self, image_paths: List[str], hands_info: str, 
                     output_dir: str = "output") -> List[str]:
        """
        步骤6: 处理手拿物品
        
        Args:
            image_paths: 输入图片路径列表
            hands_info: 手拿物品信息
            output_dir: 输出目录
            
        Returns:
            List[str]: 处理后的图片路径列表
        """
        # 规范化与健壮性校验，避免误把“头戴”传入手拿
        if not hands_info:
            print("跳过手拿处理（无手拿信息）")
            return image_paths
        info = hands_info.strip()
        if not info or info in {"无", "没有", "未提供", "不拿"}:
            print("跳过手拿处理（无效或否定的手拿信息）")
            return image_paths
        # 若出现交叉标签或仅标签文本，直接跳过
        if "头戴" in info or re.fullmatch(r"头戴[：:]?\s*", info):
            print("跳过手拿处理（检测到误传的头戴信息）")
            return image_paths

        print(f"\n=== 步骤6: 处理手拿物品 (信息: {info}) ===", flush=True)
        
        if not self.banana_hands:
            print("错误：banana-hands模块未加载", flush=True)
            return image_paths
        
        processed_images = []
        total_images = len(image_paths)
        
        for idx, image_path in enumerate(image_paths):
            print(f"[手拿处理] 处理图片 [{idx+1}/{total_images}]: {image_path}", flush=True)
            try:
                # 调用banana-hands生成图片
                print(f"[手拿处理] 调用 banana_hands.generate_image_with_accessories...", flush=True)
                result_url = self.banana_hands.generate_image_with_accessories(
                    image_path, info
                )
                print(f"[手拿处理] 返回结果: {result_url}", flush=True)
                
                if result_url:
                    # 转换URL为本地路径
                    if result_url.startswith('/'):
                        result_path = result_url.lstrip('/')
                    else:
                        result_path = result_url
                    
                    print(f"✓ 成功处理手拿物品: {result_path}", flush=True)
                    processed_images.append(result_path)
                else:
                    print(f"✗ 生成手拿图片失败: {image_path}", flush=True)
                    # 失败时保留原图片
                    processed_images.append(image_path)
                    
            except Exception as e:
                import traceback
                print(f"✗ 处理手拿物品时发生错误: {str(e)}", flush=True)
                print(f"[手拿处理] 错误堆栈: {traceback.format_exc()}", flush=True)
                # 失败时保留原图片
                processed_images.append(image_path)
        
        print(f"[手拿处理] 完成，处理了 {len(processed_images)} 张图片", flush=True)
        return processed_images
    
    def process_hats(self, image_paths: List[str], hats_info: str, 
                    output_dir: str = "output") -> List[str]:
        """
        步骤8: 处理头戴物品
        
        Args:
            image_paths: 输入图片路径列表
            hats_info: 头戴物品信息
            output_dir: 输出目录
            
        Returns:
            List[str]: 处理后的图片路径列表
        """
        if not hats_info:
            print("跳过头戴处理（无头戴信息）")
            return image_paths
        
        print(f"\n=== 步骤8: 处理头戴物品 (信息: {hats_info}) ===")
        
        if not self.banana_hats:
            print("错误：banana-hats模块未加载")
            return image_paths
        
        processed_images = []
        
        for image_path in image_paths:
            try:
                # 调用banana-hats生成图片
                result_url = self.banana_hats.generate_image_with_accessories(
                    image_path, hats_info
                )
                
                if result_url:
                    # 转换URL为本地路径
                    if result_url.startswith('/'):
                        result_path = result_url.lstrip('/')
                    else:
                        result_path = result_url
                    
                    print(f"✓ 成功处理头戴物品: {result_path}")
                    processed_images.append(result_path)
                else:
                    print(f"✗ 生成头戴图片失败: {image_path}")
                    # 失败时保留原图片
                    processed_images.append(image_path)
                    
            except Exception as e:
                print(f"✗ 处理头戴物品时发生错误: {str(e)}")
                # 失败时保留原图片
                processed_images.append(image_path)
        
        print(f"头戴处理完成，生成图片数: {len(processed_images)}")
        return processed_images
    
    def process_background(self, image_paths: List[str], background_info: str, 
                          output_dir: str = "output") -> List[str]:
        """
        步骤10: 处理背景
        
        Args:
            image_paths: 输入图片路径列表
            background_info: 背景信息
            output_dir: 输出目录
            
        Returns:
            List[str]: 处理后的图片路径列表
        """
        if not background_info:
            print("跳过背景处理（无背景信息）")
            return image_paths
        
        print(f"\n=== 步骤10: 处理背景 (信息: {background_info}) ===")
        
        if not self.banana_background:
            print("错误：banana-background模块未加载")
            return image_paths
        
        processed_images = []
        
        for image_path in image_paths:
            try:
                # 调用banana-background生成图片
                result_url = self.banana_background.generate_image_with_accessories(
                    image_path, background_info
                )
                
                if result_url:
                    # 转换URL为本地路径
                    if result_url.startswith('/'):
                        result_path = result_url.lstrip('/')
                    else:
                        result_path = result_url
                    
                    print(f"✓ 成功处理背景: {result_path}")
                    processed_images.append(result_path)
                else:
                    print(f"✗ 生成背景图片失败: {image_path}")
                    # 失败时保留原图片
                    processed_images.append(image_path)
                    
            except Exception as e:
                print(f"✗ 处理背景时发生错误: {str(e)}")
                # 失败时保留原图片
                processed_images.append(image_path)
        
        return processed_images
    
    def check_content_compliance(self, analysis: Dict[str, str]) -> bool:
        """
        检查生成内容是否合规
        
        Args:
            analysis: 内容分析结果
            
        Returns:
            bool: 是否合规
        """
        print("\n=== 内容合规检查 ===")
        
        # 组合所有内容进行检查
        content_parts = []
        for key, value in analysis.items():
            if value and key != '_raw_ai':  # 排除内部字段
                content_parts.append(f"{key}: {value}")
        
        full_content = ", ".join(content_parts)
        print(f"检查内容: {full_content}")
        
        try:
            is_compliant, reason = self.content_agent.check_compliance(full_content)
            if not is_compliant:
                print(f"✗ 内容不合规: {reason}")
                return False
            else:
                print("✓ 内容合规检查通过")
                return True
        except Exception as e:
            print(f"✗ 合规检查失败: {str(e)}")
            # 检查失败时为安全起见返回False
            return False

    def generate_complete_flow(self, head_matches: List[Dict], body_matches: List[Dict],
                              analysis: Dict[str, str], output_dir: str = "output") -> List[str]:
        """
        完整的图片生成流程
        
        Args:
            head_matches: 头像匹配结果
            body_matches: 身体匹配结果
            analysis: 内容分析结果（包含服装、手拿、头戴等信息）
            output_dir: 输出目录
            
        Returns:
            List[str]: 最终生成的图片路径列表
        """
        print("\n" + "="*60)
        print("开始完整图片生成流程")
        print("="*60)
        
        # 步骤0: 内容合规检查
        if not self.check_content_compliance(analysis):
            print("错误：内容不合规，终止生成流程")
            return []
        
        # 步骤1-3: 生成基础图片
        images = self.generate_step1_images(head_matches, body_matches, output_dir)
        
        if not images:
            print("错误：未能生成基础图片")
            return []
        
        # 步骤4-5: 处理服装
        if analysis.get('服装'):
            images = self.process_clothes(images, analysis['服装'], output_dir)
        
        # 步骤6-7: 处理手拿
        if analysis.get('手拿'):
            images = self.process_hands(images, analysis['手拿'], output_dir)
        
        # 步骤8-9: 处理头戴
        if analysis.get('头戴'):
            images = self.process_hats(images, analysis['头戴'], output_dir)
            try:
                print(f"头戴阶段返回图片数: {len(images)}")
                print(f"头戴阶段返回图片列表: {images}")
            except Exception:
                pass
        
        # 步骤10-11: 处理背景（暂时禁用，但保留接口）
        # if analysis.get('背景'):
        #     images = self.process_background(images, analysis['背景'], output_dir)
        
        # 最终 Gate 检查：在展示前对所有图片进行质量检查
        images = self.final_gate_check(images)
        
        print("\n" + "="*60)
        print(f"图片生成流程完成！共生成 {len(images)} 张图片")
        print("="*60)
        
        return images
    
    def final_gate_check(self, image_paths: List[str]) -> List[str]:
        """
        最终 Gate 检查：在图片展示到页面前进行统一质量检查
        
        Args:
            image_paths: 待检查的图片路径列表
            
        Returns:
            List[str]: 通过检查的图片路径列表
        """
        import sys
        
        def _log(msg: str):
            """带前缀的日志输出，确保立即刷新"""
            print(f"[FinalGate] {msg}", flush=True)
            sys.stdout.flush()
        
        # 若 Gate 检查关闭，直接返回所有图片
        if not ENABLE_GATE_CHECK or GATE_CHECK_SCOPE == 'none':
            _log("已跳过（开关关闭）")
            return image_paths
        
        if not image_paths:
            return []
        
        _log(f"开始检查 {len(image_paths)} 张图片")
        
        # 检查 gate 模块是否可用
        if not getattr(self, 'gate_check', None):
            _log("Gate 模块不可用，跳过检查")
            return image_paths
        
        if not hasattr(self.gate_check, 'analyze_image_with_three_models'):
            _log("Gate 模块未提供 analyze_image_with_three_models，跳过检查")
            return image_paths
        
        passed_images = []
        
        for i, image_path in enumerate(image_paths):
            _log(f"检查图片 [{i+1}/{len(image_paths)}]: {image_path}")
            try:
                ok, analysis_results = self.gate_check.analyze_image_with_three_models(image_path)
                if ok:
                    _log(f"  ✅ 通过检查")
                    passed_images.append(image_path)
                else:
                    _log(f"  ❌ 未通过检查，不展示该图片")
                    try:
                        models = list(analysis_results.keys())
                        _log(f"    异常模型: {', '.join(models[:3])}")
                    except Exception:
                        pass
            except Exception as e:
                _log(f"  ❌ 检查过程出错: {str(e)}，不展示该图片")
        
        _log(f"检查完成: {len(passed_images)}/{len(image_paths)} 张图片通过")
        return passed_images


if __name__ == "__main__":
    # 测试代码
    controller = GenerationController()
    
    # 模拟测试数据
    head_matches = [
        {'image_path': 'data/joy_head/test1.png'},
        {'image_path': 'data/joy_head/test2.png'}
    ]
    
    body_matches = [
        {'image_path': 'data/joy_body_noface/test1.png'},
        {'image_path': 'data/joy_body_noface/test2.png'}
    ]
    
    analysis = {
        '表情': '开心',
        '动作': '站姿',
        '服装': '红色上衣',
        '手拿': '气球',
        '头戴': '帽子',
        '背景': '公园'
    }
    
    # 执行完整流程
    # result = controller.generate_complete_flow(head_matches, body_matches, analysis)
    # print(f"最终生成的图片: {result}")

