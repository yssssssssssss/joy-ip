# 技术设计: joy-running-log-bar 跑马灯日志条

## 技术方案

### 核心技术
- Next.js / React / TypeScript
- Tailwind CSS（配合少量全局 keyframes）
- 继续使用现有轮询逻辑：`ChatInterface` → `GET /api/job/<job_id>/status`

### 实现要点
- **数据:** 保留现有 `runningLog` 与 `updateRunningLog(job.latest_log)`；任务开始 `runningLogActive=true`；任务结束通过 `setTimeout(1000)` 延迟隐藏并清理。
- **位置:** 将日志条渲染收口到 `ChatInput`（`variant="center"`），放置在卡片容器上方，复用相同居中与 maxWidth；移除 `ChatInterface` 中的重复渲染块。
- **跑马灯:** `RunningLogBar` 内部测量文本与容器宽度（仅溢出时启用），通过 CSS 变量控制滚动距离与时长；文本更新时重算并重启动画。
- **动效降级:** 在 `prefers-reduced-motion: reduce` 下禁用动画并回退为截断显示，避免强制动效。

## 安全与性能
- **安全:** 仅展示后端返回日志文本，不解析/执行内容（避免 `dangerouslySetInnerHTML`）。
- **性能:** 测量仅在 `text/visible` 变化时触发；动画仅在文本溢出时启用；结束延迟 1 秒再隐藏避免频繁闪烁。

## 测试与部署
- **测试:** 手工回归：提交 analyze/生成任务，观察日志条位置、跑马灯滚动、结束 1 秒后隐藏；取消任务同样符合。
- **部署:** 修改 `frontend/` 后执行 `npm run build` + `npm run export:unix`（或现有 export 流程），确认 `frontend_dist/` 产物效果一致。
