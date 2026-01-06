# 需求文档：API错误处理修复

## 简介

当前系统存在一个bug：用户在前端页面点击生成按钮后，前端显示"生成失败: 启动任务失败"，但后端实际上正在正常处理请求并生成内容。这表明前端和后端之间在错误处理和响应格式方面存在通信问题。

## 术语表

- **Flask应用（Flask Application）**：处理API请求的Python后端服务
- **前端应用（Frontend Application）**：提供用户界面的Next.js/React应用
- **API端点（API Endpoint）**：处理HTTP请求的特定URL路径
- **HTTP状态码（HTTP Status Code）**：表示HTTP请求结果的数字代码
- **JSON响应（JSON Response）**：API端点返回的结构化数据格式
- **错误处理（Error Handling）**：以一致方式捕获和响应错误的过程

## 需求

### 需求 1：统一的API响应格式

**用户故事：** 作为前端开发者，我希望所有API端点返回一致的响应格式，以便可靠地处理成功和错误情况。

#### 验收标准

1. WHEN API端点成功执行 THEN 系统 SHALL 返回HTTP状态200和`{"success": true, ...}`
2. WHEN API端点遇到业务逻辑错误 THEN 系统 SHALL 返回HTTP状态200和`{"success": false, "error": "错误信息"}`
3. WHEN API端点遇到服务器错误 THEN 系统 SHALL 返回HTTP状态500和`{"success": false, "error": "错误信息"}`
4. WHEN API端点接收到无效输入 THEN 系统 SHALL 返回HTTP状态400和`{"success": false, "error": "错误信息"}`
5. WHEN 调用`/api/start_generate`端点 THEN 系统 SHALL 无论成功或失败都返回一致的响应格式

### 需求 2：改进的错误日志记录

**用户故事：** 作为系统管理员，我希望API失败时有详细的错误日志，以便快速诊断和修复问题。

#### 验收标准

1. WHEN API端点发生异常 THEN 系统 SHALL 记录完整的堆栈跟踪
2. WHEN API请求失败 THEN 系统 SHALL 记录请求参数
3. WHEN 记录错误 THEN 系统 SHALL 包含时间戳、端点路径和错误详情
4. WHEN `/api/start_generate`发生错误 THEN 系统 SHALL 记录足够的信息以重现问题
5. WHEN 后端成功处理请求 THEN 系统 SHALL 记录成功确认信息

### 需求 3：前端错误处理

**用户故事：** 作为用户，我希望看到清晰准确的错误消息，以便了解出了什么问题以及如何修复。

#### 验收标准

1. WHEN 后端返回错误响应 THEN 前端 SHALL 显示响应中的错误消息
2. WHEN 发生网络错误 THEN 前端 SHALL 显示用户友好的网络错误消息
3. WHEN API返回HTTP 500 THEN 前端 SHALL 优雅地处理并显示适当的消息
4. WHEN API返回HTTP 400 THEN 前端 SHALL 显示验证错误消息
5. WHEN `/api/start_generate`调用失败 THEN 前端 SHALL 显示具体的错误原因

### 需求 4：请求/响应验证

**用户故事：** 作为开发者，我希望验证API请求和响应，以便尽早发现数据格式问题。

#### 验收标准

1. WHEN `/api/start_generate`端点接收请求 THEN 系统 SHALL 验证`requirement`是非空字符串
2. WHEN 创建响应 THEN 系统 SHALL 确保所有必需字段都存在
3. WHEN 前端接收响应 THEN 系统 SHALL 在处理前验证响应结构
4. WHEN 验证失败 THEN 系统 SHALL 返回清晰的验证错误消息
5. WHEN 后端返回响应 THEN 系统 SHALL 包含前端期望的所有字段

### 需求 5：调试和监控

**用户故事：** 作为开发者，我希望能够轻松调试API通信问题，以便识别问题是在前端还是后端。

#### 验收标准

1. WHEN 发起API请求 THEN 系统 SHALL 在后端记录请求详情
2. WHEN 发送API响应 THEN 系统 SHALL 记录响应状态和关键字段
3. WHEN 前端发起API调用 THEN 系统 SHALL 在浏览器控制台记录请求（开发模式）
4. WHEN 前端接收响应 THEN 系统 SHALL 在浏览器控制台记录响应（开发模式）
5. WHEN 启用调试 THEN 系统 SHALL 提供关于请求/响应周期的详细信息
