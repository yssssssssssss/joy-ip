# 任务清单: head 素材检索 query 英文翻译+补全（CLIP）

目录: `helloagents/plan/202602041026_head_clip_query_enrich/`

---

## 1. head 检索 query 生成
- [√] 1.1 新增“整段用户描述 → 英文短 query（可补全）”的生成函数（LLM 优先，失败回退到旧逻辑）
- [√] 1.2 增加必要的输出清洗与兜底校验（只取英文短语、限制长度、避免离线返回污染）

## 2. 接入检索链路
- [√] 2.1 3D：`HeadMatcher.find_best_matches_from_folder()` 改为使用新的英文 query 生成逻辑
- [√] 2.2 2D：`HeadMatcher2D.find_best_matches_2d()` 的缓存检索分支也使用新的英文 query

## 3. 配置与文档
- [√] 3.1 在 `.env.example` 中新增相关开关/模型配置项说明
- [√] 3.2 更新 `helloagents/wiki/modules/backend.md` 说明该行为与环境变量
- [√] 3.3 更新 `helloagents/CHANGELOG.md` 记录本次变更（Unreleased）

## 4. 验证
- [√] 4.1 快速冒烟：构造 2-3 条中文描述，确保 query 生成与回退逻辑可运行（不强依赖外网）

---

## 任务状态符号
- `[ ]` 待执行
- `[√]` 已完成
- `[X]` 执行失败
- `[-]` 已跳过
- `[?]` 待确认
