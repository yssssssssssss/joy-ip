# 任务清单: 4x 吞吐与超时治理（方案1）

目录: `helloagents/plan/202602022301_perf_4x_throughput/`

---

## 1. 基线与可观测性（先量化）
- [x] 1.1 在 `utils/job_manager.py` 增加 job 阶段耗时记录字段（stage_timings），并在 status 响应里返回（验证 why.md#核心场景-失败可诊断）
- [x] 1.2 在 `app_new.py` 的 `_run_generation_job` 增加关键阶段埋点（analyze/match/compose/decorate/gate/validate），并记录总耗时与队列等待（验证 why.md#需求-高并发生成-3d）
- [x] 1.3 在 `utils/generation_log.py` 扩展记录：duration、error_type、stage（用于离线统计）（验证 why.md#需求-失败可诊断）
- [x] 1.4 新增 `test/perf/load_test.py`：并发 N 可配置，统计吞吐/成功率/P95（用于 4× 对比）

## 2. Job 并发提升与队列治理（5→20）
- [x] 2.1 在 `utils/job_manager.py` 支持 env 配置 `JOB_MAX_CONCURRENT/JOB_MAX_QUEUE_SIZE/JOB_TTL_SECONDS`（验证 why.md#需求-高并发生成-3d）
- [x] 2.2 在 `utils/job_manager.py` 增加“拒绝策略”：队列满返回 503 且给出可读错误（验证 why.md#需求-高并发生成-3d）
- [x] 2.3 在 `helloagents/wiki/api.md` 补充队列满/超时等错误语义（文档同步）

## 3. 外部调用配额池（替换串行锁）
- [x] 3.1 新增 `utils/limits.py`（ConcurrencyLimiter + RateLimiter + 统一错误分类）并提供 env 配置（验证 why.md#需求-高并发生成-3d）
- [x] 3.2 在 `banana-pro-img-jd.py` 接入 `utils/limits.py`，默认关闭 `JD_IMG_SERIALIZE` 或用 limiter 替代；统一使用 `utils/http_client`（验证 why.md#需求-高并发生成-3d）
- [x] 3.3 在 `content_agent.py`/`utils/http_client.py` 接入“文本分析” limiter，并将超时/重试降为单层（验证 why.md#需求-预分析-用户编辑后生成）
- [x] 3.4 在 `gate-result.py` 接入 “Gate” limiter，并复用 `utils/http_client`（验证 why.md#需求-gate-在高负载下可控）

## 4. 超时治理与重试统一（解决“最常见失败=超时”）
- [x] 4.1 在 `utils/http_client.py` 增加可配置超时（connect/read）、并允许按调用方传入 deadline（验证 why.md#需求-失败可诊断）
- [x] 4.2 在 `banana-pro-img-jd.py` 去除与 urllib3 Retry 的叠加（只保留一层），并尊重 `Retry-After`（验证 why.md#需求-高并发生成-3d）
- [x] 4.3 在 `app_new.py` 增加 `JOB_TIME_BUDGET_S`，超过预算提前失败并标注阶段（验证 why.md#需求-失败可诊断）
- [ ] 4.4 新增简单熔断：超时/429 连续超过阈值时自动降低外部并发（验证 why.md#需求-gate-在高负载下可控）

## 5. Prompt/分析链路减调用（直接降超时）
- [x] 5.1 新增 compliance 缓存（可复用 `utils/analysis_cache.py` 模式或新增 `utils/compliance_cache.py`），`check_compliance` 优先命中缓存（验证 why.md#需求-预分析-用户编辑后生成）
- [x] 5.2 在 `matchers/head_matcher.py` 移除/替换表情翻译的外部大模型调用（改为词典或中英拼接），避免新增超时点（验证 why.md#需求-高并发生成-3d）
- [x] 5.3 在 `utils/clip_manager.py` 增加 embedding 预计算缓存（按文件夹/mtime 失效），避免每次请求全量 encode（验证 why.md#需求-高并发生成-3d）

## 6. Gate 审核降调用（fast/strict/auto）
- [x] 6.1 在 `gate-result.py` 增加 `GATE_MODE=fast|strict|auto`：fast 仅单模型；strict 才二次裁决；auto 根据负载切换（验证 why.md#需求-gate-在高负载下可控）
- [ ] 6.2 在 `generation_controller.py`/`generation_controller_2d.py` 衔接 `GATE_MODE` 与并发 limiter（验证 why.md#需求-gate-在高负载下可控）

## 7. 前端轮询与网络优化
- [x] 7.1 在 `frontend/src/components/ChatInterface.tsx` 将轮询改为自适应间隔（queued 慢、running 快、done 停），降低 status 压力（验证 why.md#需求-高并发生成-3d）
- [x] 7.2 在 `frontend/src/lib/api.ts` 增加对 503/超时错误的用户可读提示（验证 why.md#需求-失败可诊断）

## 8. 安全检查
- [ ] 8.1 执行安全检查（输入验证、敏感信息处理、路径安全、外部调用熔断/限流安全边界）

## 9. 文档更新
- [x] 9.1 更新 `helloagents/wiki/arch.md`：补充 ADR 索引（ADR-001/002）与配额池架构图
- [x] 9.2 更新 `helloagents/wiki/modules/backend.md`：记录新增的 limiter/metrics 组件与配置项

## 10. 回归与验收
- [ ] 10.1 使用压测脚本对比：并发=5（基线）与并发=20（目标），产出吞吐/成功率/P95 对比结果
- [ ] 10.2 验收 4×：在相同测试集与相同外部配额下，吞吐达到基线的 4×（或在超时率显著降低的前提下接近 4×，并给出差距原因与下一步）
