#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端测试：完整的图片生成流程
包括：用户输入 → 合规检查 → 分析 → 生图 → 图片合规检查
"""

import logging
import sys
import os
import requests
import json
import time

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_api_analyze():
    """测试分析API"""
    logger.info("=== 测试分析API ===")
    
    url = "http://localhost:5000/api/analyze"
    test_cases = [
        "生成一个穿红色上衣的joy形象",
        "头戴圣诞帽，手持礼物盒的joy",
        "符合中秋节氛围的joy形象"
    ]
    
    for i, requirement in enumerate(test_cases, 1):
        logger.info(f"测试用例 {i}: {requirement}")
        
        try:
            response = requests.post(url, json={"requirement": requirement}, timeout=180)
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                logger.info(f"✓ 分析成功")
                logger.info(f"  合规: {result.get('compliant')}")
                logger.info(f"  分析结果: {result.get('analysis')}")
            else:
                logger.error(f"✗ 分析失败: {result.get('error')}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ 请求失败: {e}")
        except Exception as e:
            logger.error(f"✗ 处理失败: {e}")
    
    return True

def test_api_generate():
    """测试生成API（异步任务）"""
    logger.info("=== 测试生成API ===")
    
    start_url = "http://localhost:5000/api/start_generate"
    status_url = "http://localhost:5000/api/job/{}/status"
    
    test_requirement = "生成一个穿红色上衣的joy形象"
    
    try:
        # 1. 启动生成任务
        logger.info(f"启动生成任务: {test_requirement}")
        response = requests.post(start_url, json={"requirement": test_requirement}, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        if not result.get('success'):
            logger.error(f"✗ 启动任务失败: {result.get('error')}")
            return False
        
        job_id = result.get('job_id')
        logger.info(f"✓ 任务已启动: job_id={job_id}")
        logger.info(f"  队列位置: {result.get('queue_position')}")
        logger.info(f"  预估等待: {result.get('estimated_wait')}秒")
        
        # 2. 轮询任务状态
        logger.info("开始轮询任务状态...")
        max_wait_time = 600  # 最大等待10分钟
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                status_response = requests.get(status_url.format(job_id), timeout=10)
                status_response.raise_for_status()
                
                status_result = status_response.json()
                if not status_result.get('success'):
                    logger.error(f"✗ 查询状态失败: {status_result.get('error')}")
                    break
                
                job = status_result.get('job', {})
                status = job.get('status')
                progress = job.get('progress', 0)
                stage = job.get('stage', '')
                
                logger.info(f"任务状态: {status}, 进度: {progress}%, 阶段: {stage}")
                
                if status == 'succeeded':
                    images = job.get('images', [])
                    logger.info(f"✓ 生成成功! 共生成 {len(images)} 张图片")
                    for img_url in images:
                        logger.info(f"  图片: {img_url}")
                    return True
                elif status == 'failed':
                    error = job.get('error', '未知错误')
                    logger.error(f"✗ 生成失败: {error}")
                    return False
                
                time.sleep(5)  # 等待5秒后再次查询
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"查询状态失败: {e}")
                time.sleep(5)
        
        logger.error("✗ 任务超时")
        return False
        
    except requests.exceptions.RequestException as e:
        logger.error(f"✗ 请求失败: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ 处理失败: {e}")
        return False

def test_health_check():
    """测试健康检查"""
    logger.info("=== 测试健康检查 ===")
    
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=10)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"✓ 健康检查通过: {result}")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"✗ 健康检查失败: {e}")
        return False

def main():
    """主测试函数"""
    logger.info("开始端到端测试...")
    
    # 检查服务是否运行
    if not test_health_check():
        logger.error("服务未运行，请先启动应用: python app_new.py")
        return False
    
    # 测试分析API
    if not test_api_analyze():
        logger.error("分析API测试失败")
        return False
    
    # 测试生成API
    if not test_api_generate():
        logger.error("生成API测试失败")
        return False
    
    logger.info("✓ 所有测试通过！")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)