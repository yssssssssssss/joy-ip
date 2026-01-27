# 变更提案: joy-running-log-bar 跑马灯日志条

## 需求背景
当前线上使用 `frontend_dist/` 的静态构建产物对外提供页面。现有 `joy-running-log-bar` 功能需要在 `frontend/` 源码内实现与维护，避免仅改 `frontend_dist/` 导致后续 build/export 被覆盖丢失。

## 变更内容
1. 将运行日志条稳定挂载在 ChatInput 卡片容器（`w-full max-w-[915px] rounded-[30px] border border-white/15 bg-[#202126] shadow-[0_8px_24px_rgba(0,0,0,0.35)]`）上方。
2. 运行日志条文本改为单行跑马灯滚动展示最新一条 `job.latest_log`（任务日志）。
3. 任务结束（成功/失败/取消）后延迟 1 秒自动隐藏日志条。

## 影响范围
- **模块:** frontend
- **文件:** `frontend/src/components/ChatInterface.tsx`、`frontend/src/components/ChatInput.tsx`、`frontend/src/components/RunningLogBar.tsx`（可能附加 `frontend/src/app/globals.css` 用于动画）
- **API:** 无（继续使用 `GET /api/job/<job_id>/status` 的 `latest_log`）
- **数据:** 无

## 核心场景

### 需求: 运行日志条跑马灯展示
**模块:** frontend

在用户提交分析/生成任务后，页面在输入框上方持续展示最新任务日志，帮助用户确认后台仍在运行。

#### 场景: 生成任务进行中
- 运行日志条出现在 ChatInput 卡片上方
- 文本为 `job.latest_log`（无则显示排队/处理中提示）
- 文本为单行跑马灯滚动展示

#### 场景: 任务结束
- 任务状态变为 succeeded/failed/cancelled 后保持显示 1 秒
- 1 秒后自动隐藏

## 风险评估
- **风险:** 跑马灯动画可能造成轻微性能开销
- **缓解:** 仅在文本溢出时启用动画；支持 `prefers-reduced-motion` 关闭动画
