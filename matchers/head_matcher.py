#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
头像匹配器类
专门处理头像表情分析和匹配
"""

import re
from typing import Dict, List, Optional, Callable
from .base_matcher import BaseMatcher


class HeadMatcher(BaseMatcher):
    """头像匹配器类"""
    
    def __init__(self):
        """初始化头像匹配器"""
        super().__init__()
        self.dimensions = ["眼睛形状", "嘴型", "表情", "脸部动态", "情感强度"]
        self.load_excel_data("data/joy_head.xlsx")
    
    def analyze_user_requirement(self, requirement: str) -> Dict[str, str]:
        """分析用户需求，提取五个维度的特征"""
        try:
            prompt = f"""将"{requirement}"按照"眼睛形状、嘴型、表情、脸部动态、情感强度"五个维度进行分析，精简得到的结果，并将结果按照以下形式输出：
                眼睛形状：
                嘴型：
                表情：
                脸部动态：
                情感强度："""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-0806",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的需求分析专家。请根据用户的需求描述，分析出对应的视觉特征。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            analysis_text = response.choices[0].message.content
            return self._parse_requirement_analysis(analysis_text)
            
        except Exception as e:
            print(f"分析用户需求失败: {str(e)}")
            return {dim: "分析失败" for dim in self.dimensions}
    
    def _parse_requirement_analysis(self, analysis_text: str) -> Dict[str, str]:
        """解析需求分析结果"""
        result = {dim: "" for dim in self.dimensions}
        
        patterns = {
            "眼睛形状": r"眼睛形状[：:]\s*([^\n]+)",
            "嘴型": r"嘴型[：:]\s*([^\n]+)",
            "表情": r"表情[：:]\s*([^\n]+)",
            "脸部动态": r"脸部动态[：:]\s*([^\n]+)",
            "情感强度": r"情感强度[：:]\s*([^\n]+)"
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, analysis_text)
            if match:
                result[key] = match.group(1).strip()
            else:
                result[key] = "未识别"
        
        return result
    
    def find_best_matches(self, requirement: str, top_k: int = 3, log_callback: Optional[Callable[[str], None]] = None) -> tuple:
        """找到最匹配的头像图片，返回结果和处理日志；支持日志回调实时输出"""
        if self.df.empty:
            return [], []
        
        # 初始化日志收集
        processing_logs = []
        
        # 分析用户需求
        requirement_features = self.analyze_user_requirement(requirement)
        log_msg = f"头像需求分析结果: {requirement_features}"
        print(log_msg)
        processing_logs.append(log_msg)
        if log_callback:
            log_callback(log_msg)
        
        # 计算每张图片的匹配得分
        scores = []
        processing_logs.append("开始计算头像图片匹配得分...")
        if log_callback:
            log_callback("开始计算头像图片匹配得分...")
        
        for index, row in self.df.iterrows():
            image_features = {dim: str(row.get(dim, '')) for dim in self.dimensions}
            
            dimension_scores = self.calculate_dimension_scores(
                requirement_features, image_features, self.dimensions
            )
            
            # 计算综合得分（五个维度的平均分）
            total_score = sum(dimension_scores.values()) / len(dimension_scores)
            
            # 构建图片路径
            image_name = str(row.get('图片名', ''))
            image_path = f"data/joy_head/{image_name}"
            
            scores.append({
                "image_name": image_name,
                "image_path": image_path,
                "score": total_score,
                "dimension_scores": dimension_scores,
                "features": image_features,
                "requirement_features": requirement_features,
                "type": "head"
            })
            
            log_msg = f"头像图片 {image_name} 综合得分: {total_score:.1f}, 维度得分: {dimension_scores}"
            print(log_msg)
            processing_logs.append(log_msg)
            if log_callback:
                log_callback(log_msg)
        
        # 按得分排序，返回前top_k个
        scores.sort(key=lambda x: x['score'], reverse=True)
        processing_logs.append(f"头像匹配完成，选择前{top_k}个最佳匹配")
        if log_callback:
            log_callback(f"头像匹配完成，选择前{top_k}个最佳匹配")
        
        return scores[:top_k], processing_logs