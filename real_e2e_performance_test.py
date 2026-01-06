#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实端到端性能测试：完整跑通所有环节
用例："顶着带小铃铛的深蓝贝雷帽，穿着红色法兰绒衬衫外套，手持散发暖光的松果魔法棒"

完整流程：
1. 系统初始化
2. 内容合规检查
3. AI内容分析（六维度）
4. 表情动作分析
5. 基础图片生成（head+body组合）
6. 统一配件处理（调用banana-pro-img-jd.py的API）
7. Gate质量检查
8. 结果整理
"""

import time
import logging
import sys
import os
from typing import Dict, List, Optional

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealE2ETimer:
    """真实端到端计时器"""
    
    def __init__(self):
        self.timings = {}
        self.start_time = None
        self.stage_details = {}
        self.total_start = None
    
    def start_total(self):
        """开始总计时"""
        self.total_start = time.time()
    
    def start(self, stage_name: str):
        """开始计时"""
        self.start_time = time.time()
        logger.info(f"🚀 开始 {stage_name}")
    
    def end(self, stage_name: str, details: str = ""):
        """结束计时"""
        if self.start_time is None:
            return 0
        
        duration = time.time() - self.start_time
        self.timings[stage_name] = duration
        self.stage_details[stage_name] = details
        logger.info(f"✅ 完成 {stage_name} - 用时: {duration:.2f}秒 {details}")
        self.start_time = None
        return duration
    
    def get_total_time(self):
        """获取总用时"""
        if self.total_start:
            return time.time() - self.total_start
        return sum(self.timings.values())

def test_real_complete_flow():
    """测试真实的完整生图流程"""
    
    test_requirement = "顶着带小铃铛的深蓝贝雷帽，穿着红色法兰绒衬衫外套，手持散发暖光的松果魔法棒"
    
    timer = RealE2ETimer()
    timer.start_total()
    
    logger.info("="*80)
    logger.info("真实端到端完整生图流程测试")
    logger.info(f"测试用例: {test_requirement}")
    logger.info("="*80)
    
    result_info = {
        'input': test_requirement,
        'stages': {},
        'errors': []
    }
    
    try:
        # ========== 阶段1: 系统初始化 ==========
        timer.start("1.系统初始化")
        
        from content_agent import ContentAgent
        from generation_controller import GenerationController
        from image_processor import ImageProcessor
        from matchers.head_matcher import HeadMatcher
        from matchers.body_matcher import BodyMatcher
        
        content_agent = ContentAgent()
        generation_controller = GenerationController()
        image_processor = ImageProcessor()
        head_matcher = HeadMatcher()
        body_matcher = BodyMatcher()
        
        timer.end("1.系统初始化", "- 所有模块加载完成")
        result_info['stages']['系统初始化'] = '成功'
        
        # ========== 阶段2: 违规词检查 ==========
        timer.start("2.违规词检查")
        
        is_compliant, reason = content_agent._check_external_banned_words(test_requirement)
        
        if not is_compliant:
            timer.end("2.违规词检查", f"- 不通过: {reason}")
            result_info['errors'].append(f"违规词检查不通过: {reason}")
            return generate_final_report(timer, result_info)
        
        timer.end("2.违规词检查", "- 通过")
        result_info['stages']['违规词检查'] = '通过'
        
        # ========== 阶段3: AI敏感内容检查 ==========
        timer.start("3.AI敏感内容检查")
        
        is_sensitive, sensitive_reason = content_agent._check_sensitive_content_with_ai(test_requirement)
        
        timer.end("3.AI敏感内容检查", f"- {'通过' if is_sensitive else '不通过'}")
        result_info['stages']['AI敏感内容检查'] = '通过' if is_sensitive else f'不通过: {sensitive_reason}'
        
        # ========== 阶段4: AI内容分析（六维度） ==========
        timer.start("4.AI内容分析")
        
        analysis = content_agent._analyze_content_combined(test_requirement)
        
        analysis_count = len([k for k, v in analysis.items() if v and not k.startswith('_')])
        timer.end("4.AI内容分析", f"- 分析维度: {analysis_count}")
        
        logger.info(f"分析结果: {analysis}")
        result_info['analysis'] = analysis
        result_info['stages']['AI内容分析'] = f'成功，{analysis_count}个维度'
        
        # ========== 阶段5: 表情动作分析 ==========
        timer.start("5.表情动作分析")
        
        expression_info = head_matcher.analyze_user_requirement(test_requirement)
        action_type = body_matcher.classify_action_type(test_requirement)
        
        timer.end("5.表情动作分析", f"- 表情: {expression_info.get('表情', '未识别')}, 动作: {action_type}")
        result_info['stages']['表情动作分析'] = f'表情: {expression_info.get("表情", "未识别")}, 动作: {action_type}'
        
        # ========== 阶段6: 基础图片生成 ==========
        timer.start("6.基础图片生成")
        
        processor_result = image_processor.process_user_requirement(test_requirement)
        
        if not processor_result['success']:
            timer.end("6.基础图片生成", f"- 失败: {processor_result.get('error', '未知错误')}")
            result_info['errors'].append(f"基础图片生成失败: {processor_result.get('error')}")
            return generate_final_report(timer, result_info)
        
        base_images = processor_result['combined_images']
        timer.end("6.基础图片生成", f"- 生成图片: {len(base_images)}张")
        
        logger.info(f"基础图片: {base_images}")
        result_info['base_images'] = base_images
        result_info['stages']['基础图片生成'] = f'成功，{len(base_images)}张'
        
        # ========== 阶段7: 统一配件处理（真实API调用） ==========
        timer.start("7.统一配件处理")
        
        # 构建配饰信息
        accessories_info = {}
        
        # 处理服装（上装+下装）
        clothes_parts = []
        if analysis.get('上装'):
            clothes_parts.append(analysis['上装'])
        if analysis.get('下装'):
            clothes_parts.append(analysis['下装'])
        if clothes_parts:
            accessories_info['服装'] = '，'.join(clothes_parts)
        
        # 处理手持
        if analysis.get('手持'):
            accessories_info['手拿'] = analysis['手持']
        
        # 处理头戴
        if analysis.get('头戴'):
            accessories_info['头戴'] = analysis['头戴']
        
        logger.info(f"配饰信息: {accessories_info}")
        
        # 调用真实的统一配件处理
        if accessories_info and base_images:
            processed_images = generation_controller.process_accessories_unified(
                base_images, accessories_info
            )
            timer.end("7.统一配件处理", f"- 处理图片: {len(processed_images)}张")
            result_info['processed_images'] = processed_images
            result_info['stages']['统一配件处理'] = f'成功，{len(processed_images)}张'
        else:
            processed_images = base_images
            timer.end("7.统一配件处理", "- 跳过（无配件信息）")
            result_info['processed_images'] = processed_images
            result_info['stages']['统一配件处理'] = '跳过'
        
        # ========== 阶段8: Gate质量检查 ==========
        timer.start("8.Gate质量检查")
        
        final_images = generation_controller.final_gate_check(processed_images)
        
        timer.end("8.Gate质量检查", f"- 通过: {len(final_images)}/{len(processed_images)}张")
        result_info['final_images'] = final_images
        result_info['stages']['Gate质量检查'] = f'{len(final_images)}/{len(processed_images)}张通过'
        
        # ========== 阶段9: 结果整理 ==========
        timer.start("9.结果整理")
        
        # 验证文件存在性
        validated_images = []
        for img_path in final_images:
            if os.path.exists(img_path):
                validated_images.append(img_path)
        
        # 保存结果
        import json
        result_file = f"output/real_e2e_result_{int(time.time())}.json"
        os.makedirs("output", exist_ok=True)
        
        result_info['validated_images'] = validated_images
        result_info['accessories_info'] = accessories_info
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_info, f, ensure_ascii=False, indent=2, default=str)
        
        timer.end("9.结果整理", f"- 最终图片: {len(validated_images)}张")
        result_info['stages']['结果整理'] = f'成功，{len(validated_images)}张'
        
        # 生成最终报告
        return generate_final_report(timer, result_info)
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        result_info['errors'].append(str(e))
        return generate_final_report(timer, result_info)

def generate_final_report(timer: RealE2ETimer, result_info: Dict):
    """生成最终的性能报告"""
    
    total_time = timer.get_total_time()
    
    logger.info("\n" + "="*80)
    logger.info("📊 真实端到端性能分析报告")
    logger.info("="*80)
    
    logger.info(f"测试用例: {result_info['input']}")
    logger.info(f"📊 总用时: {total_time:.2f}秒")
    
    # 按用时排序
    sorted_stages = sorted(timer.timings.items(), key=lambda x: x[1], reverse=True)
    
    logger.info("\n各环节详细用时:")
    logger.info("-" * 80)
    
    for i, (stage, duration) in enumerate(sorted_stages, 1):
        percentage = (duration / total_time * 100) if total_time > 0 else 0
        detail = timer.stage_details.get(stage, "")
        logger.info(f"{i:2d}. {stage:<25} {duration:>8.2f}秒 ({percentage:>5.1f}%) {detail}")
    
    # 输出阶段状态
    logger.info("\n📋 各阶段状态:")
    logger.info("-" * 80)
    for stage, status in result_info.get('stages', {}).items():
        logger.info(f"   {stage}: {status}")
    
    # 输出错误信息
    if result_info.get('errors'):
        logger.info("\n❌ 错误信息:")
        logger.info("-" * 80)
        for error in result_info['errors']:
            logger.info(f"   {error}")
    
    # 输出生成结果统计
    logger.info("\n📊 生成结果统计:")
    logger.info("-" * 80)
    logger.info(f"   基础图片数量: {len(result_info.get('base_images', []))}")
    logger.info(f"   处理后图片数量: {len(result_info.get('processed_images', []))}")
    logger.info(f"   最终图片数量: {len(result_info.get('final_images', []))}")
    logger.info(f"   验证通过图片: {len(result_info.get('validated_images', []))}")
    logger.info(f"   配件类型: {list(result_info.get('accessories_info', {}).keys())}")
    
    # 分析性能瓶颈
    analyze_real_bottlenecks(sorted_stages, total_time)
    
    return timer.timings

def analyze_real_bottlenecks(sorted_stages: List, total_time: float):
    """分析真实的性能瓶颈"""
    
    logger.info("\n" + "="*80)
    logger.info("🔍 性能瓶颈分析")
    logger.info("="*80)
    
    if not sorted_stages:
        return
    
    # 分析最耗时的环节
    top_stages = sorted_stages[:3]
    
    logger.info("⚠️  最耗时的3个环节:")
    for i, (stage, duration) in enumerate(top_stages, 1):
        percentage = (duration / total_time * 100) if total_time > 0 else 0
        logger.info(f"  {i}. {stage}: {duration:.2f}秒 ({percentage:.1f}%)")
    
    # 优化建议
    logger.info("\n💡 优化建议:")
    logger.info("-" * 80)
    
    optimization_map = {
        "4.AI内容分析": [
            "🚀 实现智能缓存，相似内容复用分析结果",
            "🚀 优化prompt设计，减少token消耗",
            "🚀 使用更快的AI模型"
        ],
        "3.AI敏感内容检查": [
            "🚀 与内容分析合并为单次AI调用",
            "🚀 实现结果缓存",
            "🚀 使用更快的AI模型"
        ],
        "5.表情动作分析": [
            "🚀 扩展本地关键词库，减少AI调用",
            "🚀 使用预训练的轻量级分类模型",
            "🚀 并行执行表情和动作分析"
        ],
        "6.基础图片生成": [
            "🚀 并行处理多个head和body组合",
            "🚀 使用GPU加速图片合成",
            "🚀 预生成常用组合"
        ],
        "7.统一配件处理": [
            "🚀 使用更快的AI模型（如Gemini-2.5-flash）",
            "🚀 批量处理多张图片",
            "🚀 实现请求缓存"
        ],
        "8.Gate质量检查": [
            "🚀 并行检查多张图片",
            "🚀 使用轻量级检查模型",
            "🚀 设置检查阈值"
        ]
    }
    
    for stage, duration in top_stages:
        if stage in optimization_map:
            logger.info(f"\n📌 {stage} 优化建议:")
            for suggestion in optimization_map[stage]:
                logger.info(f"   {suggestion}")
    
    # 预期优化效果
    estimate_optimization_impact(sorted_stages, total_time)

def estimate_optimization_impact(sorted_stages: List, current_time: float):
    """估算优化效果"""
    
    logger.info("\n📈 预期优化效果:")
    logger.info("-" * 80)
    
    # 基于真实测试的优化估算
    optimization_factors = {
        "1.系统初始化": 0.5,           # 单例和预热可减少50%
        "2.违规词检查": 0.9,           # 已经很快
        "3.AI敏感内容检查": 0.4,       # 合并调用可减少60%
        "4.AI内容分析": 0.3,           # 缓存和优化可减少70%
        "5.表情动作分析": 0.2,         # 本地处理可减少80%
        "6.基础图片生成": 0.5,         # 并行和预生成可减少50%
        "7.统一配件处理": 0.4,         # 更快模型和缓存可减少60%
        "8.Gate质量检查": 0.4,         # 并行和轻量模型可减少60%
        "9.结果整理": 0.7              # 优化算法可减少30%
    }
    
    optimized_time = 0
    for stage, duration in sorted_stages:
        factor = optimization_factors.get(stage, 0.8)
        optimized_duration = duration * factor
        optimized_time += optimized_duration
        
        improvement = (1 - factor) * 100
        logger.info(f"   {stage:<25} {duration:.2f}s → {optimized_duration:.2f}s (-{improvement:.0f}%)")
    
    total_improvement = ((current_time - optimized_time) / current_time * 100) if current_time > 0 else 0
    
    logger.info("-" * 80)
    logger.info(f"   当前总用时: {current_time:.2f}秒")
    logger.info(f"   优化后预估: {optimized_time:.2f}秒")
    logger.info(f"   总体提升: {total_improvement:.1f}%")

if __name__ == "__main__":
    logger.info("真实端到端完整生图流程测试启动")
    
    # 确认是否进行完整测试
    logger.info("⚠️  此测试将进行真实的完整生图流程，包括：")
    logger.info("   - AI内容分析")
    logger.info("   - 基础图片生成")
    logger.info("   - 配件处理API调用（banana-pro-img-jd.py）")
    logger.info("   - Gate质量检查")
    
    choice = input("是否继续？(y/N): ").strip().lower()
    
    if choice == 'y':
        test_real_complete_flow()
    else:
        logger.info("测试已取消")