#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细性能测试：实际测试AI调用的用时
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

class DetailedTimer:
    """详细计时器"""
    
    def __init__(self):
        self.timings = {}
        self.start_time = None
        self.stage_details = {}
    
    def start(self, stage_name: str):
        """开始计时"""
        self.start_time = time.time()
        logger.info(f"⏱️  开始 {stage_name}")
    
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

def test_real_performance():
    """测试真实的性能表现"""
    
    test_requirement = "顶着带小铃铛的深蓝贝雷帽，穿着红色法兰绒衬衫外套，手持散发暖光的松果魔法棒"
    
    timer = DetailedTimer()
    
    logger.info("="*80)
    logger.info("详细性能测试开始")
    logger.info(f"测试用例: {test_requirement}")
    logger.info("="*80)
    
    try:
        # 1. 模块导入和初始化
        timer.start("系统初始化")
        from content_agent import ContentAgent
        content_agent = ContentAgent()
        timer.end("系统初始化")
        
        # 2. 违规词检查
        timer.start("违规词检查")
        is_compliant, reason = content_agent._check_external_banned_words(test_requirement)
        timer.end("违规词检查", f"- 结果: {'通过' if is_compliant else '不通过'}")
        
        if not is_compliant:
            logger.error(f"违规词检查不通过: {reason}")
            return None
        
        # 3. AI敏感内容检查
        timer.start("AI敏感内容检查")
        is_sensitive, sensitive_reason = content_agent._check_sensitive_content_with_ai(test_requirement)
        timer.end("AI敏感内容检查", f"- 结果: {'通过' if is_sensitive else '不通过'}")
        
        # 4. AI内容分析
        timer.start("AI内容分析")
        analysis = content_agent._analyze_content_combined(test_requirement)
        timer.end("AI内容分析", f"- 分析维度: {len([k for k, v in analysis.items() if v and not k.startswith('_')])}")
        
        logger.info(f"分析结果: {analysis}")
        
        # 5. 表情和动作分析
        timer.start("表情动作分析")
        try:
            from matchers.head_matcher import HeadMatcher
            from matchers.body_matcher import BodyMatcher
            
            head_matcher = HeadMatcher()
            body_matcher = BodyMatcher()
            
            expression_info = head_matcher.analyze_user_requirement(test_requirement)
            action_type = body_matcher.classify_action_type(test_requirement)
            
            timer.end("表情动作分析", f"- 表情: {expression_info.get('表情', '未识别')}, 动作: {action_type}")
        except Exception as e:
            timer.end("表情动作分析", f"- 错误: {str(e)}")
        
        # 6. 统一配件处理模拟
        timer.start("配件处理准备")
        
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
        
        timer.end("配件处理准备", f"- 配件类型: {list(accessories_info.keys())}")
        
        # 7. Prompt构建测试
        timer.start("Prompt构建")
        try:
            # 使用ModuleLoader加载带连字符的模块
            from utils.module_loader import ModuleLoader
            banana_unified = ModuleLoader.load('banana-pro-img-jd.py')
            
            if banana_unified and accessories_info:
                accessories_text = "，".join([f"{k}：{v}" for k, v in accessories_info.items()])
                scene_style = banana_unified._detect_scene_style(accessories_text)
                prompt = banana_unified._build_comprehensive_prompt(accessories_text, "default", scene_style)
                
                timer.end("Prompt构建", f"- 场景: {scene_style}, 长度: {len(prompt)}字符")
            elif not banana_unified:
                timer.end("Prompt构建", "- 错误: 无法加载banana-pro-img-jd模块")
            else:
                timer.end("Prompt构建", "- 跳过（无配件信息）")
        except Exception as e:
            timer.end("Prompt构建", f"- 错误: {str(e)}")
        
        # 生成性能报告
        generate_performance_report(timer.timings, timer.stage_details)
        
        return timer.timings
        
    except Exception as e:
        logger.error(f"性能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_performance_report(timings: Dict, details: Dict):
    """生成详细的性能报告"""
    
    total_time = sum(timings.values())
    
    logger.info("\n" + "="*80)
    logger.info("详细性能分析报告")
    logger.info("="*80)
    
    # 按用时排序
    sorted_stages = sorted(timings.items(), key=lambda x: x[1], reverse=True)
    
    logger.info(f"📊 总用时: {total_time:.2f}秒")
    logger.info("\n各环节详细用时:")
    logger.info("-" * 80)
    
    for i, (stage, duration) in enumerate(sorted_stages, 1):
        percentage = (duration / total_time * 100) if total_time > 0 else 0
        detail = details.get(stage, "")
        logger.info(f"{i:2d}. {stage:<25} {duration:>8.2f}秒 ({percentage:>5.1f}%) {detail}")
    
    # 性能瓶颈分析
    analyze_performance_bottlenecks(sorted_stages, total_time)

def analyze_performance_bottlenecks(sorted_stages: List, total_time: float):
    """分析性能瓶颈"""
    
    logger.info("\n" + "="*80)
    logger.info("🔍 性能瓶颈分析")
    logger.info("="*80)
    
    if not sorted_stages:
        return
    
    # 分析最耗时的环节
    top_stages = sorted_stages[:3]
    
    logger.info("⚠️  最耗时的环节:")
    for i, (stage, duration) in enumerate(top_stages, 1):
        percentage = (duration / total_time * 100) if total_time > 0 else 0
        logger.info(f"  {i}. {stage}: {duration:.2f}秒 ({percentage:.1f}%)")
    
    # 根据实际测试结果提供优化建议
    logger.info("\n💡 基于测试结果的优化建议:")
    logger.info("-" * 80)
    
    optimization_map = {
        "AI敏感内容检查": [
            "🚀 使用更快的AI模型（如GPT-3.5-turbo-instruct）",
            "🚀 实现结果缓存，相似内容复用检查结果",
            "🚀 并行执行多个检查任务",
            "🚀 设置检查阈值，明显安全的内容快速通过"
        ],
        "AI内容分析": [
            "🚀 合并多个AI调用为单次调用（已实现）",
            "🚀 使用流式响应，提前处理部分结果",
            "🚀 优化prompt长度，减少token消耗",
            "🚀 实现智能缓存，相似分析复用结果"
        ],
        "表情动作分析": [
            "🚀 扩展本地关键词库，减少AI调用",
            "🚀 使用预训练的轻量级分类模型",
            "🚀 并行执行表情和动作分析",
            "🚀 缓存常见表情动作组合"
        ],
        "系统初始化": [
            "🚀 使用单例模式，避免重复初始化",
            "🚀 延迟加载非必需组件",
            "🚀 预热系统，提前加载常用模块",
            "🚀 使用连接池管理HTTP连接"
        ]
    }
    
    for stage, duration in top_stages:
        if stage in optimization_map:
            logger.info(f"\n📌 {stage} 优化建议:")
            for suggestion in optimization_map[stage]:
                logger.info(f"   {suggestion}")
    
    # 整体优化策略
    logger.info("\n🎯 整体优化策略:")
    logger.info("-" * 80)
    logger.info("   🚀 实现请求级缓存，避免重复计算")
    logger.info("   🚀 使用异步处理，提升并发能力")
    logger.info("   🚀 部署边缘计算节点，减少网络延迟")
    logger.info("   🚀 实现渐进式响应，优先返回关键信息")
    logger.info("   🚀 使用CDN加速静态资源和API访问")
    
    # 预期优化效果
    estimate_optimization_impact(sorted_stages, total_time)

def estimate_optimization_impact(sorted_stages: List, current_time: float):
    """估算优化效果"""
    
    logger.info("\n📈 预期优化效果:")
    logger.info("-" * 80)
    
    # 基于实际测试结果的优化估算
    optimization_factors = {
        "AI敏感内容检查": 0.4,    # 缓存和更快模型可减少60%
        "AI内容分析": 0.3,        # 优化prompt和缓存可减少70%
        "表情动作分析": 0.2,      # 本地处理可减少80%
        "系统初始化": 0.5,        # 单例和预热可减少50%
        "违规词检查": 0.9,        # 已经很快，优化空间有限
        "配件处理准备": 0.8,      # 逻辑优化可减少20%
        "Prompt构建": 0.7         # 模板优化可减少30%
    }
    
    optimized_time = 0
    for stage, duration in sorted_stages:
        factor = optimization_factors.get(stage, 0.8)  # 默认减少20%
        optimized_duration = duration * factor
        optimized_time += optimized_duration
        
        improvement = (1 - factor) * 100
        logger.info(f"   {stage:<25} {duration:.2f}s → {optimized_duration:.2f}s (-{improvement:.0f}%)")
    
    total_improvement = ((current_time - optimized_time) / current_time * 100) if current_time > 0 else 0
    
    logger.info("-" * 80)
    logger.info(f"   当前总用时: {current_time:.2f}秒")
    logger.info(f"   优化后预估: {optimized_time:.2f}秒")
    logger.info(f"   总体提升: {total_improvement:.1f}%")
    
    # 实施优先级
    logger.info("\n🎯 实施优先级建议:")
    logger.info("-" * 80)
    
    # 根据影响程度排序
    impact_scores = []
    for stage, duration in sorted_stages:
        factor = optimization_factors.get(stage, 0.8)
        time_saved = duration * (1 - factor)
        impact_scores.append((stage, time_saved, (1 - factor) * 100))
    
    impact_scores.sort(key=lambda x: x[1], reverse=True)
    
    for i, (stage, time_saved, improvement) in enumerate(impact_scores[:3], 1):
        logger.info(f"   {i}. 优化 {stage} - 可节省 {time_saved:.2f}秒 ({improvement:.0f}%)")

if __name__ == "__main__":
    logger.info("详细性能测试启动")
    
    # 确认是否进行实际AI调用测试
    logger.info("⚠️  此测试将进行实际的AI调用，可能消耗API配额")
    choice = input("是否继续？(y/N): ").strip().lower()
    
    if choice == 'y':
        test_real_performance()
    else:
        logger.info("测试已取消")