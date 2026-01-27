# RunningLogBar 日志显示改进

## 问题描述
RunningLogBar 只显示最新的一条日志，用户看不到完整的后台处理过程。

## 原因分析

### 后端行为
```python
# utils/job_manager.py
latest_log = self.logs[-1] if self.logs else None  # 只返回最后一条
```
后端每次只返回最新的一条日志。

### 前端行为
```typescript
// 之前的逻辑
if (trimmed === lastLogRef.current) return  // 跳过重复日志
lastLogRef.current = trimmed
setRunningLog(trimmed)  // 只保存一条日志
```
前端只保存和显示一条日志，且会跳过重复的日志。

## 解决方案

### 方案选择
采用**前端累积显示**方案，因为：
1. 不需要修改后端API
2. 实现简单，影响范围小
3. 可以控制显示的日志数量

### 实现细节

#### 1. ChatInterface.tsx 修改

**新增状态：**
```typescript
const [allLogs, setAllLogs] = React.useState<string[]>([])  // 存储所有日志
```

**修改日志更新逻辑：**
```typescript
const updateRunningLog = (nextLog: unknown) => {
  if (typeof nextLog !== 'string') return
  const trimmed = nextLog.trim()
  if (!trimmed) return
  if (trimmed === lastLogRef.current) return  // 跳过重复的日志
  
  lastLogRef.current = trimmed
  
  // 添加到日志列表
  setAllLogs(prev => {
    const newLogs = [...prev, trimmed]
    // 限制最多显示最近10条日志
    if (newLogs.length > 10) {
      return newLogs.slice(-10)
    }
    return newLogs
  })
  
  // 更新当前显示的日志（显示最新的）
  setRunningLog(trimmed)
}
```

**清空日志：**
```typescript
const clearRunningLog = () => {
  lastLogRef.current = ''
  setRunningLog('')
  setAllLogs([])  // 清空所有日志
}
```

#### 2. ChatInput.tsx 修改

**新增接口参数：**
```typescript
interface ChatInputProps {
  // ... 其他参数
  runningLogAllLogs?: string[]  // 新增：所有日志列表
}
```

**传递参数：**
```typescript
<RunningLogBar 
  visible={runningLogVisible && !!runningLogText} 
  text={runningLogText} 
  allLogs={runningLogAllLogs}  // 传递所有日志
/>
```

#### 3. RunningLogBar.tsx 修改

**新增接口参数：**
```typescript
interface RunningLogBarProps {
  visible: boolean
  text: string
  allLogs?: string[]  // 新增：所有日志列表
}
```

**显示逻辑：**
```typescript
// 如果有多条日志，显示所有日志；否则只显示单条
const displayLogs = allLogs.length > 0 ? allLogs : (text ? [text] : [])
const hasMultipleLogs = displayLogs.length > 1
```

**UI 渲染：**
- **单条日志**：保持原有样式（带跑马灯效果）
- **多条日志**：显示为列表，最新的日志有动画，历史日志显示静态点

## 功能特性

### 1. 日志累积显示
- 自动累积显示最近 10 条日志
- 超过 10 条时，自动移除最旧的日志

### 2. 视觉区分
- **最新日志**：紫色渐变动画点 + ping 动画
- **历史日志**：灰色静态点

### 3. 滚动支持
- 多条日志时，容器可滚动
- 最大高度 320px（max-h-80）
- 自定义滚动条样式

### 4. 响应式高度
- 单条日志：高度 48px（max-h-12）
- 多条日志：高度最大 384px（max-h-96）

### 5. 保留原有功能
- 单条日志时保留跑马灯效果
- 平滑的展开/收起动画
- 无障碍支持（aria-live）

## 使用示例

### 单条日志
```
🟣 正在分析内容...
```

### 多条日志
```
⚫ 步骤1: 开始分析内容
⚫ 步骤2: 检查合规性
⚫ 步骤3: 提取装扮信息
🟣 步骤4: 生成提示词
```

## 技术细节

### 日志去重
```typescript
if (trimmed === lastLogRef.current) return  // 跳过重复的日志
```
- 避免后端重复发送相同日志时的重复显示
- 使用 ref 存储最后一条日志，避免不必要的渲染

### 日志限制
```typescript
if (newLogs.length > 10) {
  return newLogs.slice(-10)  // 只保留最近10条
}
```
- 防止日志无限累积
- 保持 UI 性能

### 样式优化
```css
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;  /* 细滚动条 */
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);  /* 半透明 */
}
```

## 测试建议

### 1. 单条日志测试
- 提交一个简单的生成请求
- 观察是否显示单条日志
- 检查跑马灯效果是否正常

### 2. 多条日志测试
- 提交一个复杂的生成请求
- 观察是否累积显示多条日志
- 检查最新日志的动画效果

### 3. 日志限制测试
- 触发超过 10 条日志的场景
- 确认只显示最近 10 条

### 4. 清空测试
- 完成一个任务后
- 确认日志被正确清空

## 相关文件

- `frontend/src/components/ChatInterface.tsx` - 日志状态管理
- `frontend/src/components/ChatInput.tsx` - 参数传递
- `frontend/src/components/RunningLogBar.tsx` - UI 渲染
- `RUNNING_LOG_IMPROVEMENTS.md` - 本文档

## 修改日期
2025-01-19
