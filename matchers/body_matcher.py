#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
身体姿势匹配器类
专门处理身体姿势分析和匹配
"""

import re
import logging
from typing import Dict, List, Optional, Callable
from .base_matcher import BaseMatcher

logger = logging.getLogger(__name__)


class BodyMatcher(BaseMatcher):
    """身体姿势匹配器类"""
    
    def __init__(self):
        """初始化身体姿势匹配器"""
        super().__init__()
        self.dimensions = ["手部姿势", "腿部姿势", "整体姿势", "姿势意义", "情感偏向"]
    
    def analyze_user_requirement(self, requirement: str) -> Dict[str, str]:
        """分析用户需求，提取五个维度的特征"""
        try:
            # 先使用关键词匹配和动作分类
            action_type = self.classify_action_type(requirement)
            keyword_result = self._keyword_based_analysis(requirement, action_type)
            
            if any(v != "未识别" for v in keyword_result.values()):
                logger.info(f"使用关键词分析结果: {keyword_result}")
                return keyword_result
            
            # 关键词匹配失败时使用AI分析
            prompt = f"""请分析用户需求："{requirement}"

按照以下五个维度进行分析，并按格式输出：

手部姿势：（描述手部动作，如：挥手、握拳、张开、放松等）
腿部姿势：（描述腿部动作，如：站立、跑动、跳跃、坐着等）
整体姿势：（描述整体身体姿态，如：直立、前倾、后仰、蹲下等）
姿势意义：（描述姿势表达的含义，如：运动、休息、兴奋、专注等）
情感偏向：（描述情感倾向，如：积极、消极、中性、活跃等）

请严格按照上述格式输出，每个维度一行。"""
            
            system_prompt = "你是一个专业的身体姿势分析专家。请根据用户的需求描述，分析出对应的身体姿势特征。"
            
            analysis_text = self._call_ai(system_prompt, prompt, temperature=0.3, max_tokens=500)
            
            if analysis_text:
                return self._parse_requirement_analysis(analysis_text)
            else:
                logger.info("AI分析失败，使用默认值")
                return {dim: "未识别" for dim in self.dimensions}
            
        except Exception as e:
            logger.info(f"分析用户需求失败: {str(e)}")
            return {dim: "分析失败" for dim in self.dimensions}
    
    def _keyword_based_analysis(self, requirement: str, action_type: str) -> Dict[str, str]:
        """基于关键词和动作类型的快速分析"""
        result = {dim: "未识别" for dim in self.dimensions}
        
        # 根据动作类型设置基础特征
        action_mapping = {
            "跑动": {
                "手部姿势": "摆臂",
                "腿部姿势": "跑动",
                "整体姿势": "前倾",
                "姿势意义": "运动",
                "情感偏向": "积极"
            },
            "跳跃": {
                "手部姿势": "张开",
                "腿部姿势": "跳跃",
                "整体姿势": "腾空",
                "姿势意义": "兴奋",
                "情感偏向": "积极"
            },
            "坐姿": {
                "手部姿势": "放松",
                "腿部姿势": "坐着",
                "整体姿势": "端坐",
                "姿势意义": "休息",
                "情感偏向": "中性"
            },
            "欢快": {
                "手部姿势": "挥手",
                "腿部姿势": "活跃",
                "整体姿势": "轻松",
                "姿势意义": "兴奋",
                "情感偏向": "积极"
            },
            "站姿": {
                "手部姿势": "自然",
                "腿部姿势": "站立",
                "整体姿势": "直立",
                "姿势意义": "稳定",
                "情感偏向": "中性"
            }
        }
        
        if action_type in action_mapping:
            result.update(action_mapping[action_type])
            logger.info(f"根据动作类型 '{action_type}' 设置特征")
        
        return result
    
    def classify_action_type(self, requirement: str) -> str:
        """分析用户需求，将其分类到五个动作类型之一：站姿、欢快、坐姿、跳跃、跑动"""
        try:
            # 先用关键词匹配，提高准确性
            requirement_lower = requirement.lower()
            
            # 关键词映射
            keyword_mapping = {
                "跑动": ["跑", "奔跑", "跑步", "奔", "冲刺", "跑动"],
                "跳跃": ["跳", "跳跃", "蹦", "蹦跳", "跳起", "跳高"],
                "坐姿": ["坐", "坐着", "坐下", "坐姿", "坐立"],
                "欢快": ["欢快", "开心", "快乐", "兴奋", "愉快", "高兴", "喜悦"],
                "站姿": ["站", "站立", "站着", "站姿", "直立"]
            }
            
            # 优先使用关键词匹配
            for action_type, keywords in keyword_mapping.items():
                for keyword in keywords:
                    if keyword in requirement_lower:
                        logger.info(f"通过关键词 '{keyword}' 匹配到动作类型: {action_type}")
                        return action_type
            
            # 如果关键词匹配失败，使用AI分析
            prompt = f"""请分析用户需求："{requirement}"
            
将其归类到以下五个动作类型中的一个：
1. 站姿 - 静态站立姿势
2. 欢快 - 快乐、兴奋的动作
3. 坐姿 - 坐着的姿势
4. 跳跃 - 跳跃相关的动作
5. 跑动 - 跑步、奔跑相关的动作

请只返回一个动作类型名称，不要其他解释。"""
            
            system_prompt = "你是一个专业的动作分类专家。请根据用户的需求描述，准确分类到指定的动作类型。"
            
            # 使用父类的_call_ai方法
            action_type = self._call_ai(system_prompt, prompt, temperature=0.1, max_tokens=50)
            
            if action_type:
                action_type = action_type.strip()
                logger.info(f"AI分析结果: '{action_type}'")
                # 确保返回的是有效的动作类型
                valid_actions = ["站姿", "欢快", "坐姿", "跳跃", "跑动"]
                for valid_action in valid_actions:
                    if valid_action in action_type:
                        logger.info(f"AI分析匹配到动作类型: {valid_action}")
                        return valid_action
            
            # 如果都没有匹配到，默认返回站姿
            logger.info("未能匹配到动作类型，默认返回: 站姿")
            return "站姿"
            
        except Exception as e:
            logger.info(f"分类动作类型失败: {str(e)}")
            return "站姿"
    
    def _parse_requirement_analysis(self, analysis_text: str) -> Dict[str, str]:
        """解析需求分析结果"""
        result = {dim: "" for dim in self.dimensions}
        
        patterns = {
            "手部姿势": r"手部姿势[：:]\s*([^\n]+)",
            "腿部姿势": r"腿部姿势[：:]\s*([^\n]+)",
            "整体姿势": r"整体姿势[：:]\s*([^\n]+)",
            "姿势意义": r"姿势意义[：:]\s*([^\n]+)",
            "情感偏向": r"情感偏向[：:]\s*([^\n]+)"
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, analysis_text)
            if match:
                result[key] = match.group(1).strip()
            else:
                result[key] = "未识别"
        
        return result
    
    def find_best_matches(self, requirement: str, top_k: int = 3, 
                         log_callback: Optional[Callable[[str], None]] = None) -> tuple:
        """找到最匹配的身体姿势图片，返回结果和处理日志"""
        if self.df.empty:
            return [], []
        
        processing_logs = []
        
        requirement_features = self.analyze_user_requirement(requirement)
        log_msg = f"身体姿势需求分析结果: {requirement_features}"
        logger.info(log_msg)
        processing_logs.append(log_msg)
        if log_callback:
            log_callback(log_msg)
        
        scores = []
        processing_logs.append("开始计算身体姿势图片匹配得分...")
        if log_callback:
            log_callback("开始计算身体姿势图片匹配得分...")
        
        for index, row in self.df.iterrows():
            image_features = {dim: str(row.get(dim, '')) for dim in self.dimensions}
            
            dimension_scores = self.calculate_dimension_scores(
                requirement_features, image_features, self.dimensions
            )
            
            total_score = sum(dimension_scores.values()) / len(dimension_scores)
            
            image_name = str(row.get('图片名', ''))
            image_path = f"data/joy_body_noface/{image_name}"
            
            scores.append({
                "image_name": image_name,
                "image_path": image_path,
                "score": total_score,
                "dimension_scores": dimension_scores,
                "features": image_features,
                "requirement_features": requirement_features,
                "type": "body"
            })
            
            log_msg = f"身体姿势图片 {image_name} 综合得分: {total_score:.1f}, 维度得分: {dimension_scores}"
            logger.info(log_msg)
            processing_logs.append(log_msg)
            if log_callback:
                log_callback(log_msg)
        
        scores.sort(key=lambda x: x['score'], reverse=True)
        processing_logs.append(f"身体姿势匹配完成，选择前{top_k}个最佳匹配")
        if log_callback:
            log_callback(f"身体姿势匹配完成，选择前{top_k}个最佳匹配")
        
        return scores[:top_k], processing_logs
