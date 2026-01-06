#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件 - 统一配置管理
所有敏感信息从环境变量读取，避免硬编码
"""

import os
from typing import Optional, List

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv 未安装时跳过


class Config:
    """应用配置类 - 统一管理所有配置项"""
    
    # =========================
    # AI API 配置（统一管理）
    # =========================
    AI_API_URL: str = os.environ.get(
        'AI_API_URL', 
        'https://modelservice.jdcloud.com/v1/chat/completions'
    )
    AI_API_KEY: str = os.environ.get('AI_API_KEY', '')
    # AI_MODEL: str = os.environ.get('AI_MODEL', 'Gemini-3-Flash-Preview')
    AI_MODEL: str = os.environ.get('AI_MODEL', 'Gemini-2.5-pro')

    
    # 合并AI分析专用模型（可单独配置，不影响其他环节）
    # 如果未设置，则使用 AI_MODEL 的值
    AI_ANALYSIS_MODEL: str = os.environ.get('AI_ANALYSIS_MODEL', '')
    
    # =========================
    # Flask 配置
    # =========================
    DEBUG: bool = os.environ.get('DEBUG', 'false').lower() == 'true'
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    HOST: str = os.environ.get('HOST', '0.0.0.0')
    PORT: int = int(os.environ.get('PORT', 28888))
    
    # =========================
    # 文件路径配置
    # =========================
    OUTPUT_DIR: str = os.environ.get('OUTPUT_DIR', 'output')
    GENERATED_IMAGES_DIR: str = os.environ.get('GENERATED_IMAGES_DIR', 'generated_images')
    DATA_DIR: str = os.environ.get('DATA_DIR', 'data')
    SCRIPTS_DIR: str = os.path.dirname(os.path.abspath(__file__))
    
    # =========================
    # 单端口模式配置
    # =========================
    SINGLE_PORT_MODE: bool = os.environ.get('SINGLE_PORT_MODE', 'true').lower() == 'true'
    FRONTEND_BUILD_DIR: str = os.environ.get('FRONTEND_BUILD_DIR', 'frontend_dist')
    
    # =========================
    # CORS 配置
    # =========================
    CORS_ENABLED: bool = os.environ.get('CORS_ENABLED', 'false').lower() == 'true'
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        origins = os.environ.get('CORS_ORIGINS', '')
        return [o.strip() for o in origins.split(',') if o.strip()] if origins else []
    
    # =========================
    # 脚本执行配置
    # =========================
    SCRIPT_TIMEOUT: int = int(os.environ.get('SCRIPT_TIMEOUT', 120))
    
    # =========================
    # 图片生成配置
    # =========================
    MAX_RETRIES: int = int(os.environ.get('MAX_RETRIES', 3))
    IMAGE_QUALITY_CHECK: bool = os.environ.get('IMAGE_QUALITY_CHECK', 'true').lower() == 'true'
    
    # =========================
    # 违规词库（保持兼容）
    # =========================
    BANNED_KEYWORDS: List[str] = [
        '跪着', '抽烟', '女装', '裸', '生肉', 'logo'
    ]
    
    COMMON_BANNED_WORDS: List[str] = [
        '暴力', '血腥', '色情', '赌博', '毒品',
        '政治敏感', '恐怖', '歧视', '仇恨'
    ]
    
    @classmethod
    def validate(cls) -> bool:
        """验证必要配置是否已设置"""
        errors = []
        
        if not cls.AI_API_KEY:
            errors.append("AI_API_KEY 未设置，请在环境变量或 .env 文件中配置")
        
        if errors:
            print("=" * 50)
            print("配置验证警告:")
            for err in errors:
                print(f"  ⚠ {err}")
            print("=" * 50)
            return False
        
        return True


# 单例配置对象
_config: Optional[Config] = None


def get_config() -> Config:
    """
    获取配置单例
    
    Returns:
        Config: 配置对象
    """
    global _config
    if _config is None:
        _config = Config()
    return _config
