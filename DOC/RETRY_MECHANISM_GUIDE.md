# 重连机制完整说明文档

## 概述

项目中实现了**多层重连机制**，确保在网络不稳定或服务器临时故障时能够自动恢复。

## 重连机制架构

```
┌─────────────────────────────────────────────────────────┐
│                    应用层重试                              │
│  banana-pro-img-jd.py: 3次重试 + 指数退避                 │
│  generation_controller.py: 1次重试                        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  HTTP 客户端层重试                         │
│  utils/http_client.py: 3次重试 + 连接池复用               │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   urllib3 层重试                          │
│  Retry Strategy: 自动处理 429/500/502/503/504            │
└─────────────────────────────────────────────────────────┘
```

## 第一层：HTTP 客户端层重试

### 文件位置
`utils/http_client.py`

### 配置详情

#### 重试策略
```python
retry_strategy = Retry(
    total=3,                    # 总共重试 3 次
    backoff_factor=1.0,         # 退避因子：1秒, 2秒, 4秒
    status_forcelist=[429, 500, 502, 503, 504],  # 触发重试的状态码
    allowed_methods=["GET", "POST"],              # 允许重试的方法
    respect_retry_after_header=True               # 遵守 Retry-After 头
)
```

#### 连接池配置
```python
adapter = HTTPAdapter(
    max_retries=retry_strategy,
    pool_connections=10,        # 连接池大小
    pool_maxsize=20            # 最大连接数
)
```

### 重试时间计算

| 重试次数 | 等待时间 | 累计时间 |
|---------|---------|---------|
| 第1次 | 1秒 | 1秒 |
| 第2次 | 2秒 | 3秒 |
| 第3次 | 4秒 | 7秒 |

**公式**: `wait_time = backoff_factor * (2 ** (retry_number - 1))`

### 触发条件

#### 1. HTTP 状态码
- **429**: Too Many Requests（频率限制）
- **500**: Internal Server Error（服务器内部错误）
- **502**: Bad Gateway（网关错误）
- **503**: Service Unavailable（服务不可用）
- **504**: Gateway Timeout（网关超时）

#### 2. 网络错误
- 连接超时
- 读取超时
- 连接重置

### 特性

#### 1. 连接池复用
```python
pool_connections=10   # 保持10个连接
pool_maxsize=20      # 最多20个连接
```

**优势**:
- 减少 TCP 握手开销
- 提高请求速度
- 降低服务器负载

#### 2. 线程安全
```python
_session_lock = threading.Lock()

with _session_lock:
    if _http_session is None:
        _http_session = _create_session()
```

**优势**:
- 多线程环境下安全
- 避免重复创建 Session

#### 3. 尊重服务器限制
```python
respect_retry_after_header=True
```

**优势**:
- 遵守服务器返回的 `Retry-After` 头
- 避免过度请求
- 更友好的重试策略

## 第二层：应用层重试

### 文件位置
`banana-pro-img-jd.py`

### 配置详情

```python
max_retries = 3          # 最大重试次数
retry_delay = 2          # 初始重试延迟（秒）
```

### 重试逻辑

```python
for attempt in range(max_retries):
    try:
        # 发送请求
        response = http_post(URL, json=payload, headers=headers, timeout=600)
        
        # 处理 429 频率限制
        if response.status_code == 429:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # 指数退避
                print(f"遇到频率限制(429)，等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
        
        # 处理成功响应
        # ...
        
    except requests.exceptions.RequestException as req_err:
        # 处理请求异常
        if attempt < max_retries - 1:
            wait_time = retry_delay * (2 ** attempt)
            print(f"等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)
        else:
            return None
```

### 重试时间计算

| 重试次数 | 等待时间 | 累计时间 |
|---------|---------|---------|
| 第1次 | 2秒 | 2秒 |
| 第2次 | 4秒 | 6秒 |
| 第3次 | 8秒 | 14秒 |

**公式**: `wait_time = retry_delay * (2 ** attempt)`

### 触发条件

#### 1. HTTP 429 错误
```python
if response.status_code == 429:
    # 指数退避重试
```

#### 2. 请求异常
```python
except requests.exceptions.RequestException:
    # 网络错误、超时等
```

## 第三层：控制器层重试

### 文件位置
- `generation_controller.py`
- `generation_controller_2d.py`

### 配置详情

```python
self.max_retries = 1  # 最大重试次数
```

### 使用场景
控制器层的重试主要用于：
- 图片生成失败后的重试
- 质量检查失败后的重试

## 配置文件

### 文件位置
`config.py`

### 配置项

```python
# 图片生成配置
MAX_RETRIES: int = int(os.environ.get('MAX_RETRIES', 3))
```

### 环境变量
```bash
# 设置最大重试次数
export MAX_RETRIES=5
```

## 实际案例分析

### 案例：日志中的重试

```
[ContentAgent] Retrying (Retry(total=2, connect=None, read=None, redirect=None, status=None)) 
after connection broken by 'ReadTimeoutError("HTTPSConnectionPool(host='modelservice.jdcloud.com', 
port=443): Read timed out. (read timeout=600)")': /v1/images/gemini_flash/generations
```

#### 解析

1. **Retry(total=2)**: 还剩 2 次重试机会（已重试 1 次）
2. **ReadTimeoutError**: 读取超时错误
3. **timeout=600**: 超时时间为 600 秒（10 分钟）
4. **自动重试**: urllib3 自动触发重试

#### 重试流程

```
第1次请求 → 超时（600秒）
    ↓
等待 1 秒
    ↓
第2次请求 → 超时（600秒）
    ↓
等待 2 秒
    ↓
第3次请求 → 超时（600秒）
    ↓
等待 4 秒
    ↓
第4次请求（最后一次）
```

## 重试机制总结

### 总重试次数

| 层级 | 重试次数 | 总请求次数 |
|------|---------|-----------|
| HTTP 客户端层 | 3次 | 4次（1次原始 + 3次重试）|
| 应用层 | 3次 | 4次（1次原始 + 3次重试）|
| 控制器层 | 1次 | 2次（1次原始 + 1次重试）|

### 最坏情况

如果所有层级都触发重试：
```
总请求次数 = 4 (HTTP层) × 4 (应用层) × 2 (控制器层) = 32 次
```

**实际情况**: 通常只有一层会触发重试，因为：
- HTTP 层重试成功后，应用层不会重试
- 应用层重试成功后，控制器层不会重试

### 总等待时间

#### HTTP 客户端层
```
1秒 + 2秒 + 4秒 = 7秒
```

#### 应用层
```
2秒 + 4秒 + 8秒 = 14秒
```

#### 总计（最坏情况）
```
7秒 (HTTP层) + 14秒 (应用层) = 21秒
```

## 优化建议

### 当前配置评估

| 指标 | 当前值 | 评估 |
|------|--------|------|
| HTTP 层重试次数 | 3次 | ✅ 合理 |
| 应用层重试次数 | 3次 | ✅ 合理 |
| 退避策略 | 指数退避 | ✅ 最佳实践 |
| 超时时间 | 600秒 | ⚠️ 较长 |
| 连接池大小 | 10-20 | ✅ 合理 |

### 优化方案

#### 1. 调整超时时间（可选）
```python
# 当前
timeout=600  # 10分钟

# 建议（如果服务器响应快）
timeout=300  # 5分钟
```

#### 2. 增加重试次数（可选）
```python
# 当前
total=3

# 建议（如果网络不稳定）
total=5
```

#### 3. 调整退避因子（可选）
```python
# 当前
backoff_factor=1.0  # 1s, 2s, 4s

# 建议（更激进）
backoff_factor=0.5  # 0.5s, 1s, 2s

# 建议（更保守）
backoff_factor=2.0  # 2s, 4s, 8s
```

## 监控和调试

### 1. 查看重试日志
```python
import logging

# 启用 urllib3 详细日志
logging.getLogger('urllib3').setLevel(logging.DEBUG)

# 启用 requests 详细日志
logging.getLogger('requests').setLevel(logging.DEBUG)
```

### 2. 统计重试次数
```python
# 在 http_client.py 中添加
retry_count = 0

def http_post(...):
    global retry_count
    retry_count += 1
    # ...
```

### 3. 监控超时情况
```python
import time

start = time.time()
try:
    response = http_post(...)
except Exception as e:
    elapsed = time.time() - start
    logger.error(f"请求失败，耗时: {elapsed:.2f}秒, 错误: {e}")
```

## 常见问题

### Q1: 为什么还是会超时？
**A**: 
- 超时时间设置为 600 秒（10 分钟）
- 如果服务器响应时间超过 10 分钟，仍会超时
- 重试机制只能在超时后重新尝试，不能避免超时

### Q2: 重试会增加服务器负载吗？
**A**:
- 会，但影响可控
- 使用指数退避策略减少冲击
- 遵守服务器的 `Retry-After` 头

### Q3: 如何禁用重试？
**A**:
```python
# 方法1: 设置重试次数为 0
retry_strategy = Retry(total=0)

# 方法2: 直接使用 requests（不使用 http_client）
response = requests.post(url, ...)
```

### Q4: 如何增加重试次数？
**A**:
```python
# 修改 utils/http_client.py
retry_strategy = Retry(
    total=5,  # 改为 5 次
    # ...
)
```

### Q5: 重试会影响性能吗？
**A**:
- 正常情况下不会（请求成功不重试）
- 失败时会增加延迟（等待时间）
- 但提高了成功率

## 最佳实践

### 1. 合理设置超时时间
```python
# 快速 API
timeout=30  # 30秒

# 图片生成 API
timeout=300  # 5分钟

# 大模型 API
timeout=600  # 10分钟
```

### 2. 使用指数退避
```python
# ✅ 推荐
backoff_factor=1.0  # 1s, 2s, 4s

# ❌ 不推荐（固定延迟）
time.sleep(5)  # 每次都等5秒
```

### 3. 记录重试日志
```python
logger.info(f"重试第 {attempt} 次，等待 {wait_time} 秒")
```

### 4. 区分可重试和不可重试错误
```python
# 可重试：网络错误、超时、5xx 错误
if response.status_code >= 500:
    retry()

# 不可重试：4xx 错误（除了 429）
if 400 <= response.status_code < 500 and response.status_code != 429:
    raise Exception("客户端错误，不重试")
```

## 相关文件

### 核心文件
- ✅ `utils/http_client.py` - HTTP 客户端层重试
- ✅ `banana-pro-img-jd.py` - 应用层重试
- ✅ `generation_controller.py` - 控制器层重试
- ✅ `generation_controller_2d.py` - 2D 控制器层重试
- ✅ `config.py` - 配置文件

### 依赖库
- `requests` - HTTP 库
- `urllib3` - 底层 HTTP 库
- `urllib3.util.retry` - 重试策略

## 总结

项目实现了**三层重连机制**：

1. **HTTP 客户端层**: 自动处理网络错误和服务器错误
2. **应用层**: 处理业务逻辑错误和特殊状态码
3. **控制器层**: 处理生成失败的重试

**特点**:
- ✅ 指数退避策略
- ✅ 连接池复用
- ✅ 线程安全
- ✅ 遵守服务器限制
- ✅ 详细的日志记录

**效果**:
- 提高请求成功率
- 减少网络波动影响
- 自动恢复临时故障
- 优化用户体验

---

**文档版本**: 1.0  
**更新时间**: 2026-01-21  
**维护人员**: Kiro AI Assistant
