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
import sys
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import logging

from utils.module_loader import ModuleLoader
from content_agent import ContentAgent

logger = logging.getLogger(__name__)

# ==========================
# Gate 检查开关与范围（集中控制）
# ==========================
ENABLE_GATE_CHECK = str(os.environ.get("ENABLE_GATE_CHECK", "1")).strip().lower() in ("1", "true")
GATE_CHECK_SCOPE = str(os.environ.get("GATE_CHECK_SCOPE", "hats")).strip().lower()

# 并行处理配置
# 优化：默认启用2个并行worker（避免API限流），可通过环境变量覆盖
MAX_PARALLEL_WORKERS = int(os.environ.get("MAX_PARALLEL_WORKERS", "2"))

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
        # 使用统一的模块加载器
        modules = {
            'banana_unified': 'banana-pro-img-jd.py',  # 统一处理模块
            'banana_background': 'banana-background.py',
            'gate_check': 'gate-result.py',
            'per_data': 'per-data.py'
        }

        for attr_name, file_name in modules.items():
            module = ModuleLoader.load(file_name)
            if module:
                setattr(self, attr_name, module)
                logger.debug(f"成功加载模块: {file_name}")
            else:
                setattr(self, attr_name, None)
                logger.warning(f"无法加载模块: {file_name}")

        # 根据开关控制 gate-result.py 的使用
        if not ENABLE_GATE_CHECK or GATE_CHECK_SCOPE == 'none':
            self.gate_check = None
            logger.info("Gate检查已禁用")

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
        logger.info("=== 步骤1: 生成基础组合图片 ===")

        if not self.per_data:
            logger.error("per-data模块未加载")
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
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = os.path.join(output_dir, f"step1_{timestamp}_{i}_{j}.png")
                
                try:
                    # 调用per-data.py的compose_images_new_logic函数
                    result = self.per_data.compose_images_new_logic(
                        body_path, head_path, output_path
                    )
                    
                    if result and os.path.exists(output_path):
                        logger.info(f"成功生成图片: {output_path}")
                        generated_images.append(output_path)
                    elif isinstance(result, str) and os.path.exists(result):
                        logger.info(f"成功生成图片: {result}")
                        generated_images.append(result)
                    else:
                        logger.warning(f"生成图片失败: body={body_path}, head={head_path}")
                        
                except Exception as e:
                    logger.warning(f"生成图片时发生错误: {str(e)}")
        
        logger.info(f"步骤1完成，共生成 {len(generated_images)} 张图片")
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
        logger.info(f"检查图片质量: {image_path} (类型: {check_type})")

        # 若开关关闭或范围为 none：所有类型直接通过
        if not ENABLE_GATE_CHECK or GATE_CHECK_SCOPE == 'none':
            logger.info(f"{check_type} 类型图片直接通过检查（Gate检查关闭）")
            return True

        # 计算检查范围
        if GATE_CHECK_SCOPE == 'all':
            scope_types = ['clothes', 'hands', 'hats', 'background']
        else:  # 默认或 'hats'
            scope_types = ['hats']

        # 在范围内且 gate 模块可用时进行检查
        if check_type in scope_types and getattr(self, 'gate_check', None):
            try:
                logger.info(f"使用 Gate 模块检查图片: {image_path}")
                # 仅使用 gate-result.py 的统一接口
                if hasattr(self.gate_check, 'analyze_image_with_three_models'):
                    ok, analysis_results = self.gate_check.analyze_image_with_three_models(image_path)
                    logger.info(f"Gate检查结果: {'正常' if ok else '异常'}")
                    if not ok:
                        # 可选：简单打印一个模型摘要，避免过长日志
                        try:
                            models = list(analysis_results.keys())
                            logger.info(f"异常详情模型摘要: {', '.join(models[:3])} ...")
                        except Exception:
                            pass
                    return bool(ok)
                else:
                    logger.info("Gate模块未提供 analyze_image_with_three_models，跳过检查")
                    return True

            except Exception as e:
                logger.info(f"Gate检查过程中发生错误: {str(e)}")
                # 检查失败时，为了安全起见，返回False
                return False

        # 不在范围内或 gate 模块不可用：直接通过
        logger.info(f"{check_type} 类型图片直接通过检查（未启用Gate或不在范围）")
        return True
    
    def process_accessories_unified(self, image_paths: List[str], analysis: Dict[str, str], 
                                   output_dir: str = "output") -> List[str]:
        """
        统一处理配件（服装、手拿、头戴）
        
        Args:
            image_paths: 输入图片路径列表
            analysis: 分析结果，包含服装、手拿、头戴等信息
            output_dir: 输出目录
            
        Returns:
            List[str]: 处理后的图片路径列表
        """
        logger.info(f"\n=== 统一配件处理 ===")
        
        if not self.banana_unified:
            logger.error("banana-pro-img-jd模块未加载")
            return image_paths
        
        # 构建综合配件信息
        accessories_parts = []
        if analysis.get('服装'):
            accessories_parts.append(f"服装：{analysis['服装']}")
        if analysis.get('手拿'):
            accessories_parts.append(f"手拿：{analysis['手拿']}")
        if analysis.get('头戴'):
            accessories_parts.append(f"头戴：{analysis['头戴']}")
        
        if not accessories_parts:
            logger.info("无配件信息，跳过配件处理")
            return image_paths
        
        accessories_info = "，".join(accessories_parts)
        logger.info(f"综合配件信息: {accessories_info}")
        
        # 使用并行处理
        return self._process_accessory_parallel(
            image_paths, 
            accessories_info, 
            self.banana_unified.generate_image_with_accessories,
            "统一配件"
        )
    
    def _process_accessory_parallel(self, image_paths: List[str], accessory_info: str,
                                    process_func, accessory_type: str) -> List[str]:
        """
        并行处理配饰（通用方法）
        
        Args:
            image_paths: 输入图片路径列表
            accessory_info: 配饰信息
            process_func: 处理函数
            accessory_type: 配饰类型名称（用于日志）
            
        Returns:
            List[str]: 处理后的图片路径列表
        """
        if len(image_paths) <= 1:
            # 单张图片直接处理，不需要并行
            return self._process_accessory_single(image_paths, accessory_info, process_func, accessory_type)
        
        # 多张图片并行处理
        max_workers = min(MAX_PARALLEL_WORKERS, len(image_paths))
        logger.info(f"[{accessory_type}] 并行处理 {len(image_paths)} 张图片，workers={max_workers}")
        
        # 保持原始顺序的结果字典
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_idx = {
                executor.submit(self._process_single_image, img_path, accessory_info, process_func): idx
                for idx, img_path in enumerate(image_paths)
            }
            
            # 收集结果
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                original_path = image_paths[idx]
                try:
                    result = future.result(timeout=120)
                    results[idx] = result if result else original_path
                    logger.info(f"[{accessory_type}] 图片 {idx+1}/{len(image_paths)} 处理完成")
                except Exception as e:
                    logger.warning(f"[{accessory_type}] 图片 {idx+1} 处理失败: {str(e)}")
                    results[idx] = original_path
        
        # 按原始顺序返回结果
        return [results[i] for i in range(len(image_paths))]
    
    def _process_accessory_single(self, image_paths: List[str], accessory_info: str,
                                  process_func, accessory_type: str) -> List[str]:
        """串行处理配饰（单张或兜底）"""
        processed_images = []
        for image_path in image_paths:
            result = self._process_single_image(image_path, accessory_info, process_func)
            processed_images.append(result if result else image_path)
        return processed_images
    
    def _process_single_image(self, image_path: str, accessory_info: str, 
                              process_func) -> Optional[str]:
        """处理单张图片"""
        try:
            result_url = process_func(image_path, accessory_info)
            if result_url:
                # 转换URL为本地路径
                if result_url.startswith('/'):
                    return result_url.lstrip('/')
                return result_url
            return None
        except Exception as e:
            logger.warning(f"处理图片时发生错误: {str(e)}")
            return None
    
    def process_clothes(self, image_paths: List[str], clothes_info: str, 
                       output_dir: str = "output") -> List[str]:
        """
        处理服装配件（兼容旧接口）
        
        Args:
            image_paths: 输入图片路径列表
            clothes_info: 服装信息
            output_dir: 输出目录
            
        Returns:
            List[str]: 处理后的图片路径列表
        """
        if not clothes_info:
            logger.info("跳过服装处理（无服装信息）")
            return image_paths
        
        logger.info(f"=== 处理服装配件 (信息: {clothes_info}) ===")
        
        if not self.banana_unified:
            logger.error("banana-unified模块未加载")
            return image_paths
        
        # 使用统一模块处理
        result = self._process_accessory_parallel(
            image_paths, 
            f"服装：{clothes_info}", 
            self.banana_unified.generate_image_with_accessories,
            "服装"
        )
        logger.info(f"[服装处理] 完成，处理了 {len(result)} 张图片")
        return result
    
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
            logger.info("跳过手拿处理（无手拿信息）")
            return image_paths
        info = hands_info.strip()
        if not info or info in {"无", "没有", "未提供", "不拿"}:
            logger.info("跳过手拿处理（无效或否定的手拿信息）")
            return image_paths
        # 若出现交叉标签或仅标签文本，直接跳过
        if "头戴" in info or re.fullmatch(r"头戴[：:]?\s*", info):
            logger.info("跳过手拿处理（检测到误传的头戴信息）")
            return image_paths

        logger.info(f"=== 步骤6: 处理手拿物品 (信息: {info}) ===")
        
        if not self.banana_unified:
            logger.error("banana-unified模块未加载")
            return image_paths
        
        # 使用统一模块处理
        result = self._process_accessory_parallel(
            image_paths, 
            f"手拿：{info}", 
            self.banana_unified.generate_image_with_accessories,
            "手拿"
        )
        logger.info(f"[手拿处理] 完成，处理了 {len(result)} 张图片")
        return result

    def process_hats(self, image_paths: List[str], hats_info: str, 
                    output_dir: str = "output") -> List[str]:
        """
        步骤8: 处理头戴物品（支持并行处理）
        
        Args:
            image_paths: 输入图片路径列表
            hats_info: 头戴物品信息
            output_dir: 输出目录
            
        Returns:
            List[str]: 处理后的图片路径列表
        """
        if not hats_info:
            logger.info("跳过头戴处理（无头戴信息）")
            return image_paths
        
        logger.info(f"\n=== 步骤8: 处理头戴物品 (信息: {hats_info}) ===")
        
        if not self.banana_unified:
            logger.error("banana-unified模块未加载")
            return image_paths
        
        # 使用统一模块处理
        result = self._process_accessory_parallel(
            image_paths, 
            f"头戴：{hats_info}", 
            self.banana_unified.generate_image_with_accessories,
            "头戴"
        )
        logger.info(f"头戴处理完成，生成图片数: {len(result)}")
        return result
    
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
            logger.info("跳过背景处理（无背景信息）")
            return image_paths
        
        logger.info(f"\n=== 步骤10: 处理背景 (信息: {background_info}) ===")
        
        if not self.banana_background:
            logger.info("错误：banana-background模块未加载")
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
                    
                    logger.info(f"成功处理背景: {result_path}")
                    processed_images.append(result_path)
                else:
                    logger.warning(f"生成背景图片失败: {image_path}")
                    # 失败时保留原图片
                    processed_images.append(image_path)
                    
            except Exception as e:
                logger.warning(f"处理背景时发生错误: {str(e)}")
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
        logger.info("\n=== 多层内容合规检查 ===")
        
        # 组合所有内容进行检查
        content_parts = []
        for key, value in analysis.items():
            if value and key != '_raw_ai':  # 排除内部字段
                content_parts.append(f"{key}: {value}")
        
        full_content = ", ".join(content_parts)
        logger.info(f"检查内容: {full_content}")
        logger.info(f"检查层级: 1.违规词库检查 → 2.敏感内容AI检查 → 3.通用违规AI检查")
        
        try:
            is_compliant, reason = self.content_agent.check_compliance(full_content)
            if not is_compliant:
                logger.warning(f"内容不合规: {reason}")
                return False
            else:
                logger.info("✓ 所有层级检查通过，内容合规")
                return True
        except Exception as e:
            logger.warning(f"合规检查失败: {str(e)}")
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
        
        logger.info("开始完整图片生成流程")

        # 步骤0: 内容合规检查
        if not self.check_content_compliance(analysis):
            logger.info("错误：内容不合规，终止生成流程")
            return []
        
        # 步骤1-3: 生成基础图片
        images = self.generate_step1_images(head_matches, body_matches, output_dir)
        
        if not images:
            logger.info("错误：未能生成基础图片")
            return []
        
        # 步骤4-9: 统一处理配件（服装、手拿、头戴）
        images = self.process_accessories_unified(images, analysis, output_dir)
        
        # 步骤10-11: 处理背景
        if analysis.get('背景'):
            images = self.process_background(images, analysis['背景'], output_dir)
        
        # 最终 Gate 检查：在展示前对所有图片进行质量检查
        images = self.final_gate_check(images)

        logger.info(f"图片生成流程完成！共生成 {len(images)} 张图片")

        return images
    
    def final_gate_check(self, image_paths: List[str]) -> List[str]:
        """
        最终 Gate 检查：在图片展示到页面前进行统一质量检查（支持并行）
        
        Args:
            image_paths: 待检查的图片路径列表
            
        Returns:
            List[str]: 通过检查的图片路径列表
        """
        import sys
        
        def _log(msg: str):
            """带前缀的日志输出，确保立即刷新"""
            logger.info(f"[FinalGate] {msg}")
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
        
        # 单张图片直接检查，不需要并行
        if len(image_paths) == 1:
            return self._gate_check_single(image_paths, _log)
        
        # 多张图片并行检查
        return self._gate_check_parallel(image_paths, _log)
    
    def _gate_check_single(self, image_paths: List[str], _log) -> List[str]:
        """串行 Gate 检查（单张图片）"""
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
    
    def _gate_check_parallel(self, image_paths: List[str], _log) -> List[str]:
        """并行 Gate 检查（多张图片）"""
        max_workers = min(MAX_PARALLEL_WORKERS, len(image_paths))
        _log(f"并行检查 {len(image_paths)} 张图片，workers={max_workers}")
        
        # 保持原始顺序的结果字典
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有检查任务
            future_to_idx = {
                executor.submit(self._check_single_image_gate, img_path): idx
                for idx, img_path in enumerate(image_paths)
            }
            
            # 收集结果
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                image_path = image_paths[idx]
                try:
                    passed, reason = future.result(timeout=60)
                    results[idx] = (image_path, passed, reason)
                    status = "✅ 通过" if passed else f"❌ 未通过: {reason}"
                    _log(f"图片 [{idx+1}/{len(image_paths)}] {status}")
                except Exception as e:
                    results[idx] = (image_path, False, str(e))
                    _log(f"图片 [{idx+1}/{len(image_paths)}] ❌ 检查出错: {str(e)}")
        
        # 按原始顺序返回通过的图片
        passed_images = [
            results[i][0] for i in range(len(image_paths))
            if i in results and results[i][1]
        ]
        
        _log(f"检查完成: {len(passed_images)}/{len(image_paths)} 张图片通过")
        return passed_images
    
    def _check_single_image_gate(self, image_path: str) -> tuple:
        """检查单张图片（供并行调用）"""
        try:
            ok, analysis_results = self.gate_check.analyze_image_with_three_models(image_path)
            if ok:
                return (True, "")
            else:
                try:
                    models = list(analysis_results.keys())
                    return (False, f"异常模型: {', '.join(models[:3])}")
                except Exception:
                    return (False, "检查未通过")
        except Exception as e:
            return (False, str(e))

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
    # logger.info(f"最终生成的图片: {result}")

