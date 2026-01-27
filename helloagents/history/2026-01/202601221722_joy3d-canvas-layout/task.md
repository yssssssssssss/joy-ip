# 任务清单: joy3d-canvas-layout

## 1. iframe 内 canvas 展示比例修复
- [√] 1.1 canvas 按 1024x1200 等比例缩放并居中展示（不拉伸）
- [√] 1.2 视窗尺寸变化时，canvas/renderer 自动重算尺寸
- [√] 1.3 高清渲染过程不改变画布可视尺寸（仅改 buffer）

## 2. iframe 内 UI 响应式改造
- [√] 2.1 toolbar/按钮尺寸用 `clamp()` 自适应缩放，避免固定高度
- [√] 2.2 approved-row 保持单行（必要时横向滚动），减少占用 canvas 高度
- [√] 2.3 light-control 面板允许收缩（min-width 动态），文本在小屏可省略

## 3. 弹窗产物同步与回归
- [√] 3.1 重新导出前端静态产物到 `frontend_dist/`
- [√] 3.2 回归：打开/关闭 3D 编辑器不清空聊天历史；布局在不同屏幕下符合预期
