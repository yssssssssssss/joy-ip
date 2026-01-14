#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2D素材图片生成流程控制器
负责协调2D图片生成流程：
1. 使用per-data-2D.py生成基础拼接图片
2. 使用banana-pro-img-jd.py进行配件处理
3. 使用gate-result.py每步进行质量检查
"""

import os
import sys
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import logging

from utils.module_loader import ModuleLoader
from content_agent_2d import ContentAgent2D
from matchers.head_matcher_2d import HeadMatcher2D
from matchers.body_matcher_2d import BodyMatcher2D

logger = logging.getLogger(__name__)

# Gate 检查开关与范围（复用3D配置）
ENABLE_GATE_CHECK = str(os.environ.get("ENABLE_GATE_CHECK", "1")).strip().lower() in ("1", "true")
GATE_CHECK_SCOPE = str(os.environ.get("GATE_CHECK_SCOPE", "hats")).strip().lower()

# 并行处理配置
MAX_PARALLEL_WORKERS = int(os.environ.get("MAX_PARALLEL_WORKERS", "2"))
# 2D 专属并行配置（默认 4，比 3D 更高以提升效率）
MAX_PARALLEL_WORKERS_2D = int(os.environ.get("MAX_PARALLEL_WORKERS_2D", "4"))


class GenerationController2D:
    """2D素材图片生成流程控制器"""
    
    def __init__(self):
        """初始化2D控制器"""
        self.max_retries = 1
        
        # 初始化2D内容分析器
        self.content_agent = ContentAgent2D()
        
        # 初始化2D匹配器
        self.head_matcher = HeadMatcher2D()
        self.body_matcher = BodyMatcher2D()
        
        # 动态加载模块
        self._load_modules()
        
        logger.info("GenerationController2D 初始化完成")
    
    def _load_modules(self):
        """动态加载所需的Python模块"""
        modules = {
            'banana_unified': 'banana-pro-img-jd.py',  # 统一处理模块
            'banana_background': 'banana-background.py',
            'gate_check': 'gate-result.py',
            'per_data_2d': 'per-data-2D.py'  # 2D拼接模块
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
                               output_dir: str = "output", action_type: str = None) -> List[str]:
        """
        步骤1：使用per-data-2D.py生成基础组合图片（并行处理）
        
        Args:
            head_matches: 头像匹配结果列表
            body_matches: 身体匹配结果列表
            output_dir: 输出目录
            action_type: 动作类型（用于特殊处理，如跑动）
            
        Returns:
            List[str]: 生成的图片路径列表
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        logger.info("=== 步骤1: 2D基础图片生成（并行） ===")
        
        if not self.per_data_2d:
            logger.error("per-data-2D模块未加载")
            return []
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 构建所有组合任务
        tasks = []
        for i, body_match in enumerate(body_matches):
            for j, head_match in enumerate(head_matches):
                body_path = body_match.get('image_path')
                head_path = head_match.get('image_path')
                
                if not body_path or not head_path:
                    continue
                if not os.path.exists(body_path) or not os.path.exists(head_path):
                    continue
                
                tasks.append((body_path, head_path, output_dir, action_type, i, j))
        
        if not tasks:
            logger.warning("无有效的头身组合任务")
            return []
        
        logger.info(f"共 {len(tasks)} 个拼接任务，使用 {MAX_PARALLEL_WORKERS_2D} 个并行 workers")
        
        # 并行处理
        generated_images = []
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS_2D) as executor:
            future_to_idx = {
                executor.submit(self._compose_single_image, *task): idx
                for idx, task in enumerate(tasks)
            }
            
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    result = future.result(timeout=60)
                    if result:
                        generated_images.append(result)
                        logger.info(f"拼接任务 {idx+1}/{len(tasks)} 完成: {result}")
                except Exception as e:
                    logger.warning(f"拼接任务 {idx+1} 失败: {str(e)}")
        
        logger.info(f"步骤1完成，共生成 {len(generated_images)} 张2D图片")
        return generated_images
    
    def _compose_single_image(self, body_path: str, head_path: str, 
                               output_dir: str, action_type: str,
                               body_idx: int, head_idx: int) -> Optional[str]:
        """
        拼接单张图片（供并行调用）
        """
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output_path = os.path.join(output_dir, f"2d_step1_{timestamp}_{body_idx}_{head_idx}.png")
        
        try:
            result = self.per_data_2d.compose_images_new_logic(
                body_path, head_path, output_path, action_type=action_type
            )
            
            if result and isinstance(result, str) and os.path.exists(result):
                return result
            elif result and os.path.exists(output_path):
                return output_path
            else:
                return None
        except Exception as e:
            logger.warning(f"拼接图片失败 ({body_path}, {head_path}): {str(e)}")
            return None
    
    def check_image_quality(self, image_path: str, check_type: str) -> bool:
        """
        检查图片质量
        
        Args:
            image_path: 图片路径
            check_type: 检查类型
            
        Returns:
            bool: 是否通过检查
        """
        logger.info(f"检查图片质量: {image_path} (类型: {check_type})")
        
        if not ENABLE_GATE_CHECK or GATE_CHECK_SCOPE == 'none':
            logger.info(f"{check_type} 类型图片直接通过检查（Gate检查关闭）")
            return True
        
        if GATE_CHECK_SCOPE == 'all':
            scope_types = ['clothes', 'hands', 'hats', 'background']
        else:
            scope_types = ['hats']
        
        if check_type in scope_types and getattr(self, 'gate_check', None):
            try:
                logger.info(f"使用 Gate 模块检查图片: {image_path}")
                if hasattr(self.gate_check, 'analyze_image_with_three_models'):
                    ok, analysis_results = self.gate_check.analyze_image_with_three_models(image_path)
                    logger.info(f"Gate检查结果: {'正常' if ok else '异常'}")
                    return bool(ok)
                else:
                    logger.info("Gate模块未提供 analyze_image_with_three_models，跳过检查")
                    return True
            except Exception as e:
                logger.info(f"Gate检查过程中发生错误: {str(e)}")
                return False
        
        logger.info(f"{check_type} 类型图片直接通过检查")
        return True
    
    def process_accessories_unified(self, image_paths: List[str], analysis: Dict[str, str],
                                     output_dir: str = "output") -> List[str]:
        """
        统一处理配件（服装、手拿、头戴）
        
        Args:
            image_paths: 输入图片路径列表
            analysis: 分析结果
            output_dir: 输出目录
            
        Returns:
            List[str]: 处理后的图片路径列表
        """
        logger.info("=== 2D统一配件处理 ===")
        
        if not self.banana_unified:
            logger.error("banana-pro-img-jd模块未加载")
            return image_paths
        
        # 构建综合配件信息
        accessories_parts = []
        
        # 检查上装和下装
        if analysis.get('上装'):
            accessories_parts.append(f"上装：{analysis['上装']}")
        if analysis.get('下装'):
            accessories_parts.append(f"下装：{analysis['下装']}")
        
        # 如果没有分开的上下装，检查服装字段
        if not accessories_parts and analysis.get('服装'):
            accessories_parts.append(f"服装：{analysis['服装']}")
        
        if analysis.get('手持') or analysis.get('手拿'):
            hand_item = analysis.get('手持') or analysis.get('手拿')
            accessories_parts.append(f"手持：{hand_item}")
        
        if analysis.get('头戴'):
            accessories_parts.append(f"头戴：{analysis['头戴']}")
        
        if not accessories_parts:
            logger.info("无配件信息，跳过配件处理")
            return image_paths
        
        accessories_info = "，".join(accessories_parts)
        logger.info(f"2D综合配件信息: {accessories_info}")
        
        return self._process_accessory_parallel(
            image_paths,
            accessories_info,
            self.banana_unified.generate_image_with_accessories,
            "2D统一配件",
            mode="2d"  # 2D模式
        )
    
    def _process_accessory_parallel(self, image_paths: List[str], accessory_info: str,
                                     process_func, accessory_type: str, mode: str = "3d") -> List[str]:
        """并行处理配饰（4路并发）"""
        if len(image_paths) <= 1:
            return self._process_accessory_single(image_paths, accessory_info, process_func, accessory_type, mode)
        
        max_workers = min(MAX_PARALLEL_WORKERS_2D, len(image_paths))
        logger.info(f"[{accessory_type}] 并行处理 {len(image_paths)} 张图片，workers={max_workers}, mode={mode}")
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(self._process_single_image, img_path, accessory_info, process_func, mode): idx
                for idx, img_path in enumerate(image_paths)
            }
            
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
        
        return [results[i] for i in range(len(image_paths))]
    
    def _process_accessory_single(self, image_paths: List[str], accessory_info: str,
                                   process_func, accessory_type: str, mode: str = "3d") -> List[str]:
        """串行处理配饰"""
        processed_images = []
        for image_path in image_paths:
            result = self._process_single_image(image_path, accessory_info, process_func, mode)
            processed_images.append(result if result else image_path)
        return processed_images
    
    def _process_single_image(self, image_path: str, accessory_info: str,
                               process_func, mode: str = "3d") -> Optional[str]:
        """处理单张图片"""
        try:
            # 传递mode参数
            result_url = process_func(image_path, accessory_info, mode=mode)
            if result_url:
                if result_url.startswith('/'):
                    return result_url.lstrip('/')
                return result_url
            return None
        except Exception as e:
            logger.warning(f"处理图片时发生错误: {str(e)}")
            return None
    
    def process_background(self, image_paths: List[str], background_info: str,
                            output_dir: str = "output") -> List[str]:
        """处理背景"""
        if not background_info:
            logger.info("跳过背景处理（无背景信息）")
            return image_paths
        
        logger.info(f"=== 2D背景处理 (信息: {background_info}) ===")
        
        if not self.banana_background:
            logger.info("banana-background模块未加载")
            return image_paths
        
        processed_images = []
        
        for image_path in image_paths:
            try:
                result_url = self.banana_background.generate_image_with_accessories(
                    image_path, background_info
                )
                
                if result_url:
                    if result_url.startswith('/'):
                        result_path = result_url.lstrip('/')
                    else:
                        result_path = result_url
                    logger.info(f"成功处理背景: {result_path}")
                    processed_images.append(result_path)
                else:
                    logger.warning(f"生成背景图片失败: {image_path}")
                    processed_images.append(image_path)
                    
            except Exception as e:
                logger.warning(f"处理背景时发生错误: {str(e)}")
                processed_images.append(image_path)
        
        return processed_images
    
    def check_content_compliance(self, analysis: Dict[str, str]) -> bool:
        """检查生成内容是否合规"""
        logger.info("=== 2D内容合规检查 ===")
        
        content_parts = []
        for key, value in analysis.items():
            if value and key not in ['_raw_ai', '视角']:
                content_parts.append(f"{key}: {value}")
        
        full_content = ", ".join(content_parts)
        logger.info(f"检查内容: {full_content}")
        
        try:
            is_compliant, reason = self.content_agent.check_compliance(full_content)
            if not is_compliant:
                logger.warning(f"内容不合规: {reason}")
                return False
            else:
                logger.info("✓ 内容合规检查通过")
                return True
        except Exception as e:
            logger.warning(f"合规检查失败: {str(e)}")
            return False
    
    def final_gate_check(self, image_paths: List[str]) -> List[str]:
        """最终Gate检查（4路并发）"""
        def _log(msg: str):
            logger.info(f"[FinalGate2D] {msg}")
            sys.stdout.flush()
        
        if not ENABLE_GATE_CHECK or GATE_CHECK_SCOPE == 'none':
            _log("已跳过（开关关闭）")
            return image_paths
        
        if not image_paths:
            return []
        
        _log(f"开始检查 {len(image_paths)} 张2D图片")
        
        if not getattr(self, 'gate_check', None):
            _log("Gate 模块不可用，跳过检查")
            return image_paths
        
        if not hasattr(self.gate_check, 'analyze_image_with_three_models'):
            _log("Gate 模块未提供 analyze_image_with_three_models，跳过检查")
            return image_paths
        
        # 单张图片直接检查
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
                    _log(f"  ❌ 未通过检查")
            except Exception as e:
                _log(f"  ❌ 检查过程出错: {str(e)}")
        
        _log(f"检查完成: {len(passed_images)}/{len(image_paths)} 张图片通过")
        return passed_images
    
    def _gate_check_parallel(self, image_paths: List[str], _log) -> List[str]:
        """并行 Gate 检查（多张图片）"""
        max_workers = min(MAX_PARALLEL_WORKERS_2D, len(image_paths))
        _log(f"并行检查 {len(image_paths)} 张图片，workers={max_workers}")
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(self._check_single_image_gate, img_path): idx
                for idx, img_path in enumerate(image_paths)
            }
            
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

    
    def generate_complete_flow(self, requirement: str, perspective: str = "正视角",
                                output_dir: str = "output", pre_analysis: Dict = None) -> Dict:
        """
        2D完整图片生成流程
        
        Args:
            requirement: 用户需求描述
            perspective: 视角（正视角/仰视角）
            output_dir: 输出目录
            pre_analysis: 预分析结果（可选），如果提供则跳过内容分析步骤
            
        Returns:
            Dict: 生成结果，包含success, images, logs等
        """
        logger.info(f"开始2D完整图片生成流程, 视角: {perspective}")
        
        result = {
            "success": False,
            "images": [],
            "logs": [],
            "analysis": None,
            "error": None
        }
        
        # 步骤0: 内容分析和合规检查
        try:
            if pre_analysis:
                # 使用预分析结果，跳过重复分析
                logger.info("使用预分析结果，跳过重复分析")
                analysis = pre_analysis.copy()
                # 确保视角字段存在
                if '视角' not in analysis:
                    analysis['视角'] = perspective
                result["analysis"] = analysis
                result["logs"].append(f"使用预分析结果: {analysis}")
                
                # 仍需进行合规检查（检查配件内容）
                if not self.check_content_compliance(analysis):
                    result["error"] = "内容不合规"
                    result["logs"].append("配件内容合规检查未通过")
                    return result
            else:
                # 执行内容分析
                process_result = self.content_agent.process_content_2d(requirement, perspective)
                if not process_result.get('success') or not process_result.get('compliant'):
                    result["error"] = process_result.get('reason', '内容不合规')
                    result["logs"].append(f"内容分析失败: {result['error']}")
                    return result
                
                analysis = process_result.get('analysis', {})
                result["analysis"] = analysis
                result["logs"].append(f"内容分析完成: {analysis}")
        except Exception as e:
            result["error"] = f"内容分析异常: {str(e)}"
            result["logs"].append(result["error"])
            return result
        
        # 步骤1: 匹配头像和身体（各选2张，组合生成4张）
        try:
            head_matches, head_logs = self.head_matcher.find_one_best_match_2d(
                requirement, perspective, top_k=5, num_select=2
            )
            result["logs"].extend(head_logs)
            
            body_matches, body_logs = self.body_matcher.find_one_best_match_2d(
                requirement, perspective, top_k=5, num_select=2
            )
            result["logs"].extend(body_logs)
            
            if not head_matches or not body_matches:
                result["error"] = "未找到匹配的头像或身体图片"
                return result
                
            result["logs"].append(f"匹配完成: head={len(head_matches)}, body={len(body_matches)}")
        except Exception as e:
            result["error"] = f"图片匹配异常: {str(e)}"
            result["logs"].append(result["error"])
            return result
        
        # 步骤2: 生成基础拼接图片
        action_type = analysis.get('动作', '站姿')
        images = self.generate_step1_images(head_matches, body_matches, output_dir, action_type)
        
        if not images:
            result["error"] = "未能生成基础图片"
            return result
        
        result["logs"].append(f"基础图片生成完成: {len(images)} 张")
        
        # 步骤3: 处理配件
        images = self.process_accessories_unified(images, analysis, output_dir)
        result["logs"].append(f"配件处理完成: {len(images)} 张")
        
        # 步骤4: 处理背景（如果有）
        if analysis.get('背景'):
            images = self.process_background(images, analysis['背景'], output_dir)
            result["logs"].append(f"背景处理完成: {len(images)} 张")
        
        # 步骤5: 最终Gate检查
        images = self.final_gate_check(images)
        result["logs"].append(f"Gate检查完成: {len(images)} 张通过")
        
        result["success"] = len(images) > 0
        result["images"] = images
        
        logger.info(f"2D图片生成流程完成！共生成 {len(images)} 张图片")
        
        return result


if __name__ == "__main__":
    # 测试代码
    controller = GenerationController2D()
    
    # 模拟测试
    test_requirement = "一个开心的跳跃动作"
    test_perspective = "正视角"
    
    logger.info("=" * 60)
    logger.info(f"测试需求: {test_requirement}")
    logger.info(f"测试视角: {test_perspective}")
    logger.info("=" * 60)
    
    result = controller.generate_complete_flow(test_requirement, test_perspective)
    logger.info(f"生成结果: {result}")
