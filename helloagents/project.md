# 项目技术约定

## 技术栈
- **后端:** Python / Flask（见 `requirements.txt`）
- **前端:** Next.js / React / TypeScript（见 `frontend/package.json`）
- **样式:** Tailwind CSS

## 开发约定
- **目录约定:** 前端代码在 `frontend/`，后端入口为 `app_new.py`
- **命名约定:** TypeScript/React 使用 `PascalCase` 组件名与 `camelCase` 变量名；Python 使用 `snake_case`
- **API约定:** 统一使用 `/api/*` 路径；开发环境通过 Next.js rewrite 代理到后端

## 错误与日志
- **后端日志:** Flask `logger` 记录服务日志；任务内日志通过 `utils.job_manager.JobManager.append_log` 记录并随任务状态返回
- **前端错误:** 优先以用户可理解的提示展示；必要时保留 `request_id` 便于排查

## 测试与流程
- **前端:** `frontend/package.json` 中 `lint`（Next.js lint）
- **后端:** 以 API 联调与关键路径手工回归为主（生成链路耗时较长）

