#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化后端到端性能测试
测试用例："顶着带小铃铛的深蓝贝雷帽，穿着红色法兰绒衬衫外套，手持散发暖光的松果魔法棒"
"""

import time
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Timer:
    def __init__(self):
        self.timings = {}
        self.start_time = None
        self.total_start = None
    
    def start_total(self):
        self.total_start = time.time()
    
    def start(self, stage_name):
        self.start_time = time.time()
        logger.info(f"🚀 开始 {stage_name}")
    
    def end(self, stage_name, details=""):
        if self.start_time is None:
            return 0
        duration = time.time() - self.start_time
        self.timings[stage_name] = duration
        logger.info(f"✅ 完成 {stage_name} - 用时: {duration:.2f}秒 {details}")
        self.start_time = None
        return duration
    
    def get_total_time(self):
        if self.total_start:
            return time.time() - self.total_start
        return sum(self.timings.values())

def run_test():
    test_requirement = "头戴装饰松枝的棕色报童帽，穿着深红色厚针织开衫，手持顶端有发光球体的手杖"
    
    timer = Timer()
    timer.start_total()
    
    logger.info("="*80)
    logger.info("优化后端到端完整生图流程测试")
    logger.info(f"测试用例: {test_requirement}")
    logger.info("="*80)
    
    # 阶段1: 系统初始化
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
    
    # 阶段2: 违规词检查
    timer.start("2.违规词检查")
    is_compliant, reason = content_agent._check_external_banned_words(test_requirement)
    status = "通过" if is_compliant else f"不通过: {reason}"
    timer.end("2.违规词检查", f"- {status}")
    
    # 阶段3: 合并AI分析（敏感检查+六维度分析+智能补全）
    timer.start("3.合并AI分析")
    analysis = content_agent._analyze_content_combined(test_requirement)
    analysis_count = len([k for k, v in analysis.items() if v and not k.startswith('_')])
    timer.end("3.合并AI分析", f"- 分析维度: {analysis_count}")
    logger.info(f"分析结果: {analysis}")
    
    # 阶段4: 表情动作分析
    timer.start("4.表情动作分析")
    expression_info = head_matcher.analyze_user_requirement(test_requirement)
    action_type = body_matcher.classify_action_type(test_requirement)
    expr = expression_info.get("表情", "未识别")
    timer.end("4.表情动作分析", f"- 表情: {expr}, 动作: {action_type}")
    
    # 阶段5: 基础图片生成
    timer.start("5.基础图片生成")
    processor_result = image_processor.process_user_requirement(test_requirement)
    base_images = processor_result.get('combined_images', [])
    timer.end("5.基础图片生成", f"- 生成图片: {len(base_images)}张")
    
    # 阶段6: 统一配件处理
    timer.start("6.统一配件处理")
    accessories_info = {}
    clothes_parts = []
    if analysis.get('上装'):
        clothes_parts.append(analysis['上装'])
    if analysis.get('下装'):
        clothes_parts.append(analysis['下装'])
    if clothes_parts:
        accessories_info['服装'] = '，'.join(clothes_parts)
    if analysis.get('手持'):
        accessories_info['手拿'] = analysis['手持']
    if analysis.get('头戴'):
        accessories_info['头戴'] = analysis['头戴']
    
    logger.info(f"配饰信息: {accessories_info}")
    
    if accessories_info and base_images:
        processed_images = generation_controller.process_accessories_unified(base_images, accessories_info)
        timer.end("6.统一配件处理", f"- 处理图片: {len(processed_images)}张")
    else:
        processed_images = base_images
        timer.end("6.统一配件处理", "- 跳过")
    
    # 阶段7: Gate质量检查
    timer.start("7.Gate质量检查")
    final_images = generation_controller.final_gate_check(processed_images)
    timer.end("7.Gate质量检查", f"- 通过: {len(final_images)}/{len(processed_images)}张")
    
    # 最终报告
    total_time = timer.get_total_time()
    logger.info("")
    logger.info("="*80)
    logger.info("📊 优化后性能分析报告")
    logger.info("="*80)
    logger.info(f"📊 总用时: {total_time:.2f}秒")
    logger.info("")
    logger.info("各环节详细用时:")
    logger.info("-" * 80)
    
    sorted_stages = sorted(timer.timings.items(), key=lambda x: x[1], reverse=True)
    for i, (stage, duration) in enumerate(sorted_stages, 1):
        percentage = (duration / total_time * 100) if total_time > 0 else 0
        logger.info(f"{i:2d}. {stage:<25} {duration:>8.2f}秒 ({percentage:>5.1f}%)")
    
    logger.info("")
    logger.info("📊 生成结果统计:")
    logger.info(f"   基础图片数量: {len(base_images)}")
    logger.info(f"   处理后图片数量: {len(processed_images)}")
    logger.info(f"   最终图片数量: {len(final_images)}")
    logger.info(f"   配件类型: {list(accessories_info.keys())}")
    
    # 与优化前对比
    logger.info("")
    logger.info("="*80)
    logger.info("📈 优化前后对比")
    logger.info("="*80)
    
    # 优化前基线数据
    baseline = {
        "1.系统初始化": 3.89,
        "2.违规词检查": 0.00,
        "3.AI敏感内容检查": 17.28,
        "4.AI内容分析": 37.57,
        "5.表情动作分析": 12.61,
        "6.基础图片生成": 22.01,
        "7.统一配件处理": 104.47,
        "8.Gate质量检查": 80.00
    }
    baseline_total = sum(baseline.values())
    
    # 映射当前阶段到基线阶段
    stage_mapping = {
        "1.系统初始化": "1.系统初始化",
        "2.违规词检查": "2.违规词检查",
        "3.合并AI分析": ["3.AI敏感内容检查", "4.AI内容分析"],  # 合并了两个阶段
        "4.表情动作分析": "5.表情动作分析",
        "5.基础图片生成": "6.基础图片生成",
        "6.统一配件处理": "7.统一配件处理",
        "7.Gate质量检查": "8.Gate质量检查"
    }
    
    logger.info(f"{'阶段':<25} {'优化前':>10} {'优化后':>10} {'节省':>10} {'改善':>8}")
    logger.info("-" * 70)
    
    total_saved = 0
    for stage, duration in timer.timings.items():
        mapping = stage_mapping.get(stage)
        if isinstance(mapping, list):
            before = sum(baseline.get(m, 0) for m in mapping)
        else:
            before = baseline.get(mapping, 0)
        
        saved = before - duration
        total_saved += saved
        improvement = (saved / before * 100) if before > 0 else 0
        
        logger.info(f"{stage:<25} {before:>8.2f}秒 {duration:>8.2f}秒 {saved:>8.2f}秒 {improvement:>6.1f}%")
    
    logger.info("-" * 70)
    total_improvement = (total_saved / baseline_total * 100) if baseline_total > 0 else 0
    logger.info(f"{'总计':<25} {baseline_total:>8.2f}秒 {total_time:>8.2f}秒 {total_saved:>8.2f}秒 {total_improvement:>6.1f}%")
    
    # 记录生成日志
    try:
        from utils.generation_log import log_generation
        log_generation(
            prompt=test_requirement,
            images=final_images,
            analysis=analysis,
            status="success" if final_images else "failed",
            duration=total_time,
            extra={"test_mode": True}
        )
        logger.info("✅ 生成记录已保存到 logs/generation_history.jsonl")
    except Exception as e:
        logger.warning(f"记录生成日志失败: {e}")
    
    return timer.timings

if __name__ == "__main__":
    run_test()
