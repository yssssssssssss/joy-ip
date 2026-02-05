# API 手册

## 概述
后端提供 `/api/*` HTTP 接口，前端在开发环境通过 Next.js `rewrites()` 代理到后端（见 `frontend/next.config.dev.js` / `frontend/next.config.js`）。

## 接口列表（关键路径）

### 生成链路

#### [POST] /api/analyze
**描述:** 需求内容分析与合规检查；支持 `async=true` 异步分析并返回 `job_id`。

#### [POST] /api/start_generate
**描述:** 启动异步生成任务并返回 `job_id`；支持传入用户确认/编辑后的 `analysis`。

**错误说明:**
- 当队列已满时返回 `503`，并携带 `code=QUEUE_FULL`

**补充（2D 底图）:**
- 可选字段 `base_image_url`：来自 2D 素材编辑器的底图 URL（如 `/output/2d_editor/xxx_gray_bg.png`）
- 当 `mode=2D` 且提供 `base_image_url` 时，后端 2D 链路会跳过“匹配头/身 + step1 拼装”，直接进入配件/背景/Gate 等后续步骤

#### [GET] /api/job/<job_id>/status
**描述:** 查询任务状态（排队/运行/完成/失败等），用于前端轮询展示进度与结果。

**响应补充字段:**
- `job.latest_log`: 最新一条任务日志（来自 `JobManager.append_log`）
- `job.logs_count`: 当前任务日志条数
- `job.stage_timings`: 阶段耗时记录（如 `queued/match/compose/...`），用于性能分析与定位慢点

#### [POST] /api/job/<job_id>/cancel
**描述:** 取消排队中的任务。

#### [GET] /api/queue/stats
**描述:** 获取队列统计信息（运行数、等待数、并发数、平均耗时）。

**补充字段:**
- `avg_duration/p50_duration/p95_duration`：近一段时间任务执行耗时的均值/分位数（秒）
- `queue_max_size`：队列最大长度（超过会拒绝新任务并返回 503）

### 3D 编辑器链路

#### [POST] /api/run-3d-banana
**描述:** 执行 3D 渲染图后处理脚本并返回单张图片 URL（同步）。

### 2D 素材编辑器链路

#### [GET] /api/2d_assets
**描述:** 按视角/类型/动作列出 2D 素材列表（文件名排序），供前端弹窗展示网格预览。

**请求参数:**
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| perspective | string | 是 | `正视角` / `仰视角` |
| type | string | 是 | `head` / `body` |
| action | string | 否 | `站姿/欢快/跳跃/跑动/坐姿`（仅 `type=body` 时需要） |

**响应:**
```json
{
  "success": true,
  "items": [
    { "name": "1.png", "url": "/data/2d/frontview/head/1.png" }
  ]
}
```

#### [POST] /api/2d_editor/compose
**描述:** 2D 编辑器拼装接口：给定 head/body 素材 URL 与动作类型，调用 `per-data-2D.py` 拼装并返回：
- `preview_url`：透底 `2000x2000` 预览图（用于编辑器“拼装结果”区域展示）
- `base_image_url`：灰底 `1024x1200` 底图（用于后续 2D 生成链路输入）

**请求:**
```json
{
  "head_url": "/data/2d/frontview/head/1.png",
  "body_url": "/data/2d/frontview/body_stand/2d-stand-1.png",
  "action_type": "站姿"
}
```

**响应:**
```json
{
  "success": true,
  "preview_url": "/output/2d_editor/2d_editor_xxx.png",
  "base_image_url": "/output/2d_editor/2d_editor_xxx_gray_bg.png",
  "url": "/output/2d_editor/2d_editor_xxx_gray_bg.png"
}
```

#### [GET] /data/2d/<path:filename>
**描述:** 2D 素材静态访问（仅允许 png），用于前端 `<img src>` 直接预览素材缩略图。
