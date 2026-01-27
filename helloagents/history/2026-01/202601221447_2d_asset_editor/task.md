# 任务清单: 2D素材编辑器（头身选择拼装 + 作为底图进入生成）

目录: `helloagents/plan/202601221447_2d_asset_editor/`

---

## 1. 前端（2D编辑器 UI + 状态编排）
- [√] 1.1 在 `frontend/src/components/ChatInput.tsx` 增加“2D素材生成”按钮（仅 2D 模式显示，位于“场景”按钮右侧），并透出打开弹窗回调，验证 why.md#需求:-打开-2D-素材编辑器-场景:-从对话框入口打开
- [√] 1.2 新增 `frontend/src/components/TwoDEditorModal.tsx`：左侧“表情/动作”素材网格（按文件名排序、无默认选中、视角联动目录），右侧“生成结果”展示与“重试/使用”，验证 why.md#需求:-生成拼装预览-场景:-调用拼装接口并展示
- [√] 1.3 在 `frontend/src/components/ChatInterface.tsx` 接入 2D 编辑器弹窗状态与“底图预览条”（仅保留 1 张，支持清除/替换；切换视角或切换 2D/3D 自动清空），验证 why.md#需求:-使用底图进入生成链路
- [√] 1.4 在 `frontend/src/components/ChatInterface.tsx` 调用 `/api/start_generate` 时携带 `base_image_url`（当存在底图时），并在 prompt 含表情/动作关键词时提示“底图已锁定动作表情，仅处理配件/背景”，验证 why.md#需求:-使用底图进入生成链路-场景:-prompt-继续生成（锁定动作表情）
- [√] 1.5 更新 `frontend/next.config.js`：开发态新增 `/data/2d/:path*` rewrite 到后端，保证素材预览可加载

## 2. 后端（素材列表/拼装接口 + 2D链路跳过 step1）
- [√] 2.1 在 `app_new.py` 新增静态路由 `/data/2d/<path:filename>`，仅服务 `data/2d/**`，验证 why.md#需求:-按视角选择表情与动作素材
- [√] 2.2 在 `app_new.py` 新增 `GET /api/2d_assets`：按 `perspective/type/action` 返回文件名排序列表，并做扩展名白名单校验
- [√] 2.3 在 `app_new.py` 新增 `POST /api/2d_editor/compose`：校验 head/body 路径后调用 `per-data-2D.py` 拼装，输出白底 1024x1200 并返回 `/output/...` URL，验证 why.md#需求:-生成拼装预览
- [√] 2.4 扩展 `POST /api/start_generate`：接受并存储 `base_image_url` 到 job；在 2D 生成流程中透传给控制器
- [√] 2.5 修改 `generation_controller_2d.py`：`generate_complete_flow` 增加 `base_image_path` 可选参数，存在时跳过“匹配头/身 + step1 拼装”，直接进入配件/背景/Gate，验证 why.md#需求:-使用底图进入生成链路-场景:-prompt-继续生成（锁定动作表情）

## 3. 安全检查
- [√] 3.1 执行安全检查：接口参数校验、路径白名单、拒绝 `..`、限制可访问目录，避免任意文件读取风险

## 4. 文档更新
- [√] 4.1 更新 `helloagents/wiki/api.md`：补充 `GET /api/2d_assets`、`POST /api/2d_editor/compose`、`/data/2d/*` 与 `/api/start_generate` 扩展字段说明
- [√] 4.2 更新 `helloagents/wiki/modules/frontend.md`、`helloagents/wiki/modules/backend.md`：补充 2D 编辑器能力与新增接口
- [√] 4.3 更新 `helloagents/CHANGELOG.md` 记录新增功能

## 5. 验证（手工回归）
- [?] 5.1 回归：2D 模式打开弹窗→选择表情/动作→生成→重试→再生成→使用→输入 prompt 生成（验证跳过 step1）
- [?] 5.2 回归：切换视角与切换 2D/3D → 底图预览条自动清空；素材目录随视角变化且列表按文件名排序

---

## 任务状态符号
- `[ ]` 待执行
- `[√]` 已完成
- `[X]` 执行失败
- `[-]` 已跳过
- `[?]` 待确认
