# AI API 迁移文档

## 迁移概述

已将系统从 OpenAI API 迁移到 JD Cloud AI API。

## 变更内容

### 1. 新增文件

- **`utils/ai_client.py`**: 新的 AI 客户端，封装 JD Cloud AI API 调用
  - `AIClient`: 核心客户端类
  - `OpenAICompatibleClient`: 兼容 OpenAI SDK 接口的包装类
  - 最小化代码修改，保持原有调用方式

### 2. 修改的文件

#### `config.py`
```python
# 旧配置（已删除）
OPENAI_API_KEY = '35f54cc4-be7a-4414-808e-f5f9f0194d4f'
OPENAI_API_BASE = 'http://gpt-proxy.jd.com/gateway/azure'

# 新配置
AI_API_URL = 'https://modelservice.jdcloud.com/v1/images/gemini_flash/generations'
AI_API_KEY = 'pk-a3b4d157-e765-45b9-988a-b8b2a6d7c8bf'
```

#### `content_agent.py`
- 移除 `from openai import OpenAI`
- 改用 `from utils.ai_client import OpenAICompatibleClient`
- 使用新的配置初始化客户端

#### `matchers/base_matcher.py`
- 移除 `from openai import OpenAI`
- 改用 `from utils.ai_client import OpenAICompatibleClient`
- 使用新的配置初始化客户端

#### `gate-合并.py`
- 移除 `from openai import OpenAI`
- 改用 `from utils.ai_client import OpenAICompatibleClient`
- 使用新的配置初始化客户端

#### `.env`
```bash
# 新增配置
AI_API_URL=https://modelservice.jdcloud.com/v1/images/gemini_flash/generations
AI_API_KEY=pk-a3b4d157-e765-45b9-988a-b8b2a6d7c8bf
```

## API 对比

### 旧 API (OpenAI)
```python
from openai import OpenAI

client = OpenAI(
    api_key="35f54cc4-be7a-4414-808e-f5f9f0194d4f",
    base_url="http://gpt-proxy.jd.com/gateway/azure"
)

response = client.chat.completions.create(
    model="gpt-4o-0806",
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.3,
    max_tokens=300
)
```

### 新 API (JD Cloud)
```python
from utils.ai_client import OpenAICompatibleClient

client = OpenAICompatibleClient(
    api_url="https://modelservice.jdcloud.com/v1/images/gemini_flash/generations",
    api_key="pk-a3b4d157-e765-45b9-988a-b8b2a6d7c8bf"
)

# 调用方式完全相同
response = client.chat.completions.create(
    model="gemini_flash",
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.3,
    max_tokens=300
)
```

## 兼容性说明

新的 `OpenAICompatibleClient` 完全兼容 OpenAI SDK 的调用方式：
- ✅ `client.chat.completions.create()` 方法
- ✅ `messages` 参数格式
- ✅ `response.choices[0].message.content` 返回格式
- ✅ 所有现有代码无需修改调用逻辑

## 配置方式

### 方式一：环境变量（推荐）
在 `.env` 文件中配置：
```bash
AI_API_URL=https://modelservice.jdcloud.com/v1/images/gemini_flash/generations
AI_API_KEY=pk-a3b4d157-e765-45b9-988a-b8b2a6d7c8bf
```

### 方式二：直接修改 config.py
```python
AI_API_URL = 'https://modelservice.jdcloud.com/v1/images/gemini_flash/generations'
AI_API_KEY = 'pk-a3b4d157-e765-45b9-988a-b8b2a6d7c8bf'
```

## 测试验证

### 1. 测试配置加载
```bash
python -c "from config import get_config; c = get_config(); print(f'URL: {c.AI_API_URL}'); print(f'Key: {c.AI_API_KEY[:20]}...')"
```

### 2. 测试 AI 客户端
```bash
python -c "from utils.ai_client import OpenAICompatibleClient; from config import get_config; c = get_config(); client = OpenAICompatibleClient(c.AI_API_URL, c.AI_API_KEY); print('客户端初始化成功')"
```

### 3. 测试完整流程
访问应用并测试内容分析功能：
```bash
curl -X POST http://localhost:28888/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"requirement": "生成一个开心的角色"}'
```

## 注意事项

1. **API 响应格式**：如果 JD Cloud API 的实际响应格式与 OpenAI 不同，需要在 `utils/ai_client.py` 的 `chat_completion()` 方法中调整解析逻辑

2. **错误处理**：新客户端已包含超时、异常处理，但建议根据实际使用情况优化

3. **模型名称**：从 `gpt-4o-0806` 改为 `gemini_flash`，如需使用其他模型，修改调用时的 `model` 参数

4. **请求头**：当前使用的请求头包含 `Trace-id`，可根据需要自定义

## 回滚方案

如需回滚到 OpenAI API：

1. 恢复 `config.py` 中的 OpenAI 配置
2. 在各文件中恢复 `from openai import OpenAI`
3. 恢复原有的客户端初始化代码
4. 删除 `utils/ai_client.py`

## 迁移完成检查清单

- [x] 创建新的 AI 客户端 (`utils/ai_client.py`)
- [x] 更新配置文件 (`config.py`)
- [x] 更新环境变量 (`.env`)
- [x] 更新 `content_agent.py`
- [x] 更新 `matchers/base_matcher.py`
- [x] 更新 `gate-合并.py`
- [x] 测试应用启动
- [ ] 测试实际 API 调用（需要真实请求验证）
- [ ] 根据实际响应格式调整解析逻辑

## 后续优化建议

1. 根据 JD Cloud API 的实际响应格式，优化 `utils/ai_client.py` 中的解析逻辑
2. 添加重试机制和更详细的错误日志
3. 考虑添加 API 调用监控和统计
4. 优化超时时间和并发控制
