#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整端到端性能测试：包含真实的图片生成流程
用例："顶着带小铃铛的深蓝贝雷帽，穿着红色法兰绒衬衫外套，手持散发暖光的松果魔法棒"
"""

import time
import logging
import sys
import os
from typing import Dict, List

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EndToEndTimer:
    """端到端计时器"""
    
    def __init__(self):
        self.timings = {}
        self.start_time = None
        self.stage_details = {}
    
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

def test_complete_generation_flow():
    """测试完整的图片生成流程"""
    
    test_requirement = "顶着带小铃铛的深蓝贝雷帽，穿着红色法兰绒衬衫外套，手持散发暖光的松果魔法棒"
    
    timer = EndToEndTimer()
    
    logger.info("="*80)
    logger.info("完整端到端图片生成流程测试")
    logger.info(f"测试用例: {test_requirement}")
    logger.info("="*80)
    
    try:
        # 1. 系统初始化
        timer.start("系统初始化")
        from content_agent import ContentAgent
        from generation_controller import GenerationController
        from image_processor import ImageProcessor
        
        content_agent = ContentAgent()
        generation_controller = GenerationController()
        image_processor = ImageProcessor()
        timer.end("系统初始化")
        
        # 2. 内容合规检查和分析
        timer.start("内容合规检查和分析")
        result = content_agent.process_content(test_requirement)
        if not result['compliant']:
            logger.error(f"内容不合规: {result['reason']}")
            return None
        analysis = result['analysis']
        timer.end("内容合规检查和分析", f"- 分析维度: {len([k for k, v in analysis.items() if v and not k.startswith('_')])}")
        
        logger.info(f"分析结果: {analysis}")
        
        # 3. 基础图片生成
        timer.start("基础图片生成")
        
        # 使用ImageProcessor生成基础图片
        expression = analysis.get('表情', '')
        action = analysis.get('动作', '站姿')
        
        logger.info(f"生成基础图片 - 表情: {expression}, 动作: {action}")
        
        # 调用实际的图片生成
        result = image_processor.process_user_requirement(test_requirement)
        
        if result['success']:
            base_images = result['combined_images']
            timer.end("基础图片生成", f"- 生成图片: {len(base_images)}张")
        else:
            logger.error(f"基础图片生成失败: {result.get('error', '未知错误')}")
            timer.end("基础图片生成", "- 失败")
            return None
        
        if not base_images:
            logger.error("基础图片生成失败")
            return None
        
        logger.info(f"基础图片: {base_images}")
        
        # 4. 统一配件处理（真实API调用）
        timer.start("统一配件处理")
        
        # 构建配饰信息
        accessories_info = {}
        if analysis.get('上装') or analysis.get('下装'):
            clothes_parts = []
            if analysis.get('上装'):
                clothes_parts.append(analysis['上装'])
            if analysis.get('下装'):
                clothes_parts.append(analysis['下装'])
            accessories_info['服装'] = '，'.join(clothes_parts)
        
        if analysis.get('手持'):
            accessories_info['手拿'] = analysis['手持']
        
        if analysis.get('头戴'):
            accessories_info['头戴'] = analysis['头戴']
        
        # 使用GenerationController进行统一配件处理
        processed_images = []
        if accessories_info:
            logger.info(f"配饰信息: {accessories_info}")
            
            # 调用实际的统一配件处理
            for image_path in base_images:
                try:
                    processed_image = generation_controller.process_accessories_unified(
                        image_path, accessories_info
                    )
                    if processed_image:
                        processed_images.append(processed_image)
                    else:
                        logger.warning(f"配件处理失败: {image_path}")
                        processed_images.append(image_path)  # 使用原图
                except Exception as e:
                    logger.error(f"配件处理异常: {e}")
                    processed_images.append(image_path)  # 使用原图
        else:
            processed_images = base_images
        
        timer.end("统一配件处理", f"- 处理图片: {len(processed_images)}张")
        
        # 5. Gate质量检查
        timer.start("Gate质量检查")
        
        final_images = []
        for image_path in processed_images:
            try:
                # 调用实际的Gate检查
                is_valid = generation_controller.check_image_quality(image_path)
                if is_valid:
                    final_images.append(image_path)
                    logger.info(f"Gate检查通过: {image_path}")
                else:
                    logger.warning(f"Gate检查不通过: {image_path}")
            except Exception as e:
                logger.error(f"Gate检查异常: {e}")
                final_images.append(image_path)  # 保留图片
        
        timer.end("Gate质量检查", f"- 通过检查: {len(final_images)}张")
        
        # 6. 结果整理和保存
        timer.start("结果整理和保存")
        
        # 整理最终结果
        result_info = {
            'input': test_requirement,
            'analysis': analysis,
            'base_images': base_images,
            'processed_images': processed_images,
            'final_images': final_images,
            'accessories_info': accessories_info
        }
        
        # 保存结果信息
        import json
        result_file = f"output/generation_result_{int(time.time())}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_info, f, ensure_ascii=False, indent=2)
        
        timer.end("结果整理和保存", f"- 结果文件: {result_file}")
        
        # 生成完整性能报告
        generate_end_to_end_report(timer.timings, timer.stage_details, test_requirement, result_info)
        
        return timer.timings
        
    except Exception as e:
        logger.error(f"完整流程测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_end_to_end_report(timings: Dict, details: Dict, test_case: str, result_info: Dict):
    """生成端到端性能报告"""
    
    total_time = sum(timings.values())
    
    logger.info("\n" + "="*80)
    logger.info("完整端到端性能分析报告")
    logger.info("="*80)
    
    logger.info(f"测试用例: {test_case}")
    logger.info(f"📊 总用时: {total_time:.2f}秒")
    
    # 按用时排序
    sorted_stages = sorted(timings.items(), key=lambda x: x[1], reverse=True)
    
    logger.info("\n各环节详细用时:")
    logger.info("-" * 80)
    
    for i, (stage, duration) in enumerate(sorted_stages, 1):
        percentage = (duration / total_time * 100) if total_time > 0 else 0
        detail = details.get(stage, "")
        logger.info(f"{i:2d}. {stage:<25} {duration:>8.2f}秒 ({percentage:>5.1f}%) {detail}")
    
    # 输出生成结果统计
    logger.info("\n📊 生成结果统计:")
    logger.info("-" * 80)
    logger.info(f"   基础图片数量: {len(result_info.get('base_images', []))}")
    logger.info(f"   处理后图片数量: {len(result_info.get('processed_images', []))}")
    logger.info(f"   最终图片数量: {len(result_info.get('final_images', []))}")
    logger.info(f"   配件类型: {list(result_info.get('accessories_info', {}).keys())}")
    
    # 分析真实生图流程的瓶颈
    analyze_real_generation_bottlenecks(sorted_stages, total_time)

def analyze_real_generation_bottlenecks(sorted_stages: List, total_time: float):
    """分析真实生图流程的性能瓶颈"""
    
    logger.info("\n" + "="*80)
    logger.info("🔍 真实生图流程瓶颈分析")
    logger.info("="*80)
    
    if not sorted_stages:
        return
    
    # 分析最耗时的环节
    top_stages = sorted_stages[:3]
    
    logger.info("⚠️  最耗时的环节:")
    for i, (stage, duration) in enumerate(top_stages, 1):
        percentage = (duration / total_time * 100) if total_time > 0 else 0
        logger.info(f"  {i}. {stage}: {duration:.2f}秒 ({percentage:.1f}%)")
    
    # 真实生图流程优化建议
    logger.info("\n💡 真实生图流程优化建议:")
    logger.info("-" * 80)
    
    real_optimization_map = {
        "内容合规检查和分析": [
            "🚀 实现智能缓存，相似内容复用分析结果",
            "🚀 并行执行违规词检查和AI分析",
            "🚀 使用更快的AI模型",
            "🚀 优化prompt设计，减少token消耗"
        ],
        "统一配件处理": [
            "🚀 使用更快的AI模型（如Gemini-2.5-flash）",
            "🚀 批量处理多张图片，减少API调用次数",
            "🚀 实现请求缓存，相同配件复用结果",
            "🚀 使用CDN加速API访问",
            "🚀 优化prompt长度，减少token消耗"
        ],
        "基础图片生成": [
            "🚀 并行处理多个head和body组合",
            "🚀 使用GPU加速图片合成",
            "🚀 预生成常用组合，减少实时处理",
            "🚀 优化图片处理算法和参数"
        ],
        "Gate质量检查": [
            "🚀 并行检查多张图片",
            "🚀 使用轻量级检查模型",
            "🚀 设置检查阈值，跳过明显合格的图片",
            "🚀 实现检查结果缓存"
        ]
    }
    
    for stage, duration in top_stages:
        if stage in real_optimization_map:
            logger.info(f"\n📌 {stage} 优化建议:")
            for suggestion in real_optimization_map[stage]:
                logger.info(f"   {suggestion}")
    
    # 整体流程优化策略
    logger.info("\n🎯 整体流程优化策略:")
    logger.info("-" * 80)
    logger.info("   🚀 实现流水线处理，边分析边生成")
    logger.info("   🚀 使用消息队列，解耦各个处理环节")
    logger.info("   🚀 部署微服务架构，独立扩展各模块")
    logger.info("   🚀 实现渐进式响应，优先返回预览结果")
    logger.info("   🚀 使用负载均衡，分散API调用压力")
    
    # 预期真实优化效果
    estimate_real_optimization_impact(sorted_stages, total_time)

def estimate_real_optimization_impact(sorted_stages: List, current_time: float):
    """估算真实优化效果"""
    
    logger.info("\n📈 真实优化效果预估:")
    logger.info("-" * 80)
    
    # 基于真实API调用的优化估算
    real_optimization_factors = {
        "内容合规检查和分析": 0.3,    # 缓存和并行可减少70%
        "统一配件处理": 0.4,         # 更快模型和缓存可减少60%
        "基础图片生成": 0.5,         # 并行和预生成可减少50%
        "Gate质量检查": 0.4,         # 并行和轻量模型可减少60%
        "系统初始化": 0.5,           # 单例和预热可减少50%
        "结果整理和保存": 0.7         # 优化算法可减少30%
    }
    
    optimized_time = 0
    for stage, duration in sorted_stages:
        factor = real_optimization_factors.get(stage, 0.8)  # 默认减少20%
        optimized_duration = duration * factor
        optimized_time += optimized_duration
        
        improvement = (1 - factor) * 100
        logger.info(f"   {stage:<25} {duration:.2f}s → {optimized_duration:.2f}s (-{improvement:.0f}%)")
    
    total_improvement = ((current_time - optimized_time) / current_time * 100) if current_time > 0 else 0
    
    logger.info("-" * 80)
    logger.info(f"   当前总用时: {current_time:.2f}秒")
    logger.info(f"   优化后预估: {optimized_time:.2f}秒")
    logger.info(f"   总体提升: {total_improvement:.1f}%")
    
    # 关键成功指标
    logger.info("\n🎯 关键成功指标:")
    logger.info("-" * 80)
    logger.info("   📊 性能指标:")
    logger.info("     - 总响应时间 < 60秒")
    logger.info("     - API调用次数减少 > 50%")
    logger.info("     - 缓存命中率 > 70%")
    logger.info("     - 图片生成成功率 > 95%")
    logger.info("   📊 质量指标:")
    logger.info("     - 图片质量评分 > 4.0/5.0")
    logger.info("     - 配件匹配准确率 > 90%")
    logger.info("     - 系统稳定性 > 99.9%")

if __name__ == "__main__":
    logger.info("完整端到端图片生成流程测试启动")
    
    # 确认是否进行完整测试
    logger.info("⚠️  此测试将进行真实的图片生成，包括API调用")
    choice = input("是否继续？(y/N): ").strip().lower()
    
    if choice == 'y':
        test_complete_generation_flow()
    else:
        logger.info("测试已取消")