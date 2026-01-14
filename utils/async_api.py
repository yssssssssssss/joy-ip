#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步 API 调用工具
支持并发调用图片生成 API，提升处理效率
"""

import asyncio
import logging
from typing import List, Tuple, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# 默认并发数
DEFAULT_CONCURRENCY = 4


class AsyncBatchProcessor:
    """异步批量处理器"""
    
    def __init__(self, max_concurrency: int = DEFAULT_CONCURRENCY):
        self.max_concurrency = max_concurrency
        self._semaphore = None
    
    async def _run_with_semaphore(self, func: Callable, *args) -> Any:
        """使用信号量控制并发"""
        async with self._semaphore:
            # 在线程池中运行同步函数
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, func, *args)
    
    async def batch_process_async(self, tasks: List[Tuple], 
                                   process_func: Callable) -> List[Any]:
        """
        异步批量处理任务
        
        Args:
            tasks: 任务参数列表，每个元素是传给 process_func 的参数元组
            process_func: 处理函数（同步函数）
            
        Returns:
            List: 处理结果列表
        """
        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        
        async_tasks = [
            self._run_with_semaphore(process_func, *task_args)
            for task_args in tasks
        ]
        
        results = await asyncio.gather(*async_tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"任务 {i} 处理失败: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)
        
        return processed_results


def run_async_batch(tasks: List[Tuple], process_func: Callable,
                    max_concurrency: int = DEFAULT_CONCURRENCY) -> List[Any]:
    """
    同步接口：运行异步批量处理
    
    Args:
        tasks: 任务参数列表
        process_func: 处理函数
        max_concurrency: 最大并发数
        
    Returns:
        List: 处理结果列表
    """
    processor = AsyncBatchProcessor(max_concurrency)
    
    # 获取或创建事件循环
    try:
        loop = asyncio.get_running_loop()
        # 如果已有运行的循环，使用线程池
        with ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                processor.batch_process_async(tasks, process_func)
            )
            return future.result()
    except RuntimeError:
        # 没有运行的循环，直接创建
        return asyncio.run(processor.batch_process_async(tasks, process_func))


def parallel_process(items: List[Any], process_func: Callable,
                     max_workers: int = DEFAULT_CONCURRENCY) -> List[Any]:
    """
    使用线程池并行处理（更简单的接口）
    
    Args:
        items: 待处理项目列表
        process_func: 处理函数，接受单个 item 作为参数
        max_workers: 最大并发数
        
    Returns:
        List: 处理结果列表（保持原顺序）
    """
    if not items:
        return []
    
    if len(items) == 1:
        return [process_func(items[0])]
    
    results = [None] * len(items)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(process_func, item): idx
            for idx, item in enumerate(items)
        }
        
        for future in future_to_idx:
            idx = future_to_idx[future]
            try:
                results[idx] = future.result(timeout=120)
            except Exception as e:
                logger.warning(f"并行处理任务 {idx} 失败: {e}")
                results[idx] = None
    
    return results


def parallel_process_with_args(tasks: List[Tuple[Callable, Tuple]], 
                                max_workers: int = DEFAULT_CONCURRENCY) -> List[Any]:
    """
    使用线程池并行处理（支持不同函数和参数）
    
    Args:
        tasks: [(func, args), ...] 函数和参数对列表
        max_workers: 最大并发数
        
    Returns:
        List: 处理结果列表
    """
    if not tasks:
        return []
    
    results = [None] * len(tasks)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {}
        for idx, (func, args) in enumerate(tasks):
            future = executor.submit(func, *args)
            future_to_idx[future] = idx
        
        for future in future_to_idx:
            idx = future_to_idx[future]
            try:
                results[idx] = future.result(timeout=120)
            except Exception as e:
                logger.warning(f"并行处理任务 {idx} 失败: {e}")
                results[idx] = None
    
    return results


if __name__ == "__main__":
    # 测试代码
    import time
    
    def slow_task(x):
        time.sleep(0.5)
        return x * 2
    
    items = list(range(8))
    
    start = time.time()
    results = parallel_process(items, slow_task, max_workers=4)
    elapsed = time.time() - start
    
    print(f"结果: {results}")
    print(f"耗时: {elapsed:.2f}s (理论最优: 1.0s)")
