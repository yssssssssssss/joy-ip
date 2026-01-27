# API 429错误修复：频率限制问题

## 问题描述

### 错误信息
```
HTTP 400
error: {
  "code": 429,
  "message": "Resource exhausted. Please try again later.",
  "status": "RESOURCE_EXHAUSTED"
}
```

### 问题原因
1. **并发请求过多**: 项目使用4路并发处理图片，同时向 Google Vertex AI API 发送多个请求
2. **API配额限制**: Google API 有每分钟/每秒的请求频率限制
3. **90秒超时优化的副作用**: 虽然90秒超时能更快重试，但也可能导致更频繁的API调用

## 解决方案

### 方案1：降低并发数 ✅

**修改文件**: 
- `generation_controller.py`
- `generation_controller_2d.py`

**修改内容**:
```python
# 从 4 降低到 2
MAX_PARALLEL_WORKERS = int(os.environ.get("MAX_PARALLEL_WORKERS", "2"))
MAX_PARALLEL_WORKERS_2D = int(os.environ.get("MAX_PARALLEL_WORKERS_2D", "2"))
```

**效果**:
- 同时发送的API请求从4个减少到2个
- 降低50%的并发压力
- 减少触发429错误的概率

### 方案2：增加请求间隔 ✅

**修改文件**: `banana-pro-img-jd.py`

**修改内容**:
```python
# 每个请求前延迟0.5秒
time.sleep(0.5)
```

**效果**:
- 请求之间有0.5秒的间隔
- 避免瞬间大量请求
- 更平滑的API调用频率

### 方案3：已有的429错误处理 ✅

代码中已经有429错误的处理逻辑：

```python
if response.status_code == 429:
    if attempt < max_retries - 1:
        wait_time = retry_delay * (2 ** attempt)  # 指数退避：2秒、4秒、8秒
        print(f"遇到频率限制(429)，等待 {wait_time} 秒后重试...")
        time.sleep(wait_time)
        continue
```

**效果**:
- 遇到429错误时自动重试
- 使用指数退避策略（2秒、4秒、8秒）
- 最多重试3次

## 修改总结

### 修改前
- 并发数: 4个worker
- 请求间隔: 无
- 429处理: 有（指数退避）

### 修改后
- 并发数: 2个worker ✅
- 请求间隔: 0.5秒 ✅
- 429处理: 有（指数退避）✅

## 预期效果

1. **降低API调用频率**: 并发数减半 + 请求间隔 = 更低的频率
2. **减少429错误**: 不会完全消除，但会显著减少
3. **自动恢复**: 即使遇到429，也会自动重试

## 性能影响

### 处理时间变化
- **修改前**: 4张图片并发处理，理论最快时间 = 单张时间
- **修改后**: 2张图片并发处理，理论最快时间 = 单张时间 × 2

### 实际影响
- 对于2-4张图片：影响较小（增加约30-50%时间）
- 对于大量图片：影响较大，但避免了429错误导致的失败

## 如何调整

如果仍然遇到429错误，可以进一步调整：

### 1. 降低并发数到1
```bash
export MAX_PARALLEL_WORKERS=1
export MAX_PARALLEL_WORKERS_2D=1
```

### 2. 增加请求间隔
在 `banana-pro-img-jd.py` 中修改：
```python
time.sleep(1.0)  # 从0.5秒增加到1秒
```

### 3. 增加重试延迟
```python
retry_delay = 5  # 从2秒增加到5秒
```

## 监控建议

1. **观察日志中的429错误频率**
   ```bash
   grep "429" logs/*.log | wc -l
   ```

2. **监控重试成功率**
   - 如果重试后大部分成功，说明配置合理
   - 如果重试后仍然失败，需要进一步降低频率

3. **检查API配额使用情况**
   - 登录 Google Cloud Console
   - 查看 Vertex AI API 的配额使用情况
   - 考虑申请更高的配额

## 相关文档
- `TIMEOUT_90S_UPDATE.md` - 90秒超时优化
- `RETRY_MECHANISM_GUIDE.md` - 重试机制说明
- Google Vertex AI 错误代码文档: https://cloud.google.com/vertex-ai/generative-ai/docs/error-code-429
