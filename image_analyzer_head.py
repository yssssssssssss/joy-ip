#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IP头像图片分析脚本
使用GPT-4o分析图片并将结果保存到Excel文件中
"""

import os
import base64
import pandas as pd
from pathlib import Path
from openai import OpenAI
import re
from typing import Dict, List, Optional

class ImageAnalyzer:
    """图片分析器类"""
    
    def __init__(self):
        """初始化分析器"""
        # 设置OpenAI API凭证
        os.environ["OPENAI_API_KEY"] = "35f54cc4-be7a-4414-808e-f5f9f0194d4f"
        os.environ["OPENAI_API_BASE"] = "http://gpt-proxy.jd.com/gateway/azure"
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ["OPENAI_API_BASE"],
        )
        
        # 支持的图片格式
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    
    def encode_image_to_base64(self, image_path: str) -> str:
        """将图片转换为Base64编码"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"编码图片失败 {image_path}: {str(e)}")
            return ""
    
    def analyze_image_with_openai(self, image_path: str) -> Dict[str, str]:
        """使用OpenAI分析图片"""
        try:
            # 将图片转为base64编码
            base64_image = self.encode_image_to_base64(image_path)
            if not base64_image:
                return self._create_error_result("图片编码失败")
            
            # 调用OpenAI API进行图片分析
            response = self.client.chat.completions.create(
                model="gpt-4o-0806",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的图像分析专家。我给你的是IP头像，请按照 '眼睛形状、嘴型、表情、脸部动态、情感强度' 五个维度对图片进行分析，精简结论。请按照以下格式回答：\n眼睛形状：[描述]\n嘴型：[描述]\n表情：[描述]\n脸部动态：[描述]\n情感强度：[描述]"
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "请分析这张IP头像图片，按照眼睛形状、嘴型、表情、脸部动态、情感强度五个维度进行分析。"},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ],
                temperature=0.5,
                max_tokens=1000
            )
            
            # 解析分析结果
            analysis_text = response.choices[0].message.content
            return self._parse_analysis_result(analysis_text)
            
        except Exception as e:
            error_msg = f"分析失败: {str(e)}"
            print(f"分析图片失败 {image_path}: {error_msg}")
            return self._create_error_result(error_msg)
    
    def _parse_analysis_result(self, analysis_text: str) -> Dict[str, str]:
        """解析分析结果文本"""
        result = {
            "眼睛形状": "",
            "嘴型": "",
            "表情": "",
            "脸部动态": "",
            "情感强度": ""
        }
        
        # 使用正则表达式提取各个维度的信息
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
                # 如果没有找到特定格式，尝试从整体文本中提取
                result[key] = "未识别"
        
        return result
    
    def _create_error_result(self, error_msg: str) -> Dict[str, str]:
        """创建错误结果"""
        return {
            "眼睛形状": error_msg,
            "嘴型": error_msg,
            "表情": error_msg,
            "脸部动态": error_msg,
            "情感强度": error_msg
        }
    
    def get_image_files(self, folder_path: str) -> List[str]:
        """获取文件夹中的所有图片文件"""
        image_files = []
        folder = Path(folder_path)
        
        if not folder.exists():
            print(f"文件夹不存在: {folder_path}")
            return image_files
        
        for file_path in folder.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                image_files.append(str(file_path))
        
        return sorted(image_files)
    
    def analyze_folder(self, folder_path: str, output_excel: str = "analysis_results.xlsx") -> None:
        """分析文件夹中的所有图片并保存到Excel"""
        print(f"开始分析文件夹: {folder_path}")
        
        # 获取所有图片文件
        image_files = self.get_image_files(folder_path)
        
        if not image_files:
            print("未找到任何图片文件")
            return
        
        print(f"找到 {len(image_files)} 张图片")
        
        # 存储分析结果
        results = []
        
        for i, image_path in enumerate(image_files, 1):
            print(f"正在分析第 {i}/{len(image_files)} 张图片: {Path(image_path).name}")
            
            # 分析图片
            analysis_result = self.analyze_image_with_openai(image_path)
            
            # 准备Excel行数据
            row_data = {
                "图片名": Path(image_path).name,
                "眼睛形状": analysis_result["眼睛形状"],
                "嘴型": analysis_result["嘴型"],
                "表情": analysis_result["表情"],
                "脸部动态": analysis_result["脸部动态"],
                "情感强度": analysis_result["情感强度"],
                "图片url地址": str(Path(image_path).absolute())
            }
            
            results.append(row_data)
            print(f"分析完成: {Path(image_path).name}")
        
        # 保存到Excel
        self.save_to_excel(results, output_excel)
        print(f"分析完成！结果已保存到: {output_excel}")
    
    def save_to_excel(self, results: List[Dict], output_file: str) -> None:
        """将结果保存到Excel文件"""
        try:
            # 创建DataFrame
            df = pd.DataFrame(results)
            
            # 确保列的顺序
            columns_order = ["图片名", "眼睛形状", "嘴型", "表情", "脸部动态", "情感强度", "图片url地址"]
            df = df[columns_order]
            
            # 保存到Excel
            df.to_excel(output_file, index=False, engine='openpyxl')
            print(f"Excel文件保存成功: {output_file}")
            
        except Exception as e:
            print(f"保存Excel文件失败: {str(e)}")


def main():
    """主函数"""
    # 创建分析器实例
    analyzer = ImageAnalyzer()
    
    # 获取用户输入
    while True:
        folder_path = "D:\project\dongdesign\joy_ip\data\joy_head"
        if folder_path and Path(folder_path).exists():
            break
        print("文件夹路径无效，请重新输入")
    
    # 获取输出文件名
    output_file = "D:\project\dongdesign\joy_ip\data\joy_head.xlsx"
    if not output_file:
        output_file = "analysis_results.xlsx"
    
    if not output_file.endswith('.xlsx'):
        output_file += '.xlsx'
    
    # 开始分析
    try:
        analyzer.analyze_folder(folder_path, output_file)
    except KeyboardInterrupt:
        print("\n分析被用户中断")
    except Exception as e:
        print(f"分析过程中出现错误: {str(e)}")


if __name__ == "__main__":
    main()