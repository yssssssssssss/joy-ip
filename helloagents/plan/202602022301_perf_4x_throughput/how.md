# 技术设计: 4x 吞吐与超时治理（方案1）

## 技术方案

### 核心技术
- **并发治理:** JobQueue 并发提升 + 外部调用配额池（Semaphore/令牌桶/最小间隔）
- **超时治理:** 统一超时与重试策略 + Job 级 time budget + 熔断/降级
- **可观测性:** 分阶段耗时记录、外部调用耗时/错误分类、队列等待时间
- **缓存与预计算:** 分析/合规缓存、CLIP 嵌入预计算、静态素材特征预计算
- **前端轮询优化:** 自适应轮询间隔、减少无效请求

### 实现要点（按落地顺序）

#### 0) 先做基线测量（没有数据就无法证明 4×）
- 为每个 job 增加结构化的 `stage_timings`（开始/结束/耗时）
- 为每次外部调用增加 `remote_call` 记录（endpoint、模型名、耗时、状态码、错误分类、是否重试）
- 增加压测脚本（本地/内网）用于固定参数下的吞吐对比：吞吐（jobs/min）、P95、超时率、429率

#### 1) Job 级并发：从 5 → 20（4×）
- 将 `utils/job_manager.JobManager(max_concurrent=5)` 改为 **环境变量可控**：
  - `JOB_MAX_CONCURRENT`（默认 5，目标 20）
  - `JOB_MAX_QUEUE_SIZE`（默认 50，可按前端并发规模上调）
  - `JOB_TTL_SECONDS`（避免内存堆积）
- 说明：本阶段 **保持单进程任务状态一致性**，不建议启用多进程 WSGI worker。

#### 2) 外部调用配额池：把“串行锁”替换为“可配置限流”

现状问题：
- `banana-pro-img-jd.py` 默认 `JD_IMG_SERIALIZE=1`，导致外部生图在单进程近似串行；
- 同时存在 urllib3 Retry + 业务循环重试的叠加，超时会被放大。

设计：
- 新增 `utils/limits.py`，提供：
  - `ConcurrencyLimiter(name, max_concurrent)`：基于 `threading.Semaphore`
  - `RateLimiter(name, qps | min_interval)`：基于令牌桶或最小间隔 + 抖动
  - 统一上下文：`with limiter.acquire(deadline=...)` + `sleep_if_needed()`
- 为外部能力建立独立配额（默认建议值，需通过压测校准）：
  - 文本分析（`/v1/responses` 或等效）：`LLM_TEXT_MAX_CONCURRENT=8`
  - 图片生成（`/v1/images/gemini_flash/generations`）：`LLM_IMAGE_MAX_CONCURRENT=4`（目标 4× 的关键）
  - Gate 审核（同上 + 二次裁决）：`GATE_MAX_CONCURRENT=4`
- 在 `banana-pro-img-jd.py`：
  - 默认关闭 `JD_IMG_SERIALIZE`（或保留但由新 limiter 替代）
  - 每次请求使用统一 limiter（并发 + 速率），并使用共享 `requests.Session`（已有 `utils/http_client`）
- 在 `gate-result.py` 与 `content_agent.py`：
  - 统一接入 limiter，避免在高并发时互相抢占导致超时

#### 3) 超时与重试治理：避免“多层重试叠加”

现状：
- 多处 `timeout=90`，且部分模块同时做两层重试（urllib3 Retry + 自己的 for-attempt 重试）。

设计原则：
- **只保留一层重试**（建议保留业务层，因为更了解可重试条件与 backoff）
- **超时分级**：connect/read 分离；每次重试要有指数退避 + 抖动，并尊重 `Retry-After`
- **错误分类**：timeout / 429 / 5xx / invalid / unknown（用于指标与自动降载）

建议策略（初版，后续按数据校准）：
- 文本分析：`timeout_read=30s`，重试 1-2 次（仅对 429/5xx/连接错误）
- 图片生成：`timeout_read=60s`，重试 2 次（仅对 429/RESOURCE_EXHAUSTED/5xx）
- Gate：`timeout_read=30s`，重试 1 次；必要时可降级为“跳过二次裁决”

Job 级 time budget：
- 新增 `JOB_TIME_BUDGET_S`（例如 180s 或按业务设定）
- 每个阶段开始前检查剩余预算，不足则提前失败并返回明确原因（避免无意义的长耗时重试）。

熔断/降载：
- 连续超时/429 超过阈值时：
  - 先降低外部并发（例如 4→2）
  - 再降低 Job 并发（20→10）
  - 最后对新任务返回 503（保护可用性）

#### 4) Prompt/分析链路：减少外部调用次数（直接降低超时）

关键点：
- `ContentAgent._analyze_content_combined` 已有 `analysis_cache`（24h TTL），但“预分析已确认”链路仍会调用 `check_compliance`（额外 LLM 调用）。
- `HeadMatcher._translate_to_english` 会额外调用一个模型进行中文表情翻译，可能成为额外超时来源。

优化：
- 新增 `compliance_cache`（与 analysis_cache 同 TTL 或更短），`check_compliance` 优先命中缓存。
- 当 `/api/analyze` 异步分析成功后，将“合规通过”以 `job.details` 或签名形式回传，并在 `/api/start_generate` 里复用（校验 requirement 未变更）。
- 替换表情翻译：
  - 方案A（推荐）：内置常见表情词典映射（开心/生气/惊讶…），避免外部 LLM 翻译
  - 方案B：CLIP 文本使用 `中文 + 英文` 双语拼接，弱化翻译需求

#### 5) 拼装链路：利用 20 核 CPU / GPU 资源

- OpenCV 拼装为 CPU 密集任务，建议：
  - 使用可复用的 `ProcessPoolExecutor(max_workers=CPU_CORES/2)` 执行拼装，避免 GIL 限制
  - 对静态 body/head 素材预计算红区/角度等中间结果并缓存（按文件 mtime 失效）
- 对 CLIP 检索：
  - 在启动时预计算目标素材文件夹的图片 embedding（可落盘到 `cache/clip/*`）
  - 优先使用 GPU（如可用）并限制并发，避免 GPU OOM

#### 6) Gate 审核：减少外部调用 & 提供可控降级

现状：
- `gate-result.py` 的 `analyze_image_with_three_models` 实际会调用：
  - Gemini 图像接口 1 次
  - 二次裁决（chat/completions，当前为 `gpt-5`）1 次
  → 每张图至少 2 次外部调用，极易成为超时热点。

优化：
- Fast path：仅调用 Gemini 图像接口并解析“总体评分”，可直接判定通过/不通过。
- Slow path（可选）：只有当 fast path 判定为“严重崩坏/疑似异常”才触发二次裁决。
- `GATE_MODE`：
  - `strict`：总是二次裁决（质量优先）
  - `fast`：仅 fast path（吞吐优先，默认建议）
  - `auto`：高负载时 fast，低负载时 strict（建议）

#### 7) 前端与网络：降低无效流量与尾部延迟
- `/api/job/<id>/status` 轮询改为自适应：
  - queued：根据 `queue_position` 增大轮询间隔（例如 2s→5s→10s）
  - running：保持较快（1-2s）但对长阶段进行退避
  - succeeded/failed：立即停止轮询
- 静态图片分发建议：
  - 用反向代理（nginx）直接服务 `output/` 和 `generated_images/`
  - 设置 `Cache-Control`（按文件名带 hash 或时间戳可安全缓存）

## 架构决策 ADR

### ADR-001: 方案1保持单进程状态一致性
**上下文:** Job 状态在进程内内存，使用多进程 worker 会导致 status 查询命中不同进程而丢失任务。  
**决策:** 方案1阶段保持单进程（或粘性路由），通过内部并发与配额池达成 4×。  
**替代方案:** 直接上多进程 gunicorn workers → 拒绝原因：状态不一致，需引入共享存储（进入方案2）。  
**影响:** 吞吐主要通过“外部调用并发治理”提升，CPU 任务通过进程池利用多核。

### ADR-002: 外部调用使用独立配额池并统一重试
**上下文:** 当前存在脚本级串行锁与多层重试叠加，导致超时雪崩。  
**决策:** 统一 limiter + 单层重试 + deadline。  
**影响:** 可控吞吐、可预测延迟、可基于指标自动降载。

## API 设计（可选增强）
- 新增（或扩展）`GET /api/queue/stats` 返回更多性能指标（可采样/聚合）：
  - `p95_duration`、`timeout_rate`、`remote_call_rate` 等
- 新增 `GET /api/perf/metrics`（仅内网/鉴权）输出近 N 分钟指标快照（JSON）

## 数据模型（仅运行时）
- `Job.details.stage_timings`: `{stage: {start, end, ms}}`
- `Job.details.remote_calls`: `[{name, endpoint, model, ms, status, error_type, attempt}]`
- `metrics` 聚合结构：窗口化计数与分位数（可先用近 N 条样本的 P50/P95）

## 安全与性能
- **安全:**
  - 所有新开关与指标接口默认关闭或限制访问（避免泄露内部信息）
  - 对 `base_image_url` 等路径输入继续保持白名单与目录穿越防护
- **性能:**
  - 4× 目标的核心抓手：取消外部生图串行锁 → 配额池并发 4；Job 并发 20；减少 Gate 二次裁决调用

## 测试与部署
- **测试:**
  - 增加压测脚本（固定并发 N=5/10/20）对比吞吐与失败率
  - 增加“超时注入”测试（降低外部 timeout、模拟慢响应）验证降载/熔断
- **部署:**
  - 推荐用生产级 WSGI（但保持单 worker）：例如 gunicorn `-w 1 --threads <N>`
  - 外部配额通过环境变量配置（便于回滚/灰度）

