#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件示例
复制此文件为 config.py 并修改相应的值
"""

import os

# Flask配置
class Config:
    """基础配置"""
    # 调试模式
    DEBUG = False
    
    # 密钥（用于session等）
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # OpenAI API配置
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') or '35f54cc4-be7a-4414-808e-f5f9f0194d4f'
    OPENAI_API_BASE = os.environ.get('OPENAI_API_BASE') or 'http://gpt-proxy.jd.com/gateway/azure'
    
    # 文件路径配置
    OUTPUT_DIR = 'output'
    GENERATED_IMAGES_DIR = 'generated_images'
    DATA_DIR = 'data'
    
    # 图片生成配置
    MAX_RETRIES = 3  # 最大重试次数
    IMAGE_QUALITY_CHECK = True  # 是否启用质量检查
    
    # 服务器配置
    HOST = '0.0.0.0'
    PORT = 6001
    
    # CORS配置
    CORS_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000']
    
    # 违规词库
    BANNED_KEYWORDS = [
        '跪着', '抽烟', '女装', '裸', '生肉', 'logo'
    ]
    
    COMMON_BANNED_WORDS = [
        '暴力', '血腥', '色情', '赌博', '毒品',
        '政治敏感', '恐怖', '歧视', '仇恨'
    ]


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    
    # 生产环境应该使用环境变量
    SECRET_KEY = os.environ.get('SECRET_KEY')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # 更严格的CORS设置
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

