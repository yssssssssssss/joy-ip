#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
违规词库管理模块
提供全局缓存的违规词库，避免重复加载
"""

import os
import re
import threading
import logging
from typing import List, Tuple, Optional, Pattern

logger = logging.getLogger(__name__)

# 全局缓存
_banned_words: Optional[List[str]] = None
_banned_patterns: Optional[List[Pattern]] = None
_cache_lock = threading.Lock()

# 默认词库文件路径
DEFAULT_WORDS_FILE = "data/sensitive_words.txt"


def get_banned_words() -> Tuple[List[str], List[Pattern]]:
    """
    获取违规词库（带缓存）
    
    Returns:
        (普通违规词列表, 预编译的正则表达式列表)
    """
    global _banned_words, _banned_patterns
    
    if _banned_words is None:
        with _cache_lock:
            if _banned_words is None:
                _banned_words, _banned_patterns = _load_banned_words()
    
    return _banned_words, _banned_patterns


def _load_banned_words(file_path: str = DEFAULT_WORDS_FILE) -> Tuple[List[str], List[Pattern]]:
    """
    加载违规词库文件
    
    Args:
        file_path: 词库文件路径
        
    Returns:
        (普通违规词列表, 预编译的正则表达式列表)
    """
    banned_words = []
    banned_patterns = []
    
    try:
        if not os.path.exists(file_path):
            logger.warning(f"违规词库文件不存在: {file_path}")
            return banned_words, banned_patterns
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                
                if line.startswith('REGEX:'):
                    # 正则表达式 - 预编译
                    pattern_str = line[6:].strip()
                    try:
                        compiled = re.compile(pattern_str, re.IGNORECASE)
                        banned_patterns.append(compiled)
                    except re.error as e:
                        logger.warning(f"正则表达式编译失败: {pattern_str} - {e}")
                else:
                    # 普通词汇
                    banned_words.append(line)
        
        logger.info(f"违规词库加载完成: {len(banned_words)} 个词汇, {len(banned_patterns)} 个正则")
        
    except Exception as e:
        logger.error(f"加载违规词库失败: {e}")
    
    return banned_words, banned_patterns


def check_banned_words(content: str) -> Tuple[bool, str]:
    """
    检查内容是否包含违规词
    
    Args:
        content: 待检查的内容
        
    Returns:
        (是否合规, 不合规原因)
    """
    words, patterns = get_banned_words()
    
    # 检查普通违规词
    for word in words:
        if word in content:
            return False, f"包含违规词汇: {word}"
    
    # 检查正则表达式（已预编译）
    for pattern in patterns:
        match = pattern.search(content)
        if match:
            return False, f"包含违规内容: {match.group(0)}"
    
    return True, ""


def reload_banned_words():
    """重新加载违规词库（用于动态更新后刷新缓存）"""
    global _banned_words, _banned_patterns
    
    with _cache_lock:
        _banned_words, _banned_patterns = _load_banned_words()
        logger.info("违规词库已重新加载")


def add_banned_word(word: str) -> bool:
    """
    添加违规词（同时更新文件和缓存）
    
    Args:
        word: 违规词或正则表达式（REGEX:开头）
        
    Returns:
        是否添加成功
    """
    global _banned_words, _banned_patterns
    
    try:
        is_regex = word.startswith('REGEX:')
        
        with _cache_lock:
            if is_regex:
                pattern_str = word[6:].strip()
                # 检查是否已存在
                for p in _banned_patterns or []:
                    if p.pattern == pattern_str:
                        return False
                
                # 编译并添加
                try:
                    compiled = re.compile(pattern_str, re.IGNORECASE)
                    if _banned_patterns is None:
                        _banned_patterns = []
                    _banned_patterns.append(compiled)
                except re.error as e:
                    logger.error(f"正则表达式编译失败: {pattern_str} - {e}")
                    return False
            else:
                # 检查是否已存在
                if _banned_words and word in _banned_words:
                    return False
                
                if _banned_words is None:
                    _banned_words = []
                _banned_words.append(word)
            
            # 追加到文件
            os.makedirs(os.path.dirname(DEFAULT_WORDS_FILE), exist_ok=True)
            with open(DEFAULT_WORDS_FILE, 'a', encoding='utf-8') as f:
                f.write(f"\n{word}")
        
        logger.info(f"已添加违规词: {word}")
        return True
        
    except Exception as e:
        logger.error(f"添加违规词失败: {e}")
        return False


def remove_banned_word(word: str) -> bool:
    """
    移除违规词（同时更新文件和缓存）
    
    Args:
        word: 违规词或正则表达式
        
    Returns:
        是否移除成功
    """
    global _banned_words, _banned_patterns
    
    try:
        is_regex = word.startswith('REGEX:')
        removed = False
        
        with _cache_lock:
            if is_regex:
                pattern_str = word[6:].strip()
                if _banned_patterns:
                    for i, p in enumerate(_banned_patterns):
                        if p.pattern == pattern_str:
                            del _banned_patterns[i]
                            removed = True
                            break
            else:
                if _banned_words and word in _banned_words:
                    _banned_words.remove(word)
                    removed = True
            
            if removed:
                # 重写文件
                _rewrite_words_file()
        
        if removed:
            logger.info(f"已移除违规词: {word}")
        return removed
        
    except Exception as e:
        logger.error(f"移除违规词失败: {e}")
        return False


def _rewrite_words_file():
    """重写违规词库文件（需要在锁内调用）"""
    try:
        with open(DEFAULT_WORDS_FILE, 'w', encoding='utf-8') as f:
            f.write("# 违规词库文件\n")
            f.write("# 每行一个词，以#开头的行为注释\n")
            f.write("# 支持正则表达式，格式：REGEX:正则表达式\n\n")
            
            # 写入普通词汇
            if _banned_words:
                for word in _banned_words:
                    f.write(f"{word}\n")
            
            # 写入正则表达式
            if _banned_patterns:
                for pattern in _banned_patterns:
                    f.write(f"REGEX:{pattern.pattern}\n")
                    
    except Exception as e:
        logger.error(f"重写违规词库文件失败: {e}")
