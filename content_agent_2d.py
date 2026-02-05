#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2D素材生成的内容合规检查和分析Agent
功能：
1. 复用ContentAgent的合规检查能力（敏感词检查、AI敏感内容检查）
2. 复用ContentAgent的内容分析能力
3. 新增"视角"维度的分析能力
"""

import re
import logging
from typing import Dict, Tuple

from content_agent import ContentAgent
from utils.analysis_cache import analysis_cache

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='[ContentAgent2D] %(message)s')


class ContentAgent2D(ContentAgent):
    """2D素材生成的内容分析Agent"""
    
    # 视角关键词映射
    PERSPECTIVE_KEYWORDS = {
        "正视角": ["正视角", "正面", "平视", "正视"],
        "仰视角": ["仰视角", "仰视", "俯视角", "俯视", "从上往下", "从下往上", "upview"]
    }
    
    def __init__(self):
        """初始化2D内容分析Agent"""
        super().__init__()
        logger.info("ContentAgent2D 初始化完成")

    def _analyze_content_combined(self, content: str) -> Dict[str, str]:
        result = {
            "表情": "",
            "动作": "",
            "上装": "",
            "下装": "",
            "头戴": "",
            "手持": ""
        }

        logger.info("开始合并分析2D内容: %s", content)

        cache_key = f"2D::{content}"
        cached_result = analysis_cache.get(cache_key)
        if cached_result:
            logger.info("✅ 命中2D缓存，跳过AI分析")
            return cached_result

        action_type = self._quick_action_match(content)
        result["动作"] = action_type

        is_theme_request = self._is_theme_request(content)

        try:
            if is_theme_request:
                prompt = f"""请分析以下用户描述，完成三个任务：

用户描述："{content}"

【任务1：合规检查】
检查内容是否涉及以下敏感话题：
- 政治相关：政治人物、政治事件、政治口号
- 民族相关：特定民族及其传统服饰、民族冲突
- 国家相关：国旗、国徽、政治象征
- 女装相关：女装、裙子、婚纱等女性服装

【任务2：2D装扮提取与简洁补全】
这是一个 2D 素材生成需求，请：
1. 提取用户明确描述的装扮
2. 根据主题风格，为未提及的维度进行“简洁、纯色”的补全

风格要求（必须严格遵守）：
- 上装、下装、头戴必须是：简单、纯色、无图案、无文字、无Logo、无复杂装饰
- 输出只写“颜色 + 类型”，不要添加材质细节、花纹、配饰堆叠
- 下装只能是裤子类，不能是裙子
- 手持如果用户未提及，填“无”，不要自行补全手持

维度说明：
- 表情：面部表情（如开心、微笑、惊讶等）
- 上装：上半身穿着的衣物
- 下装：下半身穿着的衣物（裤子类）
- 头戴：头上佩戴的物品（如帽子、头饰等）
- 手持：手中拿着的物品（如道具、工具等）

请严格按以下格式输出（每个维度都要填写，根据主题补全）：
合规：是/否
不合规原因：xxx（如果合规则填"无"）
表情：xxx
上装：xxx
下装：xxx
头戴：xxx
手持：xxx"""
            else:
                prompt = f"""请分析以下用户描述，完成两个任务：

用户描述："{content}"

【任务1：合规检查】
检查内容是否涉及以下敏感话题：
- 政治相关：政治人物、政治事件、政治口号
- 民族相关：特定民族及其传统服饰、民族冲突
- 国家相关：国旗、国徽、政治象征
- 女装相关：女装、裙子、婚纱等女性服装

【任务2：2D装扮提取与简洁补全】
提取角色的装扮信息，并按“简洁、纯色”原则补全上装/下装：

要求（必须严格遵守）：
- 上装、下装、头戴必须是：简单、纯色、无图案、无文字、无Logo、无复杂装饰
- 输出只写“颜色 + 类型”，不要添加材质细节、花纹、配饰堆叠
- 下装只能是裤子类，不能是裙子
- 表情未提及填"无"
- 头戴未提及填"无"
- 手持未提及填"无"，不要自行补全手持

补全规则：
- 如果用户只提到上装没提到下装，请补全一个协调的“纯色裤子”
- 如果用户只提到下装没提到上装，请补全一个协调的“纯色上装”
- 如果用户上装和下装都未提及，请默认补全：
  上装：纯色T恤
  下装：纯色休闲长裤

请严格按以下格式输出：
合规：是/否
不合规原因：xxx（如果合规则填"无"）
表情：xxx
上装：xxx
下装：xxx
头戴：xxx
手持：xxx"""

            logger.info(f"合并AI分析使用模型: {self.analysis_model}")
            ai_text = self._call_llm_text(
                self.analysis_model,
                "你是专业的内容审核和美术指导，擅长检查内容合规性、提取2D角色装扮信息并进行简洁纯色搭配。",
                prompt
            )

            if ai_text:
                logger.info(f"AI合并分析原文: {ai_text}")

                if "合规：否" in ai_text or "合规:否" in ai_text:
                    reason_match = re.search(r"不合规原因[：:]\s*([^\n]+)", ai_text)
                    reason = reason_match.group(1).strip() if reason_match else "内容不合规"
                    if reason != "无":
                        result["_compliance_failed"] = True
                        result["_compliance_reason"] = f"敏感内容检测：{reason}"
                        return result

                field_patterns = {
                    "表情": r"表情[：:]\s*([^\n]+)",
                    "上装": r"上装[：:]\s*([^\n]+)",
                    "下装": r"下装[：:]\s*([^\n]+)",
                    "头戴": r"头戴[：:]\s*([^\n]+)",
                    "手持": r"手持[：:]\s*([^\n]+)"
                }

                for key, pattern in field_patterns.items():
                    match = re.search(pattern, ai_text)
                    if match:
                        value = match.group(1).strip()
                        if value and value not in ["无", "没有", "未提及", "未知", "未设置"]:
                            value = re.sub(r'\*\*([^*]+)\*\*', r'\1', value)
                            value = re.sub(r'\*([^*]+)\*', r'\1', value)
                            value = re.sub(r'^[\*\-\+]\s*', '', value)
                            value = value.strip()
                            result[key] = value
        except Exception as e:
            logger.error(f"AI合并分析失败: {e}")

        has_valid_result = any(
            result.get(key) for key in ["表情", "上装", "下装", "头戴", "手持"]
        )

        if not result.get("_compliance_failed") and has_valid_result:
            analysis_cache.set(cache_key, result)
            logger.info("✅ 2D分析结果已缓存")
        elif not has_valid_result:
            logger.warning("⚠️ 2D分析结果为空，不缓存")

        logger.info("最终2D分析结果: %s", result)
        return result
    
    def analyze_perspective(self, content: str) -> str:
        """
        分析用户输入中的视角信息
        
        Args:
            content: 用户输入内容
            
        Returns:
            str: 识别到的视角（正视角/仰视角），默认为正视角
        """
        content_lower = content.lower()
        
        # 检查仰视角关键词
        for keyword in self.PERSPECTIVE_KEYWORDS["仰视角"]:
            if keyword in content_lower:
                logger.info(f"识别到仰视角关键词: {keyword}")
                return "仰视角"
        
        # 检查正视角关键词
        for keyword in self.PERSPECTIVE_KEYWORDS["正视角"]:
            if keyword in content_lower:
                logger.info(f"识别到正视角关键词: {keyword}")
                return "正视角"
        
        # 默认返回正视角
        logger.info("未识别到视角关键词，默认使用正视角")
        return "正视角"
    
    def process_content_2d(self, content: str, perspective: str = None) -> Dict:
        """
        处理2D内容的主函数（优化版：合并AI调用）
        
        Args:
            content: 待处理的内容
            perspective: 用户选择的视角
            
        Returns:
            Dict: 处理结果，包含合规检查和内容分析
        """
        # 1. 先进行本地违规词检查（快速）
        is_compliant, reason = self._check_external_banned_words(content)
        if not is_compliant:
            return {
                "success": False,
                "compliant": False,
                "reason": f"违规词检测：{reason}",
                "analysis": None
            }
        
        # 2. 合并AI调用：同时进行敏感检查和内容分析
        try:
            analysis = self._analyze_content_combined(content)
            if analysis.get("_compliance_failed"):
                return {
                    "success": False,
                    "compliant": False,
                    "reason": analysis.get("_compliance_reason", "内容不合规"),
                    "analysis": None
                }
            
            # 移除内部标记
            analysis.pop("_compliance_failed", None)
            analysis.pop("_compliance_reason", None)
            
            # 3. 处理视角（2D特有）
            if perspective and perspective in ["正视角", "仰视角"]:
                analysis["视角"] = perspective
                logger.info(f"使用用户指定的视角: {perspective}")
            else:
                # 自动从内容中识别视角
                analysis["视角"] = self.analyze_perspective(content)
            
            return {
                "success": True,
                "compliant": True,
                "reason": "",
                "analysis": analysis
            }
        except Exception as e:
            logger.error(f"2D内容处理失败: {e}")
            return {
                "success": False,
                "compliant": True,
                "reason": "",
                "analysis": {
                    "表情": "",
                    "动作": "站姿",
                    "视角": perspective or "正视角",
                    "上装": "",
                    "下装": "",
                    "头戴": "",
                    "手持": ""
                }
            }


if __name__ == "__main__":
    # 测试代码
    agent = ContentAgent2D()
    
    # 测试内容
    test_cases = [
        ("我想要一个开心的跳跃动作", None),
        ("正面站立的形象", None),
        ("仰视角的奔跑姿态", None),
        ("一个微笑的角色", "仰视角"),
    ]
    
    logger.info("=" * 60)
    for content, perspective in test_cases:
        logger.info(f"测试内容: {content}, 指定视角: {perspective}")
        result = agent.process_content_2d(content, perspective)
        logger.info(f"处理结果: {result}")
        logger.info("-" * 40)
