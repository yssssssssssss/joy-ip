# Timeout 更新为 10 分钟

## 修改原因
由于模型访问出现比较明显的延迟，之前设置的 read timeout 都不适用了，需要将所有超时设置修改为 10 分钟（600 秒）。

## 修改范围

### 后端 Python 文件

#### 1. content_agent.py
**修改内容：**
- 更新违规词库：30秒 → 600秒
- AI 敏感内容检查：120秒 → 600秒
- AI 分析装扮：120秒 → 600秒
- AI 补全字段：120秒 → 600秒
- AI 合并分析：120秒 → 600秒

**修改数量：** 5 处

---

#### 2. matchers/base_matcher.py
**修改内容：**
- AI 匹配请求：60秒 → 600秒

**修改数量：** 1 处

---

#### 3. matchers/head_matcher.py
**修改内容：**
- AI 表情分析：30秒 → 600秒

**修改数量：** 1 处

---

#### 4. utils/image_uploader.py
**修改内容：**
- 图片上传：60秒 → 600秒

**修改数量：** 1 处

---

#### 5. utils/ai_client.py
**修改内容：**
- AI API 请求：30秒 → 600秒

**修改数量：** 1 处

---

#### 6. generation_controller.py
**修改内容：**
- 图片生成任务：60秒 → 600秒
- 图片处理任务：120秒 → 600秒
- Gate 检查任务：60秒 → 600秒

**修改数量：** 3 处

---

#### 7. utils/async_api.py
**修改内容：**
- 并行处理任务：120秒 → 600秒（2处）

**修改数量：** 2 处

---

#### 8. generation_controller_2d.py
**修改内容：**
- 图片生成任务：60秒 → 600秒
- 图片处理任务：120秒 → 600秒
- Gate 检查任务：60秒 → 600秒

**修改数量：** 3 处

---

#### 9. gate-result.py
**修改内容：**
- AI 请求：60秒 → 600秒（3处）

**修改数量：** 3 处

---

#### 10. banana-pro-img-jd.py
**修改内容：**
- 图片生成请求：120秒 → 600秒（3处）

**修改数量：** 3 处

---

### 前端 TypeScript 文件

#### 1. frontend/src/components/ChatInterface.tsx
**修改内容：**
- 分析任务轮询总时长：180秒（3分钟）→ 600秒（10分钟）

**修改位置：**
```typescript
// 之前
const deadline = Date.now() + 180000  // 3分钟

// 现在
const deadline = Date.now() + 600000  // 10分钟
```

**说明：**
- 这是分析任务状态轮询的最大等待时间
- 单次请求已经没有超时限制（timeout: 0）
- 但总轮询时长仍有限制，防止无限等待

---

## 修改统计

### 后端
- **修改文件数：** 10 个
- **修改位置数：** 24 处
- **超时时间：** 30秒/60秒/120秒 → 600秒（10分钟）

### 前端
- **修改文件数：** 1 个
- **修改位置数：** 1 处
- **超时时间：** 180秒（3分钟）→ 600秒（10分钟）

### 总计
- **修改文件数：** 11 个
- **修改位置数：** 25 处

---

## 技术细节

### 后端超时格式
```python
# HTTP 请求超时
response = http_post(url, json=payload, headers=headers, timeout=600)

# 线程任务超时
result = future.result(timeout=600)

# 子进程超时
subprocess.run(cmd, timeout=600)
```

### 前端超时格式
```typescript
// Axios 请求超时（已取消）
{ timeout: 0 }  // 无超时限制

// 轮询总时长限制
const deadline = Date.now() + 600000  // 10分钟
```

---

## 影响分析

### 正面影响
1. ✅ 适应模型访问延迟
2. ✅ 减少超时错误
3. ✅ 提高任务成功率
4. ✅ 改善用户体验

### 注意事项
1. ⚠️ 长时间等待可能影响用户体验
2. ⚠️ 需要确保 RunningLogBar 显示实时进度
3. ⚠️ 用户仍可手动取消任务
4. ⚠️ 服务器资源占用时间更长

---

## 配套改进

### 1. 前端超时取消（已完成）
- 所有 Axios 请求的 timeout 设置为 0
- 详见：`TIMEOUT_CHANGES.md`

### 2. 日志显示改进（已完成）
- RunningLogBar 显示所有日志
- 用户可以看到实时进度
- 详见：`RUNNING_LOG_IMPROVEMENTS.md`

### 3. 轮询机制
- 保持 1.5 秒的轮询间隔
- 总轮询时长从 3 分钟延长到 10 分钟
- 用户可以看到持续的进度更新

---

## 测试建议

### 1. 正常场景
- 提交一个正常的生成请求
- 观察是否能在 10 分钟内完成

### 2. 慢速场景
- 在模型响应慢的情况下测试
- 确认不会提前超时

### 3. 超长场景
- 如果任务超过 10 分钟
- 确认会显示超时错误

### 4. 用户取消
- 测试用户手动取消功能
- 确认可以正常中断

---

## 回滚方案

如果需要恢复原来的超时设置：

### 后端
```bash
# 使用 git 恢复
git checkout HEAD -- content_agent.py matchers/ utils/ generation_controller.py generation_controller_2d.py gate-result.py banana-pro-img-jd.py
```

### 前端
```typescript
// 恢复为 3 分钟
const deadline = Date.now() + 180000
```

---

## 相关文档
- `TIMEOUT_CHANGES.md` - 前端超时取消
- `RUNNING_LOG_IMPROVEMENTS.md` - 日志显示改进
- `update_timeouts.py` - 批量更新脚本
- `TIMEOUT_UPDATE_10MIN.md` - 本文档

---

## 修改日期
2025-01-19

## 修改人员
Kiro AI Assistant
