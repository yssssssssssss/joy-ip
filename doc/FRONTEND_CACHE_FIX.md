# 前端缓存问题修复指南

## 问题描述

前端页面显示"生成失败：启动任务失败"，但后端任务实际在正常执行。

## 根本原因

浏览器缓存了旧版本的前端代码，旧代码调用的是错误的 API 端点 `/api/start-generate`（带连字符），而后端实际端点是 `/api/start_generate`（带下划线）。

## 已完成的修复

1. ✅ 修改了 `frontend/src/components/ChatInterface.tsx`，将 API 调用从 `/api/start-generate` 改为 `/api/start_generate`
2. ✅ 重新构建了前端：`npm run export`
3. ✅ 重启了后端应用

## 解决方案

### 方案 1：清除浏览器缓存（推荐）

#### Chrome/Edge
1. 按 `Ctrl + Shift + Delete`（Windows）或 `Cmd + Shift + Delete`（Mac）
2. 选择"缓存的图片和文件"
3. 时间范围选择"全部时间"
4. 点击"清除数据"
5. 刷新页面（`Ctrl + F5` 或 `Cmd + Shift + R`）

#### 或者使用硬刷新
- Windows: `Ctrl + F5` 或 `Ctrl + Shift + R`
- Mac: `Cmd + Shift + R`

### 方案 2：使用隐私/无痕模式测试

1. 打开新的隐私/无痕窗口
2. 访问应用 URL
3. 测试生成功能

### 方案 3：使用测试页面验证 API

访问测试页面验证 API 是否正常工作：
```
http://YOUR_SERVER_URL:28888/test_api.html
```

这个页面会直接测试 API 端点，不受前端缓存影响。

### 方案 4：添加版本号强制刷新（开发用）

如果问题持续存在，可以在前端添加版本号参数：

```bash
# 在 frontend 目录
cd frontend

# 修改 package.json 中的版本号
# 然后重新构建
npm run export

# 重启后端
pkill -f "python app_new.py"
python app_new.py
```

## 验证修复

### 1. 检查浏览器开发者工具

1. 打开浏览器开发者工具（F12）
2. 切换到 Network（网络）标签
3. 清除网络日志
4. 在前端页面输入文本并点击生成
5. 查看网络请求：
   - ✅ 应该看到 `POST /api/start_generate`（带下划线）
   - ❌ 如果看到 `POST /api/start-generate`（带连字符），说明还在使用旧缓存

### 2. 检查响应

正确的响应应该是：
```json
{
  "success": true,
  "job_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

错误的响应（404）：
```json
{
  "error": "Not Found"
}
```

### 3. 使用 curl 测试后端

```bash
# 测试健康检查
curl http://localhost:28888/api/health

# 测试启动生成
curl -X POST http://localhost:28888/api/start_generate \
  -H "Content-Type: application/json" \
  -d '{"requirement": "测试生成"}'

# 应该返回：
# {"job_id":"...","success":true}
```

## 当前系统状态

- ✅ 后端运行正常（进程 ID: 16）
- ✅ API 端点正确：`/api/start_generate`
- ✅ 前端已重新构建，包含正确的 API 调用
- ⚠️ 浏览器可能缓存了旧版本

## 技术细节

### API 端点对比

| 旧版本（错误） | 新版本（正确） |
|--------------|--------------|
| `/api/start-generate` | `/api/start_generate` |
| 带连字符 | 带下划线 |
| 404 错误 | 200 成功 |

### 文件修改记录

1. `frontend/src/components/ChatInterface.tsx` - 第 192 行
   - 旧：`axios.post('/api/start-generate', ...)`
   - 新：`axios.post('/api/start_generate', ...)`

2. `frontend/src/lib/api.ts` - 第 40 行
   - 已经是正确的：`apiRequest('/api/start_generate', ...)`

### 构建输出位置

- 源代码：`frontend/src/`
- 构建输出：`frontend_dist/`
- 后端静态文件目录：`frontend_dist/`（由 Flask 提供服务）

## 预防措施

为避免将来出现类似问题：

1. **统一命名规范**：所有 API 端点使用下划线（snake_case）
2. **添加 API 测试**：在 CI/CD 中添加端点测试
3. **版本控制**：在前端添加版本号，便于识别缓存问题
4. **文档同步**：确保前后端 API 文档一致

## 联系支持

如果清除缓存后问题仍然存在：

1. 检查浏览器控制台是否有错误
2. 检查网络请求是否正确
3. 使用 `test_api.html` 页面测试
4. 查看后端日志：`tail -f logs/app_cloud.log`（如果配置了日志文件）

## 快速命令参考

```bash
# 重新构建前端
cd frontend && npm run export && cd ..

# 重启后端
pkill -f "python app_new.py"
python app_new.py

# 测试 API
curl -X POST http://localhost:28888/api/start_generate \
  -H "Content-Type: application/json" \
  -d '{"requirement": "测试"}'

# 查看运行进程
ps aux | grep "python app_new.py"

# 查看端口占用
lsof -i :28888
```
