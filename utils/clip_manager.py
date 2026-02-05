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
import hashlib

logger = logging.getLogger(__name__)

# 全局 CLIP 模型实例
_GLOBAL_CLIP_MODEL = None
_GLOBAL_CLIP_TOKENIZER = None
_CLIP_LOCK = threading.Lock()
_PRELOAD_THREAD = None
_PRELOAD_COMPLETE = threading.Event()


def _offline_mode_enabled() -> bool:
    return str(os.environ.get("OFFLINE_MODE", "0")).strip().lower() in ("1", "true", "yes")


class _DummyClipModel:
    """离线模式下的占位 CLIP 模型（不依赖外网下载）"""

    def __init__(self, dim: int = 512):
        self.dim = int(dim)
        self.max_seq_length = 77

    def encode(self, sentences, convert_to_tensor: bool = False, normalize_embeddings: bool = False, **kwargs):
        import torch

        if sentences is None:
            items = []
        elif isinstance(sentences, (str, bytes)):
            items = [sentences]
        else:
            try:
                items = list(sentences)
            except Exception:
                items = [sentences]

        vectors = []
        for item in items:
            try:
                if isinstance(item, str):
                    key = f"text:{item}"
                elif hasattr(item, "size") and hasattr(item, "getpixel"):
                    w, h = item.size
                    try:
                        p1 = item.getpixel((0, 0)) if w and h else 0
                        p2 = item.getpixel((max(0, w - 1), max(0, h - 1))) if w and h else 0
                    except Exception:
                        p1 = 0
                        p2 = 0
                    key = f"img:{w}x{h}:{p1}:{p2}"
                else:
                    key = f"obj:{type(item).__name__}"
            except Exception:
                key = "obj"

            h = hashlib.md5(str(key).encode("utf-8", errors="ignore")).digest()
            seed = int.from_bytes(h[:4], "little", signed=False)
            g = torch.Generator()
            g.manual_seed(seed)
            v = torch.randn(self.dim, generator=g)
            if normalize_embeddings:
                n = torch.norm(v)
                if n > 0:
                    v = v / n
            vectors.append(v)

        if vectors:
            out = torch.stack(vectors, dim=0)
        else:
            out = torch.empty((0, self.dim))

        return out if convert_to_tensor else out.cpu().numpy()


def get_clip_model():
    """
    获取全局共享的 CLIP 模型
    线程安全，懒加载，只加载一次
    支持本地模型路径，避免网络连接问题
    """
    global _GLOBAL_CLIP_MODEL
    
    if _GLOBAL_CLIP_MODEL is None:
        with _CLIP_LOCK:
            if _GLOBAL_CLIP_MODEL is None:
                logger.info("开始加载全局 CLIP 模型...")
                try:
                    from sentence_transformers import SentenceTransformer
                    
                    # 优先使用本地模型路径（如果存在）
                    local_model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'clip-ViT-B-32')
                    
                    if os.path.exists(local_model_path):
                        logger.info(f"使用本地 CLIP 模型: {local_model_path}")
                        _GLOBAL_CLIP_MODEL = SentenceTransformer(local_model_path)
                    elif _offline_mode_enabled():
                        logger.warning("OFFLINE_MODE=1 且未找到本地 CLIP 模型，改用 DummyClipModel")
                        _GLOBAL_CLIP_MODEL = _DummyClipModel()
                    else:
                        # 尝试从 HuggingFace 下载（可能失败）
                        logger.info("本地模型不存在，尝试从 HuggingFace 下载...")
                        try:
                            _GLOBAL_CLIP_MODEL = SentenceTransformer('clip-ViT-B-32')
                        except Exception as download_error:
                            logger.error(f"从 HuggingFace 下载失败: {download_error}")
                            logger.info("提示：请手动下载模型到 models/clip-ViT-B-32 目录")
                            raise
                    
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
    支持本地模型路径
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
                    
                    local_tokenizer_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'clip-vit-base-patch32')
                    
                    if os.path.exists(local_tokenizer_path):
                        logger.info(f"使用本地 CLIP 分词器: {local_tokenizer_path}")
                        _GLOBAL_CLIP_TOKENIZER = CLIPTokenizerClass.from_pretrained(local_tokenizer_path)
                    elif _offline_mode_enabled():
                        logger.warning("OFFLINE_MODE=1 且未找到本地 CLIP 分词器，跳过加载（返回 None）")
                        _GLOBAL_CLIP_TOKENIZER = None
                    else:
                        logger.info("本地分词器不存在，尝试从 HuggingFace 下载...")
                        _GLOBAL_CLIP_TOKENIZER = CLIPTokenizerClass.from_pretrained('openai/clip-vit-base-patch32')
                        try:
                            os.makedirs(local_tokenizer_path, exist_ok=True)
                            _GLOBAL_CLIP_TOKENIZER.save_pretrained(local_tokenizer_path)
                            logger.info(f"已保存 CLIP 分词器到本地: {local_tokenizer_path}")
                        except Exception as save_error:
                            logger.warning(f"保存 CLIP 分词器到本地失败: {save_error}")
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
