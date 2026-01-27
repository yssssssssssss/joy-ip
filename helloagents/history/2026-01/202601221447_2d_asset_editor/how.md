# 技术设计: 2D素材编辑器（头身选择拼装 + 作为底图进入生成）

## 技术方案

### 核心技术
- 前端：Next.js / React / TypeScript（新增 2D 编辑器弹窗组件与状态编排）
- 后端：Flask（新增素材列表/拼装 API，扩展 2D 生成链路支持“底图直入”）
- 拼装：复用 `per-data-2D.py` 的 `compose_images_new_logic`（输出白底 1024x1200）

### 实现要点
- **前端入口与弹窗**
  - 在 `frontend/src/components/ChatInput.tsx` 的预设按钮区，2D 模式下在“场景”按钮右侧新增“2D素材生成”按钮。
  - 新增 `frontend/src/components/TwoDEditorModal.tsx`：左侧素材选择（表情/动作），右侧结果预览（生成/重试/使用）。
- **素材获取与展示**
  - 后端提供素材列表接口，按文件名排序返回可访问 URL（随视角切换目录）。
  - 后端提供静态资源路由 `/data/2d/<path>` 以便前端 `<img>` 直接加载素材。
- **拼装预览生成**
  - 后端新增拼装接口，输入 head/body 资源路径与动作类型，调用 `per-data-2D.py` 输出白底 1024x1200 图片，返回 `/output/...` URL。
- **底图复用与链路跳过**
  - 前端“使用”后在输入框上方展示预览条（仅保留 1 张，支持清除/替换）；切换视角或切换 2D/3D 自动清空。
  - 前端在调用 `/api/start_generate` 时携带 `base_image_url`（可选）；后端保存到 job，并在 2D 生成流程中传入 `GenerationController2D.generate_complete_flow(base_image_path=...)`。
  - `GenerationController2D.generate_complete_flow` 增加可选参数，当提供 `base_image_path` 时跳过“匹配头/身 + step1 拼装”，直接从该底图进入配件/背景/Gate 等后续步骤。
- **提示策略**
  - 当底图存在且用户输入 prompt 包含表情/动作描述关键词时，前端提示“底图已锁定动作表情，仅处理配件/背景”。

## 架构设计
本次为既有“2D/3D 生成链路 + JobManager”架构的增量扩展，不引入新服务。

## 架构决策 ADR

### ADR-001: 2D素材列表来源采用后端接口（而非前端静态清单）
**上下文:** 前端为静态导出应用，运行时无法直接读取服务器文件系统目录；需要展示素材网格并随视角切换目录。
**决策:** 提供后端素材列表接口 `GET /api/2d_assets`，按视角/类型/动作返回文件名排序列表。
**理由:** 降低前端维护成本；素材增删无需重新打包前端（但本需求不要求热更新监听）。
**替代方案:** 前端内置静态 manifest（JSON/常量）→ 拒绝原因: 需要手工同步素材变更，易失真。
**影响:** 后端需增加路径白名单校验，避免目录遍历与越权读取。

## API设计

### [GET] /api/2d_assets
- **请求:**
  - `perspective`: `正视角|仰视角`
  - `type`: `head|body`
  - `action`: `站姿|欢快|跳跃|跑动|坐姿`（仅 `type=body` 时需要）
- **响应:**
  - `success: boolean`
  - `items: { name: string; url: string }[]`（按文件名排序）

### [POST] /api/2d_editor/compose
- **请求:**
  - `head_url`: `/data/2d/...png`
  - `body_url`: `/data/2d/...png`
  - `action_type`: `站姿|欢快|跳跃|跑动|坐姿`
- **响应:**
  - `success: boolean`
  - `url: string`（如 `/output/2d_editor/xxx_white_bg.png`）

### [POST] /api/start_generate（扩展字段）
- **请求（新增可选字段）:**
  - `base_image_url?: string`（如 `/output/2d_editor/xxx_white_bg.png`）
- **行为:**
  - `mode=2D` 且存在 `base_image_url` 时，2D 链路从该底图开始处理配件/背景/Gate，跳过头/身匹配与拼装

### [GET] /data/2d/<path:filename>
- **用途:** 提供 2D 素材静态访问（供前端素材预览）

## 安全与性能
- **安全:**
  - 素材列表与拼装接口对路径做规范化，拒绝包含 `..` 的路径
  - 仅允许访问 `data/2d/**` 目录；仅允许白名单扩展名（如 `.png`）
  - `base_image_url` 仅允许 `output/**`（或固定子目录）以避免任意文件读取
- **性能:**
  - 素材列表按需拉取（打开弹窗或切换视角/动作时请求）
  - 拼装接口生成单张底图，避免批量生成

## 测试与部署
- **测试:**
  - 手工回归：打开弹窗→选择表情/动作→生成→使用→继续生成→验证后端跳过 step1
  - 切换视角/切换 2D/3D → 底图预览条自动清空
- **部署:**
  - 前端开发态补充 Next.js rewrite：`/data/2d/*` 代理到后端
  - 生产态若由后端单端口模式提供静态文件，则 `/data/2d/*` 路由由后端直接提供
