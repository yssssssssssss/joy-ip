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
