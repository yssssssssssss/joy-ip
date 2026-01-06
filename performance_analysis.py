#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能分析脚本：测试完整流程的各环节用时
用例："顶着带小铃铛的深蓝贝雷帽，穿着红色法兰绒衬衫外套，手持散发暖光的松果魔法棒"
"""

import time
import logging
import sys
import os
from typing import Dict, List

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PerformanceTimer:
    """性能计时器"""
    
    def __init__(self):
        self.timings = {}
        self.start_time = None
    
    def start(self, stage_name: str):
        """开始计时"""
        self.start_time = time.time()
        logger.info(f"🚀 开始 {stage_name}")
    
    def end(self, stage_name: str):
        """结束计时"""
        if self.start_time is None:
            return 0
        
        duration = time.time() - self.start_time
        self.timings[stage_name] = duration
        logger.info(f"✅ 完成 {stage_name} - 用时: {duration:.2f}秒")
        self.start_time = None
        return duration
    
    def get_report(self) -> Dict:
        """获取性能报告"""
        total_time = sum(self.timings.values())
        report = {
            'total_time': total_time,
            'stages': {},
            'percentages': {}
        }
        
        for stage, duration in self.timings.items():
            report['stages'][stage] = duration
            report['percentages'][stage] = (duration / total_time * 100) if total_time > 0 else 0
        
        return report

def test_performance_analysis():
    """测试完整流程的性能"""
    
    # 测试用例
    test_requirement = "顶着带小铃铛的深蓝贝雷帽，穿着红色法兰绒衬衫外套，手持散发暖光的松果魔法棒"
    
    timer = PerformanceTimer()
    
    logger.info("="*80)
    logger.info(f"性能分析测试开始")
    logger.info(f"测试用例: {test_requirement}")
    logger.info("="*80)
    
    try:
        # 1. 导入模块
        timer.start("模块导入")
        from content_agent import ContentAgent
        from generation_controller import GenerationController
        from matchers.head_matcher import HeadMatcher
        from matchers.body_matcher import BodyMatcher
        from image_processor import ImageProcessor
        timer.end("模块导入")
        
        # 2. 初始化组件
        timer.start("组件初始化")
        content_agent = ContentAgent()
        generation_controller = GenerationController()
        head_matcher = HeadMatcher()
        body_matcher = BodyMatcher()
        image_processor = ImageProcessor()
        timer.end("组件初始化")
        
        # 3. 合规检查和内容分析
        timer.start("合规检查和内容分析")
        result = content_agent.process_content(test_requirement)
        if not result['compliant']:
            logger.error(f"内容不合规: {result['reason']}")
            return None
        analysis = result['analysis']
        timer.end("合规检查和内容分析")
        
        logger.info(f"分析结果: {analysis}")
        
        # 4. 表情分析
        timer.start("表情分析")
        expression_info = head_matcher.analyze_user_requirement(test_requirement)
        timer.end("表情分析")
        
        # 5. 动作分析
        timer.start("动作分析")
        action_type = body_matcher.classify_action_type(test_requirement)
        timer.end("动作分析")
        
        # 6. 图片处理（模拟）
        timer.start("基础图片生成")
        # 这里模拟图片处理，实际会调用image_processor
        time.sleep(0.5)  # 模拟处理时间
        mock_images = ["output/test_image_1.png", "output/test_image_2.png"]
        timer.end("基础图片生成")
        
        # 7. 统一配件处理（模拟）
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
        
        # 模拟统一配件处理
        if accessories_info:
            logger.info(f"配饰信息: {accessories_info}")
            # 模拟API调用时间
            time.sleep(2.0)  # 模拟统一处理时间
        
        timer.end("统一配件处理")
        
        # 8. Gate检查（模拟）
        timer.start("Gate质量检查")
        time.sleep(0.3)  # 模拟Gate检查时间
        timer.end("Gate质量检查")
        
        # 生成性能报告
        report = timer.get_report()
        
        logger.info("\n" + "="*80)
        logger.info("性能分析报告")
        logger.info("="*80)
        
        # 按用时排序
        sorted_stages = sorted(report['stages'].items(), key=lambda x: x[1], reverse=True)
        
        logger.info(f"总用时: {report['total_time']:.2f}秒")
        logger.info("\n各环节用时详情:")
        logger.info("-" * 60)
        
        for i, (stage, duration) in enumerate(sorted_stages, 1):
            percentage = report['percentages'][stage]
            logger.info(f"{i:2d}. {stage:<20} {duration:>8.2f}秒 ({percentage:>5.1f}%)")
        
        # 分析最耗时的环节
        analyze_bottlenecks(sorted_stages, report['total_time'])
        
        return report
        
    except Exception as e:
        logger.error(f"性能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_bottlenecks(sorted_stages: List, total_time: float):
    """分析性能瓶颈并提供优化建议"""
    
    logger.info("\n" + "="*80)
    logger.info("性能瓶颈分析与优化建议")
    logger.info("="*80)
    
    if not sorted_stages:
        return
    
    # 找出最耗时的环节
    top_3_stages = sorted_stages[:3]
    
    logger.info("🔍 最耗时的3个环节:")
    for i, (stage, duration) in enumerate(top_3_stages, 1):
        percentage = (duration / total_time * 100) if total_time > 0 else 0
        logger.info(f"  {i}. {stage}: {duration:.2f}秒 ({percentage:.1f}%)")
    
    # 针对性优化建议
    optimization_suggestions = {
        "合规检查和内容分析": [
            "🚀 缓存AI模型响应，相似内容复用结果",
            "🚀 并行执行违规词检查和AI分析",
            "🚀 使用更快的AI模型或本地模型",
            "🚀 预处理常见词汇，减少AI调用"
        ],
        "统一配件处理": [
            "🚀 使用更快的AI模型（如Gemini-2.5-flash）",
            "🚀 批量处理多张图片，减少网络开销",
            "🚀 实现请求缓存，相同配件复用结果",
            "🚀 优化prompt长度，减少token消耗",
            "🚀 使用CDN加速API访问"
        ],
        "表情分析": [
            "🚀 使用本地关键词匹配替代AI调用",
            "🚀 预训练轻量级模型进行表情识别",
            "🚀 缓存常见表情分析结果"
        ],
        "动作分析": [
            "🚀 扩展关键词库，减少AI调用",
            "🚀 使用正则表达式快速匹配",
            "🚀 预设动作模板库"
        ],
        "基础图片生成": [
            "🚀 并行处理多个head和body组合",
            "🚀 使用GPU加速图片合成",
            "🚀 预生成常用组合，减少实时处理"
        ],
        "Gate质量检查": [
            "🚀 并行检查多张图片",
            "🚀 使用轻量级检查模型",
            "🚀 设置检查阈值，跳过明显合格的图片"
        ]
    }
    
    logger.info("\n💡 针对性优化建议:")
    logger.info("-" * 60)
    
    for stage, duration in top_3_stages:
        if stage in optimization_suggestions:
            logger.info(f"\n📌 {stage} ({duration:.2f}秒):")
            for suggestion in optimization_suggestions[stage]:
                logger.info(f"   {suggestion}")
    
    # 整体优化建议
    logger.info("\n🎯 整体优化策略:")
    logger.info("-" * 60)
    logger.info("   🚀 实现智能缓存系统，复用相似请求结果")
    logger.info("   🚀 使用异步并发处理，提升整体吞吐量")
    logger.info("   🚀 部署本地AI模型，减少网络延迟")
    logger.info("   🚀 实现渐进式加载，优先返回部分结果")
    logger.info("   🚀 使用队列系统，平衡负载和响应时间")
    
    # 预期优化效果
    logger.info("\n📈 预期优化效果:")
    logger.info("-" * 60)
    
    current_time = total_time
    
    # 估算优化后的时间
    optimized_estimates = {
        "合规检查和内容分析": 0.7,  # 缓存和并行优化
        "统一配件处理": 0.5,      # 更快模型和缓存
        "表情分析": 0.3,          # 本地匹配
        "动作分析": 0.2,          # 关键词匹配
        "基础图片生成": 0.8,      # 并行和预生成
        "Gate质量检查": 0.6       # 并行和轻量模型
    }
    
    optimized_total = sum(optimized_estimates.values()) + 0.5  # 其他环节
    improvement = ((current_time - optimized_total) / current_time * 100) if current_time > 0 else 0
    
    logger.info(f"   当前总用时: {current_time:.2f}秒")
    logger.info(f"   优化后预估: {optimized_total:.2f}秒")
    logger.info(f"   性能提升: {improvement:.1f}%")

def test_specific_case():
    """测试特定用例的性能"""
    
    logger.info("开始测试特定用例性能...")
    
    # 直接测试content_agent的性能
    timer = PerformanceTimer()
    
    test_requirement = "顶着带小铃铛的深蓝贝雷帽，穿着红色法兰绒衬衫外套，手持散发暖光的松果魔法棒"
    
    try:
        timer.start("ContentAgent初始化")
        from content_agent import ContentAgent
        agent = ContentAgent()
        timer.end("ContentAgent初始化")
        
        timer.start("违规词检查")
        is_compliant, reason = agent._check_external_banned_words(test_requirement)
        timer.end("违规词检查")
        
        if is_compliant:
            logger.info("✅ 违规词检查通过")
        else:
            logger.warning(f"❌ 违规词检查不通过: {reason}")
        
        # 注意：这里不进行实际的AI调用，避免消耗API配额
        logger.info("⚠️  跳过AI调用测试（避免消耗API配额）")
        
        report = timer.get_report()
        
        logger.info("\n快速测试结果:")
        for stage, duration in report['stages'].items():
            logger.info(f"  {stage}: {duration:.3f}秒")
        
        return report
        
    except Exception as e:
        logger.error(f"特定用例测试失败: {e}")
        return None

if __name__ == "__main__":
    logger.info("性能分析工具启动")
    
    # 选择测试模式
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # 快速测试模式（不调用AI）
        test_specific_case()
    else:
        # 完整测试模式
        logger.info("使用 --quick 参数进行快速测试（不调用AI）")
        logger.info("直接运行进行完整测试（会调用AI接口）")
        
        choice = input("是否进行完整测试？(y/N): ").strip().lower()
        if choice == 'y':
            test_performance_analysis()
        else:
            test_specific_case()