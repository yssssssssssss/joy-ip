#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成记录日志模块
记录用户 prompt 与生成图片的关联关系
使用 JSON Lines 格式存储，简单高效可靠
"""

import json
import os
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional

# 日志文件路径
LOG_FILE = "logs/generation_history.jsonl"
_lock = Lock()


def log_generation(
    prompt: str,
    images: List[str],
    job_id: str = None,
    analysis: Dict = None,
    status: str = "success",
    duration: float = None,
    extra: Dict = None
) -> str:
    """
    记录一次生成任务
    
    Args:
        prompt: 用户输入的原始 prompt
        images: 生成的图片路径列表
        job_id: 任务ID（可选，默认自动生成）
        analysis: AI分析结果（可选）
        status: 任务状态 (success/failed/partial)
        duration: 耗时秒数（可选）
        extra: 额外信息（可选）
    
    Returns:
        str: 记录的 job_id
    """
    record_id = job_id or datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]
    
    record = {
        "timestamp": datetime.now().isoformat(),
        "job_id": record_id,
        "prompt": prompt,
        "images": images,
        "image_count": len(images),
        "status": status,
    }
    
    if analysis:
        record["analysis"] = analysis
    if duration is not None:
        record["duration"] = round(duration, 2)
    if extra:
        record.update(extra)
    
    # 确保目录存在
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    # 线程安全写入
    with _lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    return record_id


def query_by_prompt(keyword: str, limit: int = 100) -> List[Dict]:
    """
    按 prompt 关键词查询
    
    Args:
        keyword: 搜索关键词
        limit: 最大返回数量
    
    Returns:
        List[Dict]: 匹配的记录列表（按时间倒序）
    """
    results = []
    if not os.path.exists(LOG_FILE):
        return results
    
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line.strip())
                if keyword in record.get("prompt", ""):
                    results.append(record)
            except json.JSONDecodeError:
                continue
    
    # 按时间倒序，取最新的
    results.reverse()
    return results[:limit]


def query_by_image(image_name: str) -> Optional[Dict]:
    """
    按图片名查询对应的 prompt 和记录
    
    Args:
        image_name: 图片文件名（支持部分匹配）
    
    Returns:
        Dict: 匹配的记录，未找到返回 None
    """
    if not os.path.exists(LOG_FILE):
        return None
    
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line.strip())
                images = record.get("images", [])
                if any(image_name in img for img in images):
                    return record
            except json.JSONDecodeError:
                continue
    
    return None


def query_by_job_id(job_id: str) -> Optional[Dict]:
    """
    按 job_id 查询记录
    
    Args:
        job_id: 任务ID
    
    Returns:
        Dict: 匹配的记录，未找到返回 None
    """
    if not os.path.exists(LOG_FILE):
        return None
    
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line.strip())
                if record.get("job_id") == job_id:
                    return record
            except json.JSONDecodeError:
                continue
    
    return None


def get_recent_records(limit: int = 50) -> List[Dict]:
    """
    获取最近的生成记录
    
    Args:
        limit: 返回数量
    
    Returns:
        List[Dict]: 最近的记录列表（按时间倒序）
    """
    records = []
    if not os.path.exists(LOG_FILE):
        return records
    
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line.strip())
                records.append(record)
            except json.JSONDecodeError:
                continue
    
    # 按时间倒序
    records.reverse()
    return records[:limit]


def get_statistics() -> Dict:
    """
    获取生成统计信息
    
    Returns:
        Dict: 统计信息
    """
    stats = {
        "total_jobs": 0,
        "success_jobs": 0,
        "failed_jobs": 0,
        "total_images": 0,
        "avg_duration": 0,
    }
    
    if not os.path.exists(LOG_FILE):
        return stats
    
    durations = []
    
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line.strip())
                stats["total_jobs"] += 1
                
                if record.get("status") == "success":
                    stats["success_jobs"] += 1
                else:
                    stats["failed_jobs"] += 1
                
                stats["total_images"] += record.get("image_count", 0)
                
                if record.get("duration"):
                    durations.append(record["duration"])
                    
            except json.JSONDecodeError:
                continue
    
    if durations:
        stats["avg_duration"] = round(sum(durations) / len(durations), 2)
    
    return stats
