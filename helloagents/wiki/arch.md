# 架构设计

## 总体架构
```mermaid
flowchart TD
  U[用户浏览器] --> FE[Next.js 前端\nfrontend/]
  FE -->|/api/*| BE[Flask 后端\napp_new.py]
  BE --> JM[JobManager\nutils/job_manager.py]
  JM --> PIPE[生成链路\nGenerationController* 等]
  PIPE --> LIMIT[外部调用限流与超时治理\nutils/limits.py + utils/http_client.py]
  LIMIT --> EXT[(外部模型服务\nJDCloud ModelService)]
  PIPE --> FS[(文件系统\noutput/ generated_images/)]
  BE --> FS
  FE -->|/output /generated_images| FS
```

## 技术栈
- **后端:** Python / Flask
- **前端:** Next.js / React / TypeScript
- **任务:** 后端 JobQueue（并发控制 + 排队）
- **存储:** 文件系统为主（无数据库依赖）

## 核心流程
```mermaid
sequenceDiagram
  participant User as 用户
  participant FE as 前端
  participant BE as 后端

  User->>FE: 输入并点击生成
  FE->>BE: POST /api/analyze (async)
  loop 轮询
    FE->>BE: GET /api/job/{job_id}/status
    BE-->>FE: job.status + latest_log
  end
  FE-->>User: 展示预分析预览（可编辑）
  User->>FE: 确认生成
  FE->>BE: POST /api/start_generate
  loop 轮询
    FE->>BE: GET /api/job/{job_id}/status
    BE-->>FE: job.status + queue_position + latest_log
  end
  FE-->>User: 展示生成图片结果
```

## 重大架构决策
完整 ADR 记录在各变更的 `how.md` 中，本章节提供索引。

| adr_id | title | date | status | affected_modules | details |
|--------|-------|------|--------|------------------|---------|
| ADR-001 | 方案1保持单进程状态一致性 | 2026-02-02 | ✅已采纳 | backend | [how.md](../history/2026-02/202602022301_perf_4x_throughput/how.md) |
| ADR-002 | 外部调用使用独立配额池并统一重试 | 2026-02-02 | ✅已采纳 | backend | [how.md](../history/2026-02/202602022301_perf_4x_throughput/how.md) |

