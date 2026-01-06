#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
远程文件下载器模块
提供远程文件下载功能
"""

import os
import re
import time
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """下载错误"""
    pass


class RemoteFileDownloader:
    """
    远程文件下载器
    
    下载远程图片到本地临时目录
    """
    
    def __init__(self, temp_dir: str = 'generated_images', timeout: int = 30):
        """
        初始化远程文件下载器
        
        Args:
            temp_dir: 临时文件目录，默认为'generated_images'
            timeout: 下载超时时间（秒），默认30秒
        """
        self.temp_dir = temp_dir
        self.timeout = timeout
        
        # 确保临时目录存在
        os.makedirs(self.temp_dir, exist_ok=True)
        
        logger.info(f"RemoteFileDownloader初始化: temp_dir={temp_dir}, timeout={timeout}s")
    
    def is_remote_url(self, path: str) -> bool:
        """
        判断是否为远程URL
        
        Args:
            path: 路径或URL字符串
            
        Returns:
            True表示是远程URL，False表示是本地路径
        """
        if not isinstance(path, str):
            return False
        
        # 检查是否以http://或https://开头
        return bool(re.match(r'^https?://', path, re.IGNORECASE))
    
    def download(self, url: str, custom_filename: Optional[str] = None) -> str:
        """
        下载远程文件到本地
        
        Args:
            url: 远程文件URL
            custom_filename: 自定义文件名（可选），如果不指定则自动生成
            
        Returns:
            本地文件绝对路径
            
        Raises:
            DownloadError: 下载失败时抛出
        """
        if not self.is_remote_url(url):
            raise DownloadError(f"不是有效的远程URL: {url}")
        
        logger.info(f"开始下载: {url}")
        
        try:
            # 发送HTTP请求
            response = requests.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # 确定文件扩展名
            ext = self._get_file_extension(url, response)
            
            # 生成文件名
            if custom_filename:
                filename = custom_filename
                if not filename.endswith(ext):
                    filename += ext
            else:
                timestamp = int(time.time() * 1000)
                filename = f"tmp_download_{timestamp}{ext}"
            
            # 保存文件
            file_path = os.path.join(self.temp_dir, filename)
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(file_path)
            logger.info(f"下载完成: {file_path} ({file_size} bytes)")
            
            return os.path.abspath(file_path)
            
        except requests.exceptions.Timeout:
            error_msg = f"下载超时（{self.timeout}秒）: {url}"
            logger.error(error_msg)
            raise DownloadError(error_msg)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"下载失败: {str(e)}"
            logger.error(error_msg)
            raise DownloadError(error_msg) from e
            
        except Exception as e:
            error_msg = f"下载异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise DownloadError(error_msg) from e
    
    def _get_file_extension(self, url: str, response: requests.Response) -> str:
        """
        从URL或响应头中获取文件扩展名
        
        Args:
            url: 文件URL
            response: HTTP响应对象
            
        Returns:
            文件扩展名（包含点号，如'.png'）
        """
        # 首先尝试从Content-Type获取
        content_type = response.headers.get('Content-Type', '').lower()
        
        if 'image/png' in content_type:
            return '.png'
        elif 'image/jpeg' in content_type or 'image/jpg' in content_type:
            return '.jpg'
        elif 'image/gif' in content_type:
            return '.gif'
        elif 'image/webp' in content_type:
            return '.webp'
        
        # 尝试从URL中提取扩展名
        url_path = url.split('?')[0]  # 移除查询参数
        if '.' in url_path:
            ext = os.path.splitext(url_path)[1].lower()
            if ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                return ext
        
        # 默认使用.png
        return '.png'
    
    def download_if_remote(self, path: str) -> str:
        """
        如果是远程URL则下载，否则返回原路径
        
        Args:
            path: 路径或URL
            
        Returns:
            本地文件路径（绝对路径）
        """
        if self.is_remote_url(path):
            logger.info(f"检测到远程URL，开始下载: {path}")
            return self.download(path)
        else:
            # 如果是相对路径，转换为绝对路径
            if not os.path.isabs(path):
                abs_path = os.path.abspath(path)
                logger.debug(f"转换相对路径为绝对路径: {path} -> {abs_path}")
                return abs_path
            return path
