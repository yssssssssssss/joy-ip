#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务管理器
管理后台生成任务的生命周期，支持排队和并发控制
"""

import threading
import time
import uuid
from collections import deque
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """任务状态"""
    QUEUED = "queued"      # 排队等待中
    RUNNING = "running"    # 执行中
    SUCCEEDED = "succeeded"  # 成功
    FAILED = "failed"      # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class Job:
    """任务数据类"""
    job_id: str
    requirement: str
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    stage: str = "queued"
    analysis: Optional[Dict] = None
    pre_analysis: Optional[Dict] = None  # 用户确认的预分析结果
    mode: str = "3D"  # 生成模式：2D 或 3D
    perspective: str = "正视角"  # 视角：正视角 或 仰视角
    images: List[str] = field(default_factory=list)
    error: Optional[str] = None
    details: Dict = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None  # 开始执行时间
    finished_at: Optional[float] = None  # 完成时间
    queue_position: int = 0  # 队列位置（0表示正在执行或已完成）
    estimated_wait: float = 0  # 预估等待时间（秒）

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": self.progress,
            "stage": self.stage,
            "analysis": self.analysis,
            "pre_analysis": self.pre_analysis,
            "mode": self.mode,
            "perspective": self.perspective,
            "images": self.images,
            "error": self.error,
            "details": self.details,
            "updated_at": self.updated_at,
            "queue_position": self.queue_position,
            "estimated_wait": round(self.estimated_wait, 1),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at
        }


class JobQueue:
    """
    任务队列管理器
    控制并发执行数量，超出的任务进入等待队列
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        max_queue_size: int = 50,
        avg_job_duration: float = 60.0  # 默认预估每个任务60秒
    ):
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        self._avg_job_duration = avg_job_duration
        
        # 等待队列（FIFO）
        self._waiting_queue: deque = deque()
        # 正在执行的任务
        self._running_jobs: Dict[str, Job] = {}
        # 任务执行函数映射
        self._job_handlers: Dict[str, Callable] = {}
        
        self._lock = threading.Lock()
        
        # 历史执行时间记录（用于动态计算平均时间）
        self._duration_history: List[float] = []
        self._max_history_size = 20
        
        logger.info(f"JobQueue 初始化: max_concurrent={max_concurrent}, max_queue={max_queue_size}")

    @property
    def avg_job_duration(self) -> float:
        """获取平均任务执行时间"""
        if self._duration_history:
            return sum(self._duration_history) / len(self._duration_history)
        return self._avg_job_duration

    def _record_duration(self, duration: float):
        """记录任务执行时间"""
        with self._lock:
            self._duration_history.append(duration)
            if len(self._duration_history) > self._max_history_size:
                self._duration_history.pop(0)

    def get_queue_stats(self) -> Dict:
        """获取队列统计信息"""
        with self._lock:
            return {
                "running_count": len(self._running_jobs),
                "waiting_count": len(self._waiting_queue),
                "max_concurrent": self.max_concurrent,
                "avg_duration": round(self.avg_job_duration, 1)
            }

    def get_position_and_wait(self, job_id: str) -> tuple:
        """
        获取任务的队列位置和预估等待时间
        
        Returns:
            (position, estimated_wait_seconds)
            position=0 表示正在执行或已完成
        """
        with self._lock:
            # 检查是否正在执行
            if job_id in self._running_jobs:
                return (0, 0)
            
            # 在等待队列中查找位置
            for i, (waiting_id, _, _) in enumerate(self._waiting_queue):
                if waiting_id == job_id:
                    position = i + 1
                    # 预估等待时间 = 前面的任务数 * 平均执行时间
                    # 考虑并发：实际等待 = (position / max_concurrent) * avg_duration
                    batches_ahead = (position + len(self._running_jobs) - 1) // self.max_concurrent
                    estimated_wait = batches_ahead * self.avg_job_duration
                    return (position, estimated_wait)
            
            return (0, 0)

    def submit(self, job: Job, handler: Callable) -> bool:
        """
        提交任务到队列
        
        Args:
            job: 任务对象
            handler: 任务执行函数 handler(job_id, requirement)
            
        Returns:
            bool: 是否成功提交
        """
        with self._lock:
            # 检查队列是否已满
            if len(self._waiting_queue) >= self.max_queue_size:
                logger.warning(f"队列已满，拒绝任务: {job.job_id}")
                return False
            
            # 保存处理函数
            self._job_handlers[job.job_id] = handler
            
            # 检查是否可以直接执行
            if len(self._running_jobs) < self.max_concurrent:
                self._start_job(job)
            else:
                # 加入等待队列
                position = len(self._waiting_queue) + 1
                job.queue_position = position
                job.estimated_wait = self._calculate_wait_time(position)
                self._waiting_queue.append((job.job_id, job, handler))
                logger.info(f"任务加入队列: {job.job_id}, 位置: {position}, 预估等待: {job.estimated_wait:.1f}秒")
            
            return True

    def _calculate_wait_time(self, position: int) -> float:
        """计算预估等待时间"""
        # 考虑并发执行
        running_count = len(self._running_jobs)
        batches_ahead = (position + running_count - 1) // self.max_concurrent
        return batches_ahead * self.avg_job_duration

    def _start_job(self, job: Job):
        """启动任务执行（需要在锁内调用）"""
        job.status = JobStatus.RUNNING
        job.stage = "starting"
        job.queue_position = 0
        job.estimated_wait = 0
        job.started_at = time.time()
        job.updated_at = time.time()
        
        self._running_jobs[job.job_id] = job
        
        handler = self._job_handlers.get(job.job_id)
        if handler:
            # 启动执行线程
            thread = threading.Thread(
                target=self._run_job_wrapper,
                args=(job.job_id, job.requirement, handler),
                daemon=True
            )
            thread.start()
            logger.info(f"任务开始执行: {job.job_id}")

    def _run_job_wrapper(self, job_id: str, requirement: str, handler: Callable):
        """任务执行包装器"""
        start_time = time.time()
        try:
            handler(job_id, requirement)
        except Exception as e:
            logger.error(f"任务执行异常: {job_id}, {str(e)}")
        finally:
            duration = time.time() - start_time
            self._record_duration(duration)
            self._on_job_complete(job_id)

    def _on_job_complete(self, job_id: str):
        """任务完成回调"""
        with self._lock:
            # 从运行列表移除
            if job_id in self._running_jobs:
                job = self._running_jobs.pop(job_id)
                job.finished_at = time.time()
            
            # 清理处理函数
            self._job_handlers.pop(job_id, None)
            
            # 更新等待队列中所有任务的位置和预估时间
            self._update_queue_positions()
            
            # 启动下一个等待任务
            self._try_start_next()

    def _update_queue_positions(self):
        """更新等待队列中所有任务的位置（需要在锁内调用）"""
        for i, (_, job, _) in enumerate(self._waiting_queue):
            job.queue_position = i + 1
            job.estimated_wait = self._calculate_wait_time(i + 1)
            job.updated_at = time.time()

    def _try_start_next(self):
        """尝试启动下一个等待任务（需要在锁内调用）"""
        while len(self._running_jobs) < self.max_concurrent and self._waiting_queue:
            job_id, job, handler = self._waiting_queue.popleft()
            self._start_job(job)
            logger.info(f"从队列启动任务: {job_id}")

    def cancel_job(self, job_id: str) -> bool:
        """取消任务"""
        with self._lock:
            # 从等待队列中移除
            for i, (waiting_id, job, _) in enumerate(list(self._waiting_queue)):
                if waiting_id == job_id:
                    del self._waiting_queue[i]
                    job.status = JobStatus.CANCELLED
                    self._job_handlers.pop(job_id, None)
                    self._update_queue_positions()
                    logger.info(f"任务已取消: {job_id}")
                    return True
            return False


class JobManager:
    """任务管理器（带队列控制）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        max_jobs: int = 100,
        job_ttl: int = 3600,
        cleanup_interval: int = 300,
        max_concurrent: int = 5,
        max_queue_size: int = 50
    ):
        if self._initialized:
            return

        self._initialized = True
        self._jobs: Dict[str, Job] = {}
        self._jobs_lock = threading.Lock()
        self._max_jobs = max_jobs
        self._job_ttl = job_ttl

        # 初始化任务队列
        self._queue = JobQueue(
            max_concurrent=max_concurrent,
            max_queue_size=max_queue_size
        )

        # 启动清理线程
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            args=(cleanup_interval,),
            daemon=True
        )
        self._cleanup_thread.start()

        logger.info(f"JobManager 初始化完成: max_jobs={max_jobs}, ttl={job_ttl}s, max_concurrent={max_concurrent}")

    def create_job(self, requirement: str) -> str:
        """创建新任务（仅创建，不启动）"""
        job_id = uuid.uuid4().hex

        with self._jobs_lock:
            if len(self._jobs) >= self._max_jobs:
                self._cleanup_old_jobs()

            job = Job(job_id=job_id, requirement=requirement)
            self._jobs[job_id] = job

        logger.info(f"创建任务: {job_id}")
        return job_id

    def submit_job(self, job_id: str, handler: Callable) -> Dict:
        """
        提交任务到执行队列
        
        Returns:
            Dict: 包含队列位置和预估等待时间
        """
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if not job:
                return {"success": False, "error": "任务不存在"}

        success = self._queue.submit(job, handler)
        if not success:
            return {"success": False, "error": "队列已满，请稍后重试"}

        position, wait_time = self._queue.get_position_and_wait(job_id)
        return {
            "success": True,
            "queue_position": position,
            "estimated_wait": round(wait_time, 1)
        }

    def get_job(self, job_id: str) -> Optional[Job]:
        """获取任务"""
        with self._jobs_lock:
            return self._jobs.get(job_id)

    def get_job_dict(self, job_id: str) -> Optional[Dict]:
        """获取任务字典（包含队列信息）"""
        job = self.get_job(job_id)
        if not job:
            return None
        
        # 更新队列位置信息
        position, wait_time = self._queue.get_position_and_wait(job_id)
        job.queue_position = position
        job.estimated_wait = wait_time
        
        return job.to_dict()

    def get_queue_stats(self) -> Dict:
        """获取队列统计信息"""
        return self._queue.get_queue_stats()

    def update_job(self, job_id: str, **kwargs):
        """更新任务"""
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if job:
                for key, value in kwargs.items():
                    if key == 'status':
                        if isinstance(value, str):
                            value = JobStatus(value)
                        elif not isinstance(value, JobStatus):
                            continue
                    if hasattr(job, key):
                        setattr(job, key, value)
                job.updated_at = time.time()

    def append_log(self, job_id: str, message: str):
        """追加日志"""
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if job:
                seq = len(job.logs) + 1
                job.logs.append(f"步骤{seq}: {message}")
                job.updated_at = time.time()

    def set_failed(self, job_id: str, error: str, **kwargs):
        """设置任务失败"""
        self.update_job(
            job_id,
            status=JobStatus.FAILED,
            error=error,
            **kwargs
        )

    def set_succeeded(self, job_id: str, images: List[str], **kwargs):
        """设置任务成功"""
        self.update_job(
            job_id,
            status=JobStatus.SUCCEEDED,
            images=images,
            progress=100,
            stage='done',
            **kwargs
        )

    def cancel_job(self, job_id: str) -> bool:
        """取消排队中的任务"""
        success = self._queue.cancel_job(job_id)
        if success:
            self.update_job(job_id, status=JobStatus.CANCELLED)
        return success

    def _cleanup_old_jobs(self):
        """清理过期任务（需要在锁内调用）"""
        now = time.time()
        expired = [
            job_id for job_id, job in self._jobs.items()
            if now - job.created_at > self._job_ttl
            and job.status in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED)
        ]

        for job_id in expired:
            del self._jobs[job_id]

        if expired:
            logger.info(f"清理了 {len(expired)} 个过期任务")

    def _cleanup_loop(self, interval: int):
        """定期清理循环"""
        while True:
            time.sleep(interval)
            with self._jobs_lock:
                self._cleanup_old_jobs()


# 全局任务管理器（并发限制5个）
job_manager = JobManager(max_concurrent=5, max_queue_size=50)
