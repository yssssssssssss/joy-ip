#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础匹配器类
提供通用的匹配功能
"""

import os
import pandas as pd
import re
from openai import OpenAI
from typing import Dict, List
import base64


class BaseMatcher:
    """基础匹配器类"""
    
    def __init__(self):
        """初始化匹配器"""
        # 设置OpenAI API凭证
        os.environ["OPENAI_API_KEY"] = "35f54cc4-be7a-4414-808e-f5f9f0194d4f"
        os.environ["OPENAI_API_BASE"] = "http://gpt-proxy.jd.com/gateway/azure"
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ["OPENAI_API_BASE"],
        )
        
        self.df = pd.DataFrame()
    
    def load_excel_data(self, excel_path: str):
        """加载Excel中的图片分析数据"""
        try:
            if os.path.exists(excel_path):
                self.df = pd.read_excel(excel_path)
                print(f"成功加载Excel数据，共{len(self.df)}条记录")
            else:
                print(f"Excel文件不存在: {excel_path}")
                self.df = pd.DataFrame()
        except Exception as e:
            print(f"加载Excel数据失败: {str(e)}")
            self.df = pd.DataFrame()
    
    def calculate_dimension_scores(self, requirement_features: Dict[str, str], 
                                 image_features: Dict[str, str], 
                                 dimensions: List[str]) -> Dict[str, float]:
        """计算各维度的分别得分"""
        try:
            # 构建比较prompt
            req_features_str = "\n".join([f"{dim}：{requirement_features[dim]}" for dim in dimensions])
            img_features_str = "\n".join([f"{dim}：{image_features[dim]}" for dim in dimensions])
            
            comparison_prompt = f"""
请对比以下两组特征在每个维度上的相似度，并分别给出0-100的得分：

用户需求特征：
{req_features_str}

图片特征：
{img_features_str}

请按照以下格式返回每个维度的得分（0-100）：
{chr(10).join([f"{dim}：XX" for dim in dimensions])}
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-0806",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的特征比较专家。请根据两组特征在每个维度上的相似程度分别给出0-100的得分，100表示完全匹配，0表示完全不匹配。"
                    },
                    {
                        "role": "user",
                        "content": comparison_prompt
                    }
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            score_text = response.choices[0].message.content.strip()
            return self._parse_dimension_scores(score_text, dimensions)
                
        except Exception as e:
            print(f"计算维度得分失败: {str(e)}")
            return {dim: 0.0 for dim in dimensions}
    
    def _parse_dimension_scores(self, score_text: str, dimensions: List[str]) -> Dict[str, float]:
        """解析维度得分结果"""
        scores = {dim: 0.0 for dim in dimensions}
        
        for dim in dimensions:
            pattern = rf"{re.escape(dim)}[：:]\s*(\d+)"
            match = re.search(pattern, score_text)
            if match:
                score = float(match.group(1))
                scores[dim] = min(100, max(0, score))  # 确保分数在0-100范围内
        
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
            print(f"处理图片失败 {image_path}: {str(e)}")
            return ""