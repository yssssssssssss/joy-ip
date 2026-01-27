# 模块: backend

## 职责
- 提供 Flask API（分析、生成、任务状态查询等）
- 管理异步任务队列与并发控制（JobManager / JobQueue）
- 执行生成链路并持续更新任务状态与任务日志
- 提供 2D 素材编辑器相关 API（素材列表/拼装）并支持 2D 底图直入生成链路（跳过 step1）

## 关键文件
- `app_new.py`：服务入口与主要 API 路由
- `utils/job_manager.py`：任务数据结构、排队并发控制、任务日志（状态响应包含 `latest_log` / `logs_count`）
- `utils/resource_manager.py`：共享资源与模型加载（避免重复初始化）
