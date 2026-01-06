#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本执行器模块
提供安全的Python脚本执行和文件检测功能
"""

import subprocess
import os
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class ScriptExecutionError(Exception):
    """脚本执行错误"""
    pass


class ScriptExecutor:
    """
    Python脚本执行器
    
    提供安全的脚本执行、超时控制和新文件检测功能
    """
    
    def __init__(self, timeout: int = 120, cwd: Optional[str] = None):
        """
        初始化脚本执行器
        
        Args:
            timeout: 脚本执行超时时间（秒），默认120秒
            cwd: 工作目录，默认为当前目录
        """
        self.timeout = timeout
        self.cwd = cwd or os.getcwd()
        logger.info(f"ScriptExecutor初始化: timeout={timeout}s, cwd={self.cwd}")
    
    def run_script(
        self, 
        script_path: str, 
        args: List[str],
        timeout: Optional[int] = None
    ) -> Tuple[int, str, str]:
        """
        执行Python脚本
        
        Args:
            script_path: 脚本绝对路径或相对路径
            args: 脚本参数列表
            timeout: 超时时间（秒），如果不指定则使用实例默认值
            
        Returns:
            (返回码, stdout输出, stderr输出)
            
        Raises:
            ScriptExecutionError: 脚本执行超时或其他错误
        """
        # 确保脚本路径存在
        if not os.path.isabs(script_path):
            script_path = os.path.join(self.cwd, script_path)
        
        if not os.path.exists(script_path):
            error_msg = f"脚本文件不存在: {script_path}"
            logger.error(error_msg)
            raise ScriptExecutionError(error_msg)
        
        # 构建命令
        cmd = ['python', script_path] + args
        timeout_value = timeout if timeout is not None else self.timeout
        
        logger.info(f"执行脚本: {' '.join(cmd)}")
        logger.info(f"工作目录: {self.cwd}, 超时: {timeout_value}s")
        
        try:
            # 执行脚本
            result = subprocess.run(
                cmd,
                cwd=self.cwd,
                timeout=timeout_value,
                capture_output=True,
                text=True
            )
            
            logger.info(f"脚本执行完成: 返回码={result.returncode}")
            if result.stdout:
                logger.debug(f"stdout: {result.stdout[:500]}")  # 只记录前500字符
            if result.stderr:
                logger.debug(f"stderr: {result.stderr[:500]}")
            
            return result.returncode, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired as e:
            error_msg = f"脚本执行超时（{timeout_value}秒）: {script_path}"
            logger.error(error_msg)
            raise ScriptExecutionError(error_msg) from e
            
        except Exception as e:
            error_msg = f"脚本执行失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ScriptExecutionError(error_msg) from e
    
    def get_new_files(
        self, 
        directory: str, 
        before_files: List[str]
    ) -> List[str]:
        """
        获取目录中新增的文件
        
        Args:
            directory: 监控目录的绝对路径或相对路径
            before_files: 执行前的文件名列表（不含路径）
            
        Returns:
            新增文件的绝对路径列表
        """
        # 确保目录路径是绝对路径
        if not os.path.isabs(directory):
            directory = os.path.join(self.cwd, directory)
        
        if not os.path.exists(directory):
            logger.warning(f"目录不存在: {directory}")
            return []
        
        try:
            # 获取当前文件列表
            after_files = os.listdir(directory)
            
            # 找出新增的文件
            new_files = [f for f in after_files if f not in before_files]
            
            # 转换为绝对路径
            new_file_paths = [
                os.path.join(directory, f) 
                for f in new_files
                if os.path.isfile(os.path.join(directory, f))  # 只返回文件，不包括目录
            ]
            
            logger.info(f"检测到 {len(new_file_paths)} 个新文件")
            for path in new_file_paths:
                logger.debug(f"新文件: {path}")
            
            return new_file_paths
            
        except Exception as e:
            logger.error(f"检测新文件失败: {str(e)}", exc_info=True)
            return []
    
    def get_file_list(self, directory: str) -> List[str]:
        """
        获取目录中的文件列表（仅文件名，不含路径）
        
        Args:
            directory: 目录路径
            
        Returns:
            文件名列表
        """
        # 确保目录路径是绝对路径
        if not os.path.isabs(directory):
            directory = os.path.join(self.cwd, directory)
        
        if not os.path.exists(directory):
            logger.warning(f"目录不存在: {directory}")
            return []
        
        try:
            files = [
                f for f in os.listdir(directory)
                if os.path.isfile(os.path.join(directory, f))
            ]
            logger.debug(f"目录 {directory} 包含 {len(files)} 个文件")
            return files
        except Exception as e:
            logger.error(f"获取文件列表失败: {str(e)}", exc_info=True)
            return []
