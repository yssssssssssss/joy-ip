# API 429错误修复 ✅

## 问题
**错误代码**: 429 - Resource Exhausted  
**原因**: Google API 频率限制，并发请求过多

## 解决方案

### 1. 降低并发数 ✅
- **从 4 降低到 2**
- 修改文件: `generation_controller.py`, `generation_controller_2d.py`
- 效果: 同时发送的API请求减少50%

### 2. 增加请求间隔 ✅
- **每个请求前延迟 0.5秒**
- 修改文件: `banana-pro-img-jd.py`
- 效果: 避免瞬间大量请求

### 3. 已有的重试机制 ✅
- 遇到429错误自动重试（最多3次）
- 指数退避: 2秒 → 4秒 → 8秒
- 无需额外修改

## 修改内容

### generation_controller.py
```python
# 从 4 改为 2
MAX_PARALLEL_WORKERS = int(os.environ.get("MAX_PARALLEL_WORKERS", "2"))
```

### generation_controller_2d.py
```python
# 从 4 改为 2
MAX_PARALLEL_WORKERS_2D = int(os.environ.get("MAX_PARALLEL_WORKERS_2D", "2"))
```

### banana-pro-img-jd.py
```python
# 添加请求前延迟
time.sleep(0.5)
```

## 效果对比

| 项目 | 修改前 | 修改后 |
|------|--------|--------|
| 并发数 | 4个 | 2个 ✅ |
| 请求间隔 | 无 | 0.5秒 ✅ |
| 429处理 | 有 | 有 ✅ |

## 性能影响
- **处理时间**: 增加约30-50%（但避免了失败）
- **成功率**: 显著提升（减少429错误）
- **用户体验**: 更稳定，不会频繁失败

## 如果还遇到429错误

### 方法1: 进一步降低并发
```bash
export MAX_PARALLEL_WORKERS=1
export MAX_PARALLEL_WORKERS_2D=1
```

### 方法2: 增加请求间隔
修改 `banana-pro-img-jd.py`:
```python
time.sleep(1.0)  # 从0.5秒增加到1秒
```

### 方法3: 增加重试延迟
修改 `banana-pro-img-jd.py`:
```python
retry_delay = 5  # 从2秒增加到5秒
```

## 监控建议
1. 观察日志中429错误的频率
2. 如果仍然频繁出现，继续降低并发或增加间隔
3. 考虑向Google申请更高的API配额

详细文档: `API_429_ERROR_FIX.md`
