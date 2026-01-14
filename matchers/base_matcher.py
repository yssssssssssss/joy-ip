#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

import logging

logger = logging.getLogger(__name__)
基础匹配器类
提供通用的匹配功能
"""

import os
import sys
import pandas as pd
import re
from typing import Dict, List
import base64

# 确保能导入项目根目录的 config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_config
from utils.http_client import http_post, parse_ai_response


class BaseMatcher:
    """基础匹配器类"""
    
    def __init__(self):
        """初始化匹配器"""
        # 从统一配置获取 API 信息
        config = get_config()
        self.api_url = config.AI_API_URL
        self.api_token = config.AI_API_KEY
        self.model = config.AI_MODEL
        
        self.df = pd.DataFrame()
    
    def _call_ai(self, system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 500) -> str:
        """
        统一的AI调用方法，使用共享 HTTP Session
        """
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            resp = http_post(self.api_url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            
            # 使用统一的响应解析
            return parse_ai_response(data)
            
        except Exception as e:
            logger.info(f"AI调用失败: {str(e)}")
            return ""
    
    def load_excel_data(self, excel_path: str):
        """加载Excel中的图片分析数据"""
        try:
            if os.path.exists(excel_path):
                self.df = pd.read_excel(excel_path)
                logger.info(f"成功加载Excel数据，共{len(self.df)}条记录")
            else:
                logger.info(f"Excel文件不存在: {excel_path}")
                self.df = pd.DataFrame()
        except Exception as e:
            logger.info(f"加载Excel数据失败: {str(e)}")
            self.df = pd.DataFrame()
    
    def calculate_dimension_scores(self, requirement_features: Dict[str, str], 
                                 image_features: Dict[str, str], 
                                 dimensions: List[str]) -> Dict[str, float]:
        """计算各维度的分别得分"""
        try:
            req_features_str = "\n".join([f"{dim}：{requirement_features.get(dim, '')}" for dim in dimensions])
            img_features_str = "\n".join([f"{dim}：{image_features.get(dim, '')}" for dim in dimensions])
            
            comparison_prompt = f"""请对比以下两组特征在每个维度上的相似度，并分别给出0-100的得分：

用户需求特征：
{req_features_str}

图片特征：
{img_features_str}

请按照以下格式返回每个维度的得分（0-100）：
""" + "\n".join([f"{dim}：XX" for dim in dimensions])
            
            system_prompt = "你是一个专业的特征比较专家。请根据两组特征在每个维度上的相似程度分别给出0-100的得分，100表示完全匹配，0表示完全不匹配。"
            
            score_text = self._call_ai(system_prompt, comparison_prompt, temperature=0.1, max_tokens=200)
            
            if score_text:
                return self._parse_dimension_scores(score_text, dimensions)
            else:
                logger.info("API响应内容无效")
                return {dim: 0.0 for dim in dimensions}
                
        except Exception as e:
            logger.info(f"计算维度得分失败: {str(e)}")
            return {dim: 0.0 for dim in dimensions}
    
    def _parse_dimension_scores(self, score_text: str, dimensions: List[str]) -> Dict[str, float]:
        """解析维度得分结果"""
        scores = {dim: 0.0 for dim in dimensions}
        
        for dim in dimensions:
            pattern = rf"{re.escape(dim)}[：:]\s*(\d+)"
            match = re.search(pattern, score_text)
            if match and match.group(1):
                try:
                    score = float(match.group(1))
                    scores[dim] = min(100, max(0, score))
                except ValueError:
                    scores[dim] = 0.0
        
        return scores
    
    def convert_image_to_base64(self, image_path: str) -> str:
        """将图片转换为base64格式"""
        try:
            if os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                    return f"data:image/png;base64,{image_data}"
            else:
                return ""
        except Exception as e:
            logger.info(f"处理图片失败 {image_path}: {str(e)}")
            return ""
