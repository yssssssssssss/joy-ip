#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLIP 模型全局管理器
确保 CLIP 模型只加载一次，所有实例共享
支持后台预加载，减少首次请求延迟
"""

import threading
import logging
import os

logger = logging.getLogger(__name__)

# 全局 CLIP 模型实例
_GLOBAL_CLIP_MODEL = None
_GLOBAL_CLIP_TOKENIZER = None
_CLIP_LOCK = threading.Lock()
_PRELOAD_THREAD = None
_PRELOAD_COMPLETE = threading.Event()


def get_clip_model():
    """
    获取全局共享的 CLIP 模型
    线程安全，懒加载，只加载一次
    """
    global _GLOBAL_CLIP_MODEL
    
    if _GLOBAL_CLIP_MODEL is None:
        with _CLIP_LOCK:
            if _GLOBAL_CLIP_MODEL is None:
                logger.info("开始加载全局 CLIP 模型...")
                try:
                    from sentence_transformers import SentenceTransformer
                    _GLOBAL_CLIP_MODEL = SentenceTransformer('clip-ViT-B-32')
                    # 尝试设置最大序列长度
                    if hasattr(_GLOBAL_CLIP_MODEL, 'max_seq_length'):
                        try:
                            _GLOBAL_CLIP_MODEL.max_seq_length = 77
                        except Exception:
                            pass
                    logger.info("✅ 全局 CLIP 模型加载完成")
                    _PRELOAD_COMPLETE.set()
                except Exception as e:
                    logger.error(f"CLIP 模型加载失败: {e}")
                    raise
    
    return _GLOBAL_CLIP_MODEL


def get_clip_tokenizer():
    """
    获取全局共享的 CLIP 分词器
    线程安全，懒加载
    """
    global _GLOBAL_CLIP_TOKENIZER
    
    if _GLOBAL_CLIP_TOKENIZER is None:
        with _CLIP_LOCK:
            if _GLOBAL_CLIP_TOKENIZER is None:
                try:
                    try:
                        from transformers import CLIPTokenizerFast as CLIPTokenizerClass
                    except Exception:
                        from transformers import CLIPTokenizer as CLIPTokenizerClass
                    
                    _GLOBAL_CLIP_TOKENIZER = CLIPTokenizerClass.from_pretrained(
                        'openai/clip-vit-base-patch32'
                    )
                    logger.info("✅ 全局 CLIP 分词器加载完成")
                except Exception as e:
                    logger.warning(f"CLIP 分词器加载失败: {e}")
                    _GLOBAL_CLIP_TOKENIZER = None
    
    return _GLOBAL_CLIP_TOKENIZER


def is_clip_loaded() -> bool:
    """检查 CLIP 模型是否已加载"""
    return _GLOBAL_CLIP_MODEL is not None


def preload_clip():
    """
    预加载 CLIP 模型（可在应用启动时调用）
    """
    try:
        get_clip_model()
        get_clip_tokenizer()
        return True
    except Exception as e:
        logger.error(f"预加载 CLIP 失败: {e}")
        return False


def _background_preload():
    """后台预加载CLIP模型（内部函数）"""
    try:
        logger.info("🚀 后台开始预加载 CLIP 模型...")
        get_clip_model()
        get_clip_tokenizer()
        logger.info("✅ CLIP 模型后台预加载完成")
    except Exception as e:
        logger.warning(f"CLIP 模型后台预加载失败: {e}")


def start_background_preload():
    """
    启动后台预加载线程
    在应用启动时调用，不阻塞主线程
    """
    global _PRELOAD_THREAD
    
    # 检查环境变量是否禁用预加载
    if os.environ.get("DISABLE_CLIP_PRELOAD", "").lower() in ("1", "true"):
        logger.info("CLIP 预加载已禁用（环境变量）")
        return
    
    # 如果已经加载或正在加载，跳过
    if _GLOBAL_CLIP_MODEL is not None:
        logger.info("CLIP 模型已加载，跳过预加载")
        return
    
    if _PRELOAD_THREAD is not None and _PRELOAD_THREAD.is_alive():
        logger.info("CLIP 预加载线程已在运行")
        return
    
    # 启动后台预加载线程
    _PRELOAD_THREAD = threading.Thread(target=_background_preload, daemon=True, name="CLIP-Preload")
    _PRELOAD_THREAD.start()
    logger.info("🚀 CLIP 后台预加载线程已启动")


def wait_for_preload(timeout: float = None) -> bool:
    """
    等待预加载完成
    
    Args:
        timeout: 超时时间（秒），None表示无限等待
        
    Returns:
        bool: 是否加载完成
    """
    return _PRELOAD_COMPLETE.wait(timeout=timeout)


# 模块加载时自动启动后台预加载
# 这样在 import 时就开始加载，不影响主线程
start_background_preload()
