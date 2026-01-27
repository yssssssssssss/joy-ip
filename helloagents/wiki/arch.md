# 架构设计

## 总体架构
```mermaid
flowchart TD
  U[用户浏览器] --> FE[Next.js 前端\nfrontend/]
  FE -->|/api/*| BE[Flask 后端\napp_new.py]
  BE --> JM[JobManager\nutils/job_manager.py]
  JM --> PIPE[生成链路\nGenerationController* 等]
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
当前暂无独立 ADR 索引（后续在变更的 `how.md` 中维护并在此处追加链接）。

