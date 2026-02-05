# 变更历史索引

本文件记录所有已完成变更的索引，便于追溯和查询。

## 索引

| 时间戳 | 功能名称 | 类型 | 状态 | 方案包路径 |
|--------|----------|------|------|------------|
| 202601161723 | running_log_bar | 功能 | ✅已完成 | [2026-01/202601161723_running_log_bar](2026-01/202601161723_running_log_bar/) |
| 202601201020 | joy_running_log_bar | 修复 | ✅已完成 | [2026-01/202601201020_joy_running_log_bar](2026-01/202601201020_joy_running_log_bar/) |
| 202601221138 | joy3d-modal | 变更 | ✅已完成 | [2026-01/202601221138_joy3d-modal](2026-01/202601221138_joy3d-modal/) |
| 202601221447 | 2d_asset_editor | 功能 | ✅已完成 | [2026-01/202601221447_2d_asset_editor](2026-01/202601221447_2d_asset_editor/) |
| 202601221604 | joy3d-modal-fix | 修复 | ✅已完成 | [2026-01/202601221604_joy3d-modal-fix](2026-01/202601221604_joy3d-modal-fix/) |
| 202601221722 | joy3d-canvas-layout | 修复 | ✅已完成 | [2026-01/202601221722_joy3d-canvas-layout](2026-01/202601221722_joy3d-canvas-layout/) |
| 202602041026 | head_clip_query_enrich | 变更 | ✅已完成 | [2026-02/202602041026_head_clip_query_enrich](2026-02/202602041026_head_clip_query_enrich/) |

## 按月归档

### 2026-01

- [202601161723_running_log_bar](2026-01/202601161723_running_log_bar/) - 输入框上方滑入运行日志条，展示任务最新日志
- [202601201020_joy_running_log_bar](2026-01/202601201020_joy_running_log_bar/) - 运行日志条跑马灯滚动展示最新日志，任务结束延迟隐藏，位置在 ChatInput 卡片上方
- [202601221138_joy3d-modal](2026-01/202601221138_joy3d-modal/) - JOY 3D 编辑器改为弹窗并自适配尺寸，关闭不清空生成记录
- [202601221447_2d_asset_editor](2026-01/202601221447_2d_asset_editor/) - 2D 素材编辑器：选择表情/动作素材拼装底图，并作为后续生成链路输入
- [202601221604_joy3d-modal-fix](2026-01/202601221604_joy3d-modal-fix/) - 修复 3D 编辑器弹窗比例与关闭后聊天记录本地持久化
- [202601221722_joy3d-canvas-layout](2026-01/202601221722_joy3d-canvas-layout/) - 修复 3D 编辑器画布按 `1024x1200` 比例居中适配，toolbar/预审区响应式收缩并减少占用画布高度

### 2026-02

- [202602041026_head_clip_query_enrich](2026-02/202602041026_head_clip_query_enrich/) - head 素材检索 query 英文翻译+补全（CLIP）
