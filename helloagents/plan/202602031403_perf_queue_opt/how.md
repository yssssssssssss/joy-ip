# 技术设计: 性能与排队机制优化（单进程 Flask / JobManager）

## 技术方案

### 核心技术
- Python / Flask（`app_new.py`）
- 进程内任务队列：`utils.job_manager.JobManager`
- 外部调用复用连接池：`utils/http_client.py`
- 外部服务并发/速率限制：`utils/limits.py`

### 实现要点
1. **分层并发模型（推荐）**
   - **任务级并发（Job Queue）**：控制同时“跑完整流程”的任务数，避免线程爆炸。
   - **任务内阶段并发（Per-job Stage Parallelism）**：拼图/生图/Gate 各自最多 4 路并行。
   - **外部服务全局并发（Global Limiter）**：跨任务统一限制 LLM 文本、LLM 生图、Gate 的并发与速率，防止超时雪崩与 429 风暴。

2. **稳定性优先于吞吐**
   - 在“生图/Gate”阶段不追求无限并发，而是把并发稳定控制在上游可承受区间。
   - 通过“重试 + 指数退避 + 抖动 + 全局限流”把失败类型从“超时”转为“可控排队/可预期延迟”。

## 架构决策 ADR

### ADR-001: 保持单进程部署，强化进程内队列与限流（推荐）
**上下文:** 当前线上以 `python app_new.py` 启动。改造为外置队列/多进程会引入更多部署复杂度。

**决策:**
- 继续使用进程内 `JobManager`，但增强：
  - 分离/限制分析任务的线程膨胀
  - 统一任务内阶段并发（目标 4 路）
  - 强化全局限流（文本/生图/Gate）
  - 预算化超时：把“等待并发配额的时间”纳入整体预算，避免挂死或长尾

**替代方案:**
- 方案B：引入 Redis + RQ/Celery 外置队列
  - 拒绝原因：部署复杂度提升，当前阶段优先用最小改动把超时/排队问题收敛

**影响:**
- 优点：改动面可控、上线快、能显著减少超时雪崩与线程膨胀
- 缺点：进程重启会丢失队列与任务状态（当前本就如此）

## 并发与队列设计

### 1) 任务级排队（Job Queue）
现状：
- `start_generate` 使用 `job_manager.submit_job()` 进入队列
- `analyze(async)` 当前绕过队列直接起线程（需要纳入统一管理）

改进建议：
- 将 `analyze(async)` 也纳入队列/线程池，避免高峰时无限创建线程。
- 队列策略：保持 FIFO + 背压（队列满返回 `QUEUE_FULL`），并保持 `queue_position/estimated_wait` 可用。

可选增强（视改动量选择）：
- 增加“任务类型”与“分组并发上限”（例如：分析任务单独一个较大并发组；生成任务一个较小并发组），避免长任务阻塞短任务。

### 2) 任务内三阶段 4 路并行
目标：单任务内部阶段并行上限固定为 4（可用环境变量覆盖）。

**拼图（compose）**
- 当前 3D 主链路使用 `ImageProcessor.combine_images()` 逐个拼装，存在“空结果仍 success”导致 validate 失败的风险。
- 改造：
  - 并行化拼图（上限 4）
  - 当拼图 0 张产出时，视为失败并可重试选图（避免返回空结果）
  - 修复/规避拼图脚本里的调试文件写入冲突（并发下容易造成图片损坏/读写异常）

**生图（decorate / accessories）**
- 当前 `GenerationController._process_accessory_parallel()` 支持并行，但默认 `MAX_PARALLEL_WORKERS=2`，需提升到 4。
- 同时确保全局 limiter 生效：
  - `LLM_IMAGE_MAX_CONCURRENT=4`（跨任务）
  - `JD_IMG_SERIALIZE=0`（允许并行，交给 limiter 做总闸）

**Gate（gate / final_gate_check）**
- `final_gate_check()` 已支持并行，默认同样受 `MAX_PARALLEL_WORKERS` 控制；提升到 4。
- 配合 `GATE_MAX_CONCURRENT=4` 做跨任务总闸。

## 超时与重试（盘点与建议）

### 现状盘点（代码默认值）
- LLM 文本：`LLM_TEXT_TIMEOUT_S=60`，并发：`LLM_TEXT_MAX_CONCURRENT=8`（`content_agent.py` / `utils/limits.py`）
- LLM 生图（JD）：`LLM_IMAGE_TIMEOUT_S=60`，重试：`LLM_IMAGE_MAX_RETRIES=2`，并发：`LLM_IMAGE_MAX_CONCURRENT=4`（`banana-pro-img-jd.py` / `utils/limits.py`）
- Gate：`GATE_IMAGE_TIMEOUT_S=45`，`GATE_JUDGE_TIMEOUT_S=30`，并发：`GATE_MAX_CONCURRENT=4`（`gate-result.py` / `utils/limits.py`）
- 另外存在若干 `future.result(timeout=90)` 的线程池等待上限（`generation_controller.py`），可能与“请求超时+重试”叠加产生不一致。

### 调参建议（先稳再快）
- 建议先把“线程池等待 timeout=90”改为基于“请求超时×重试次数+余量”的动态值，或改为仅依赖请求超时与 `JOB_TIME_BUDGET_S`。
- 若线上观测到“真实生成需要更久”，再调大 `LLM_IMAGE_TIMEOUT_S` / `GATE_IMAGE_TIMEOUT_S`，同时配合更强的全局限流，避免长超时把队列拖死。

## 安全与性能
- **安全:** 不在代码中落盘或输出真实密钥；敏感信息保持在环境变量。
- **性能:**
  - 减少无意义的磁盘 debug 写入（或改为每任务唯一文件名）
  - 拼图阶段并行化 + 失败重试
  - 统一连接池（http_client）+ limiter 降低重试雪崩

## 测试与部署
- **测试:**
  - 本地无端口压测：`test/perf/local_load_test.py`
  - 重点验证：高并发下不再出现 `validate` 文件缺失；队列等待可控；失败从“超时”转为“可解释的限流/排队”
- **部署:**
  - 继续 `python app_new.py`
  - 通过 `.env`/环境变量设置推荐参数（不建议把真实密钥与生产参数提交到仓库）

