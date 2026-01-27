# 任务清单: 生成流程运行日志条（输入框上方）

目录: `helloagents/plan/202601161723_running_log_bar/`

---

## 1. backend（任务状态携带最新日志）
- [√] 1.1 在 `utils/job_manager.py` 中为 `Job.to_dict()` 增加 `latest_log` / `logs_count` 字段，验证 why.md#需求-生成流程展示实时日志-场景-生成阶段展示日志
- [√] 1.2 在 `app_new.py` 的 `/api/job/<job_id>/status` 响应中确认字段透传与兼容性，验证 why.md#需求-生成流程展示实时日志-场景-生成阶段展示日志

## 2. frontend（滑入式一行日志条）
- [√] 2.1 新增日志条组件（单行截断 + 滑入/滑出），放置于输入框上方，验证 why.md#需求-生成流程展示实时日志-场景-分析阶段展示日志
- [√] 2.2 在 `frontend/src/components/ChatInterface.tsx` 中接入分析轮询与生成轮询的 `latest_log` 更新逻辑，验证 why.md#需求-生成流程展示实时日志-场景-生成阶段展示日志
- [√] 2.3 处理排队/无日志/任务结束状态的显示与清空策略，验证 why.md#需求-生成流程展示实时日志-场景-生成阶段展示日志

## 3. 安全检查
- [√] 3.1 执行安全检查（按G9: 输入验证、敏感信息处理、权限控制、EHRB风险规避）

## 4. 文档更新
- [√] 4.1 更新 `helloagents/wiki/api.md`（补充 `latest_log` / `logs_count` 字段说明）
- [√] 4.2 更新 `helloagents/CHANGELOG.md`（记录本次新增能力）

## 5. 测试
- [-] 5.1 本地回归：分析阶段日志更新、排队阶段占位、生成阶段日志更新、成功/失败/取消后自动隐藏
  > 备注: 当前环境缺少 `frontend/node_modules`，未执行完整前后端联调回归；仅完成 Python 语法检查（`py_compile`）。
