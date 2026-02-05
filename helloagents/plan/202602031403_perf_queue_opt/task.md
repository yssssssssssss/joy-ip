# 任务清单: 性能与排队机制优化（单进程 Flask / JobManager）

目录: `helloagents/plan/202602031403_perf_queue_opt/`

---

## 1. 任务内三阶段 4 路并行（拼图/生图/Gate）
- [√] 1.1 在 `per-data.py` 中修复并发写调试图片的文件名冲突（改为基于输出文件名/任务ID生成唯一 debug 文件名；并支持开关关闭 debug 输出）
- [√] 1.2 在 `image_processor.py` 中实现拼图阶段并行（默认 4 workers，可用 env 覆盖），并在“0 张产出”时直接失败或触发选图重试
- [√] 1.3 在 `generation_controller.py` 中将 `MAX_PARALLEL_WORKERS` 默认提升到 4，并统一用于生图与 Gate 并行阶段（可用 env 覆盖）
- [√] 1.4 在 `generation_controller_2d.py` 中将 `MAX_PARALLEL_WORKERS_2D` 默认提升到 4（可用 env 覆盖）

## 2. 排队机制稳定性优化（多任务并发）
- [ ] 2.1 在 `app_new.py` 中把 `analyze(async)` 纳入受控的后台执行（避免无限起线程）；复用 JobManager/或独立线程池并发上限
- [ ] 2.2 在 `utils/job_manager.py` 中评估并实现更稳的执行模型（例如用固定大小线程池替代“每任务一个线程”，并保持 FIFO/队列位置/预估等待逻辑）
- [ ] 2.3 为队列增加可选的“任务分组并发上限”（分析任务 vs 生成任务）或“优先级”，避免长任务阻塞短任务（如改动量过大可降级为配置建议）

## 3. 超时与重试一致性（降低超时失败）
- [ ] 3.1 盘点并统一代码中的 timeout/retry：`LLM_TEXT_TIMEOUT_S` / `LLM_IMAGE_TIMEOUT_S` / `GATE_IMAGE_TIMEOUT_S` / `GATE_JUDGE_TIMEOUT_S` / `LLM_IMAGE_MAX_RETRIES`
- [ ] 3.2 在 `generation_controller.py` 中移除或改造 `future.result(timeout=90)`（改为基于 env/重试次数/任务预算的动态 timeout），避免“线程池等待超时”提前截断
- [ ] 3.3 在 `.env.example` 中补齐推荐的线上参数组合（并明确：开启 4 路并行时建议 `JD_IMG_SERIALIZE=0` 且依赖 `LLM_IMAGE_MAX_CONCURRENT` 做全局闸）

## 4. 文档更新
- [ ] 4.1 更新 `helloagents/wiki/modules/backend.md`，补充并发/队列/超时/重试的关键环境变量说明与推荐默认值

## 5. 测试
- [ ] 5.1 本地离线压测回归（不出错为第一目标）：`test/perf/local_load_test.py` 在 `JOB_MAX_CONCURRENT=5/10/20` 下分别跑压测并对比吞吐/排队等待/失败率
- [ ] 5.2 线上小流量验证计划（手工）：开启 4 路并行参数后，观测超时率、429、平均/长尾耗时与队列等待变化（必要时回滚到更保守参数）

---

## 任务状态符号
- `[ ]` 待执行
- `[√]` 已完成
- `[X]` 执行失败
- `[-]` 已跳过
- `[?]` 待确认
