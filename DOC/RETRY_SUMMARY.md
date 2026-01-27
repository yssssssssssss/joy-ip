# 重连机制快速参考

## 📋 三层重连架构

```
应用层 (banana-pro-img-jd.py)
  ↓ 3次重试 + 指数退避 (2s, 4s, 8s)
  
HTTP客户端层 (utils/http_client.py)
  ↓ 3次重试 + 指数退避 (1s, 2s, 4s)
  
urllib3层
  ↓ 自动处理 429/500/502/503/504
```

## ⚙️ 核心配置

### 1. HTTP 客户端层
**文件**: `utils/http_client.py`

```python
Retry(
    total=3,                                    # 重试3次
    backoff_factor=1.0,                         # 退避: 1s, 2s, 4s
    status_forcelist=[429, 500, 502, 503, 504], # 触发状态码
    respect_retry_after_header=True             # 遵守服务器限制
)

HTTPAdapter(
    pool_connections=10,    # 连接池: 10个连接
    pool_maxsize=20        # 最大: 20个连接
)
```

### 2. 应用层
**文件**: `banana-pro-img-jd.py`

```python
max_retries = 3         # 重试3次
retry_delay = 2         # 退避: 2s, 4s, 8s
timeout = 600           # 超时: 10分钟
```

### 3. 控制器层
**文件**: `generation_controller.py`, `generation_controller_2d.py`

```python
self.max_retries = 1    # 重试1次
```

## 📊 重试时间表

### HTTP 客户端层
| 尝试 | 等待时间 | 累计 |
|------|---------|------|
| 1 | 0s | 0s |
| 2 | 1s | 1s |
| 3 | 2s | 3s |
| 4 | 4s | 7s |

### 应用层
| 尝试 | 等待时间 | 累计 |
|------|---------|------|
| 1 | 0s | 0s |
| 2 | 2s | 2s |
| 3 | 4s | 6s |
| 4 | 8s | 14s |

## 🔍 日志解读

### 示例日志
```
[ContentAgent] Retrying (Retry(total=2, ...)) after connection broken by 
'ReadTimeoutError(...Read timed out. (read timeout=600)")': 
/v1/images/gemini_flash/generations
```

### 含义
- `Retry(total=2)`: 还剩2次重试机会（已重试1次）
- `ReadTimeoutError`: 读取超时
- `timeout=600`: 超时时间600秒（10分钟）
- **自动重试中**: urllib3 自动处理

## 🎯 触发条件

### HTTP 状态码
- **429**: 频率限制
- **500**: 服务器错误
- **502**: 网关错误
- **503**: 服务不可用
- **504**: 网关超时

### 网络错误
- 连接超时
- 读取超时
- 连接重置

## ⚡ 特性

- ✅ **指数退避**: 避免服务器过载
- ✅ **连接池复用**: 减少TCP握手
- ✅ **线程安全**: 多线程环境可用
- ✅ **智能重试**: 遵守服务器限制
- ✅ **详细日志**: 便于调试

## 🔧 配置调整

### 增加重试次数
```python
# utils/http_client.py
retry_strategy = Retry(
    total=5,  # 改为5次
    # ...
)
```

### 调整超时时间
```python
# banana-pro-img-jd.py
timeout=300  # 改为5分钟
```

### 环境变量
```bash
export MAX_RETRIES=5
```

## 📈 性能影响

### 正常情况
- ✅ 无影响（请求成功不重试）
- ✅ 连接池提升性能

### 失败情况
- ⚠️ 增加延迟（等待重试）
- ✅ 提高成功率

## 🎓 最佳实践

1. **合理设置超时**: 根据API响应时间调整
2. **使用指数退避**: 避免固定延迟
3. **记录重试日志**: 便于监控和调试
4. **区分错误类型**: 4xx不重试，5xx重试

## 📚 详细文档

查看 `RETRY_MECHANISM_GUIDE.md` 获取完整说明。

---

**快速参考** | **版本**: 1.0 | **更新**: 2026-01-21
