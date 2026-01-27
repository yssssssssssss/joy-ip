# 数据模型

## 1. 持久化存储
- **图片文件:** 生成结果落盘到 `output/` 或 `generated_images/`，通过静态路径提供给前端访问。
- **无数据库:** 当前未使用数据库或持久化任务存储。

## 2. 运行时数据
- **任务状态:** `utils.job_manager.JobManager` 以进程内内存保存任务（含队列信息、进度、错误与任务日志）。
- **前端本地状态:** 聊天消息与输入等通过 `localStorage` 保存（见 `frontend/src/app/providers.tsx`）。

