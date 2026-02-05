# 模块: frontend

## 职责
- 提供聊天式 UI（输入、消息展示、图片预览/下载）
- 驱动分析预览、生成任务启动与任务状态轮询
- 显示排队信息与生成中状态
- 提供 JOY 3D 编辑器弹窗并与生成流程衔接（渲染预览/保存路径）
- 提供 2D 素材编辑器弹窗（头/身素材选择拼装）并将底图接入 2D 生成流程

## 关键文件
- `frontend/src/components/ChatInterface.tsx`：主交互编排（分析/生成/轮询）
- `frontend/src/components/ThreeEditorModal.tsx`：JOY 3D 编辑器弹窗（遮罩层/自适配尺寸/iframe 主区域 1:1）
- `frontend/src/components/TwoDEditorModal.tsx`：2D 素材编辑器弹窗（表情/动作选择、拼装预览、使用为底图）
- `frontend/src/components/ChatInput.tsx`：输入卡片与运行日志条挂载位置（运行日志条位于卡片容器上方）
- `frontend/src/components/MessageArea.tsx`：消息区与排队/生成中展示
- `frontend/src/components/RunningLogBar.tsx`：输入框上方的运行日志条（展示最新任务日志，单行跑马灯滚动）
- `frontend/src/app/globals.css`：运行日志条跑马灯动画样式（`joy-running-log-marquee`）
- `frontend_dist/`：Next.js 静态导出产物目录（生产环境对外服务用），应通过 build/export 生成而非手改
- `frontend/src/app/providers.tsx`：聊天状态与本地持久化
- `frontend/src/lib/api.ts`：API 客户端与类型
- `frontend/public/three-editor/*`：静态 3D 编辑器页面（通过 `iframe` 在弹窗中加载）

## 构建与导出
- 生产环境（单端口模式）前端静态产物目录为 `frontend_dist/`，不要手工修改，应通过导出流程生成
- 执行 `npm -C frontend run export:unix` 生成 `frontend/out/` 并同步到 `frontend_dist/`
- 备注：当前运行环境下跨目录 `rename()` 会返回 `EXDEV`，`export:unix` 已通过 `frontend/scripts/rename-exdev-fix.cjs` 预加载补丁将 `fs.promises.rename` 降级为 copy+unlink，确保 Next.js 静态导出可完成

## 3D 编辑器尺寸约定
- 弹窗（宿主页面）：`ThreeEditorModal` 以窗口高度为标准计算弹窗尺寸；扣除头/底栏后，iframe 编辑器区域严格 1:1
- 画布（iframe 内）：`three-editor` 的 `canvas` 按 `1024x1200` 比例在可用区域内等比缩放并居中展示（不拉伸），toolbar/approved-row 等 UI 会随尺寸响应式收缩

## 2D 编辑器预览/底图约定
- “拼装结果”区域展示 `preview_url`（透底 `2000x2000`）
- 点击“使用”后写入预览条/透传后端的是 `base_image_url`（灰底 `1024x1200`）
