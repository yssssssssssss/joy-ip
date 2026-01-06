#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片上传器模块
提供图片上传到图床的功能
"""

import subprocess
import os
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ImageUploadError(Exception):
    """图片上传错误"""
    pass


class ImageUploader:
    """
    图片上传器
    
    使用upload2imgbed.py脚本上传图片到图床
    """
    
    def __init__(self, upload_script: str = 'upload2imgbed.py', cwd: Optional[str] = None):
        """
        初始化图片上传器
        
        Args:
            upload_script: 上传脚本路径，默认为'upload2imgbed.py'
            cwd: 工作目录，默认为当前目录
        """
        self.cwd = cwd or os.getcwd()
        
        # 确保脚本路径是绝对路径
        if not os.path.isabs(upload_script):
            self.upload_script = os.path.join(self.cwd, upload_script)
        else:
            self.upload_script = upload_script
        
        logger.info(f"ImageUploader初始化: script={self.upload_script}, cwd={self.cwd}")
        
        # 检查上传脚本是否存在
        if not os.path.exists(self.upload_script):
            logger.warning(f"上传脚本不存在: {self.upload_script}")
    
    def upload_file(
        self, 
        file_path: str, 
        custom_name: Optional[str] = None
    ) -> Dict:
        """
        上传文件到图床
        
        Args:
            file_path: 本地文件路径（绝对路径或相对路径）
            custom_name: 自定义文件名（可选）
            
        Returns:
            {'success': bool, 'url': str, 'error': str}
        """
        # 确保文件路径是绝对路径
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.cwd, file_path)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            error_msg = f"文件不存在: {file_path}"
            logger.error(error_msg)
            return {
                'success': False,
                'url': '',
                'error': error_msg
            }
        
        # 如果没有指定自定义名称，使用文件的basename
        if not custom_name:
            custom_name = os.path.basename(file_path)
        
        logger.info(f"上传文件: {file_path} (名称: {custom_name})")
        
        try:
            # 执行上传脚本
            result = subprocess.run(
                ['python', self.upload_script, file_path, custom_name],
                cwd=self.cwd,
                timeout=60,  # 上传超时60秒
                capture_output=True,
                text=True
            )
            
            # 解析输出
            if result.stdout:
                try:
                    data = json.loads(result.stdout.strip())
                    
                    # 尝试多种可能的URL字段
                    url = data.get('url') or data.get('result', {}).get('url', '')
                    
                    if url:
                        logger.info(f"上传成功: {url}")
                        return {
                            'success': True,
                            'url': url,
                            'error': ''
                        }
                    else:
                        error_msg = data.get('error', '上传失败，未返回URL')
                        logger.warning(f"上传失败: {error_msg}")
                        return {
                            'success': False,
                            'url': '',
                            'error': error_msg
                        }
                        
                except json.JSONDecodeError as e:
                    error_msg = f"解析上传结果失败: {str(e)}"
                    logger.error(f"{error_msg}, stdout: {result.stdout}")
                    return {
                        'success': False,
                        'url': '',
                        'error': error_msg
                    }
            else:
                error_msg = result.stderr or '上传脚本无输出'
                logger.error(f"上传失败: {error_msg}")
                return {
                    'success': False,
                    'url': '',
                    'error': error_msg
                }
                
        except subprocess.TimeoutExpired:
            error_msg = "上传超时（60秒）"
            logger.error(error_msg)
            return {
                'success': False,
                'url': '',
                'error': error_msg
            }
            
        except Exception as e:
            error_msg = f"上传异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'url': '',
                'error': error_msg
            }
    
    def upload_multiple(self, file_paths: List[str]) -> List[str]:
        """
        批量上传文件
        
        Args:
            file_paths: 本地文件路径列表
            
        Returns:
            成功上传的URL列表（失败的文件不包含在结果中）
        """
        logger.info(f"批量上传 {len(file_paths)} 个文件")
        
        urls = []
        for file_path in file_paths:
            result = self.upload_file(file_path)
            if result['success'] and result['url']:
                urls.append(result['url'])
            else:
                logger.warning(f"文件上传失败: {file_path}, 错误: {result.get('error')}")
        
        logger.info(f"批量上传完成: {len(urls)}/{len(file_paths)} 成功")
        return urls
    
    def upload_with_fallback(
        self, 
        file_paths: List[str],
        fallback_prefix: str = '/generated_images/'
    ) -> tuple[List[str], List[str], List[str]]:
        """
        批量上传文件，失败时返回本地路径作为降级方案
        
        Args:
            file_paths: 本地文件绝对路径列表
            fallback_prefix: 本地路径前缀，默认为'/generated_images/'
            
        Returns:
            (上传成功的URL列表, 本地路径列表, 所有结果URL列表)
        """
        logger.info(f"批量上传（带降级）{len(file_paths)} 个文件")
        
        uploaded_urls = []
        local_urls = []
        
        for file_path in file_paths:
            result = self.upload_file(file_path)
            
            # 生成本地可访问路径
            filename = os.path.basename(file_path)
            local_url = f"{fallback_prefix}{filename}"
            local_urls.append(local_url)
            
            if result['success'] and result['url']:
                uploaded_urls.append(result['url'])
            else:
                logger.warning(f"文件上传失败，将使用本地路径: {file_path}")
        
        # 如果有上传成功的，返回上传的URL；否则返回本地路径
        result_urls = uploaded_urls if uploaded_urls else local_urls
        
        logger.info(f"批量上传完成: {len(uploaded_urls)} 个上传成功, {len(local_urls)} 个本地路径")
        
        return uploaded_urls, local_urls, result_urls
