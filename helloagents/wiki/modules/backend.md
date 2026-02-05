# 模块: backend

## 职责
- 提供 Flask API（分析、生成、任务状态查询等）
- 管理异步任务队列与并发控制（JobManager / JobQueue）
- 执行生成链路并持续更新任务状态与任务日志
- 提供 2D 素材编辑器相关 API（素材列表/拼装）并支持 2D 底图直入生成链路（跳过 step1）
- 提供外部调用限流与超时治理（降低超时/429雪崩风险）

## 关键文件
- `app_new.py`：服务入口与主要 API 路由
- `utils/job_manager.py`：任务数据结构、排队并发控制、任务日志（状态响应包含 `latest_log` / `logs_count`）
- `utils/resource_manager.py`：共享资源与模型加载（避免重复初始化）
- `utils/limits.py`：外部调用并发/速率限制（文本/生图/Gate 独立配额）

## 关键环境变量（节选）
- `ENABLE_HEAD_CLIP_QUERY_EN`：头像素材检索时，优先使用 LLM 生成的“英文检索”短语作为 CLIP query；失败自动回退到旧的表情关键词方案
- `LLM_THINKING_BUDGET`：Gemini `/v1/responses` 的思考预算（默认 32）。过大可能导致输出被 `MAX_TOKENS` 截断；设为 `0` 则不发送该字段
