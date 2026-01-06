# 3D编辑器工作流程指南

## 📋 完整交互流程

### 步骤1: 打开3D编辑器
用户点击 **"3D场景"** 按钮

**效果**:
- 弹窗在屏幕中央显示
- 带半透明黑色遮罩背景
- 弹窗尺寸: 90vw × 80vh（最大1200px宽）

---

### 步骤2: 在3D编辑器中操作
用户在3D编辑器中：
1. 选择3D模型
2. 调整角度、位置、光照等
3. 预览效果

**状态**:
- 弹窗保持打开
- 用户可以自由操作

---

### 步骤3: 确认渲染
用户点击3D编辑器中的 **"确认渲染"** 或 **"保存"** 按钮

**后台处理**:
1. 3D编辑器生成高质量渲染图
2. 发送 `postMessage` 到父窗口
3. 消息类型: `three-editor-hq-saved`
4. 包含渲染图片的路径和预览URL

**前端响应**:
1. 接收到消息
2. 保存渲染结果到状态
   - `renderFilePath`: 图片文件路径
   - `renderPreviewUrl`: 预览URL
3. **自动关闭3D编辑器弹窗** ✨

---

### 步骤4: 输入描述文本
弹窗关闭后，用户在输入框中输入描述

**示例**:
```
我想生成一个微笑的站姿角色，穿着红色上衣，拿着气球 ip形象
```

**状态**:
- 渲染的3D图片已保存在后台
- 输入框正常可用
- 可以看到渲染预览（如果配置显示）

---

### 步骤5: 开始生成
用户点击 **发送按钮**（紫蓝渐变色）

**处理逻辑**:
```typescript
// 检查是否有渲染的3D图片
if (renderFilePath) {
  // 使用3D渲染图片进行生成
  const runRes = await axios.post('/api/run-3d-banana', {
    imagePath: renderFilePath,
    promptText: text
  })
} else {
  // 正常的生成流程
  const startRes = await axios.post('/api/start_generate', {
    requirement: text
  })
}
```

**后端API**:
- 接口: `/api/run-3d-banana`
- 参数:
  - `imagePath`: 渲染图片路径
  - `promptText`: 用户输入的描述文本
- 返回: 生成的图片URL

---

### 步骤6: 查看结果
生成完成后显示结果图片

**效果**:
- 基于3D渲染图生成的最终图片
- 结合了用户的描述文本
- 显示在聊天界面中

---

## 🎯 关键特性

### 1. 自动关闭弹窗
- ✅ 用户确认渲染后自动关闭
- ✅ 无需手动点击"关闭"按钮
- ✅ 流程更加顺畅

### 2. 状态保持
- ✅ 渲染结果保存在组件状态中
- ✅ 弹窗关闭后数据不丢失
- ✅ 可以随时使用渲染图片

### 3. 智能路由
- ✅ 有渲染图片时使用3D生成API
- ✅ 无渲染图片时使用普通生成API
- ✅ 自动选择最佳处理方式

### 4. 预览显示（可选）
- ✅ 可以显示渲染预览图
- ✅ 用户知道当前使用的是哪张图
- ✅ 提供视觉反馈

---

## 💡 用户体验优化

### 优化前的流程
```
1. 点击"3D场景"
2. 在编辑器中操作
3. 点击"确认渲染"
4. 手动点击"关闭"按钮 ❌
5. 输入描述文本
6. 点击发送
```

### 优化后的流程
```
1. 点击"3D场景"
2. 在编辑器中操作
3. 点击"确认渲染"
4. 弹窗自动关闭 ✅
5. 输入描述文本
6. 点击发送
```

**减少步骤**: 从6步减少到5步  
**减少点击**: 减少1次手动关闭操作  
**体验提升**: 更符合用户预期

---

## 🔧 技术实现

### 消息通信
```typescript
// 3D编辑器发送消息
window.parent.postMessage({
  type: 'three-editor-hq-saved',
  filePath: '/output/render_123456.png',
  previewUrl: '/output/render_123456.png',
  url: '/output/render_123456.png'
}, '*')
```

### 前端接收处理
```typescript
useEffect(() => {
  const onMessage = (e: MessageEvent) => {
    const data = e.data
    if (data.type === 'three-editor-hq-saved') {
      // 保存渲染结果
      setRenderFilePath(data.filePath || null)
      setRenderPreviewUrl(data.previewUrl || data.url || null)
      // 自动关闭弹窗
      setThreeModalOpen(false)
    }
  }
  window.addEventListener('message', onMessage)
  return () => window.removeEventListener('message', onMessage)
}, [])
```

### 生成逻辑
```typescript
const handleSend = async (overrideText?: string) => {
  const text = (overrideText ?? input).trim()
  
  // 检查是否有3D渲染图片
  if (renderFilePath) {
    // 使用3D渲染图片生成
    const runRes = await axios.post('/api/run-3d-banana', {
      imagePath: renderFilePath,
      promptText: text
    })
    
    if (runRes.data?.success && runRes.data?.url) {
      // 显示生成结果
      const assistantMessage: Message = {
        type: 'assistant',
        content: '已根据渲染图生成结果',
        images: [runRes.data.url]
      }
      setMessages(prev => [...prev, assistantMessage])
    }
  } else {
    // 正常生成流程
    // ...
  }
}
```

---

## 🎨 UI状态管理

### 状态变量
```typescript
const [threeModalOpen, setThreeModalOpen] = useState(false)
const [renderFilePath, setRenderFilePath] = useState<string | null>(null)
const [renderPreviewUrl, setRenderPreviewUrl] = useState<string | null>(null)
```

### 状态流转
```
初始状态:
  threeModalOpen: false
  renderFilePath: null
  renderPreviewUrl: null

点击"3D场景":
  threeModalOpen: true

确认渲染:
  renderFilePath: '/output/render_123.png'
  renderPreviewUrl: '/output/render_123.png'
  threeModalOpen: false (自动关闭)

点击发送:
  使用 renderFilePath 进行生成
```

---

## 📱 响应式设计

### 弹窗尺寸
```css
width: 90vw;           /* 视口宽度的90% */
max-width: 1200px;     /* 最大1200px */
height: 80vh;          /* 视口高度的80% */
```

### 不同屏幕适配
- **桌面**: 1200px × 80vh
- **平板**: 90vw × 80vh
- **手机**: 90vw × 80vh

---

## 🔍 调试和测试

### 测试步骤
1. 打开浏览器开发者工具（F12）
2. 切换到 Console 标签
3. 点击"3D场景"按钮
4. 在3D编辑器中操作
5. 点击"确认渲染"
6. 观察控制台消息
7. 确认弹窗自动关闭
8. 输入文本并发送
9. 查看生成结果

### 验证点
- ✅ 弹窗在屏幕中央显示
- ✅ 确认渲染后弹窗自动关闭
- ✅ 渲染结果正确保存
- ✅ 发送时使用正确的API
- ✅ 生成结果正确显示

---

## 🆘 常见问题

### Q1: 弹窗没有自动关闭？
**可能原因**:
- 3D编辑器没有发送正确的消息
- 消息类型不匹配
- 前端代码未更新

**解决方案**:
1. 检查浏览器控制台是否有错误
2. 确认前端代码已更新（清除缓存）
3. 检查3D编辑器的消息格式

---

### Q2: 渲染图片没有保存？
**可能原因**:
- 消息中缺少 `filePath` 字段
- 后端保存失败

**解决方案**:
1. 检查控制台消息内容
2. 查看后端日志
3. 确认 `/api/save-render` 接口正常

---

### Q3: 生成时没有使用渲染图片？
**可能原因**:
- `renderFilePath` 状态为空
- 条件判断逻辑错误

**解决方案**:
1. 在发送前检查 `renderFilePath` 的值
2. 添加调试日志
3. 确认状态正确保存

---

## 📚 相关文档

- **`UI_CHANGES_SUMMARY.md`** - UI修改总结
- **`DEVELOPMENT_WORKFLOW.md`** - 开发流程指南
- **`QUICK_REFERENCE.md`** - 快速参考

---

## 🎯 未来优化方向

### 1. 添加渲染预览显示
在输入框上方显示当前使用的渲染图片

### 2. 支持多次渲染
允许用户渲染多张图片并选择使用哪一张

### 3. 添加渲染历史
保存最近的渲染记录，方便重复使用

### 4. 优化加载状态
在渲染过程中显示进度条或加载动画

### 5. 添加快捷键
- ESC: 关闭弹窗
- Enter: 确认渲染

---

**最后更新**: 2025-12-09 11:35  
**状态**: ✅ 已实现并部署
