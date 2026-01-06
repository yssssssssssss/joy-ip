# Joy IP 3D 图片生成系统

基于AI的3D角色图片生成系统，具有智能内容分析、合规检查和多阶段图片生成功能。

## 功能特性

### 1. AI聊天界面
- 基于shadcn/ui的现代化聊天界面
- 支持预设内容快速插入（表情、动作、风格）
- 实时生成反馈
- 图片hover下载功能

### 2. 智能内容分析
- **合规检查**：屏蔽违规关键词和内容
- **多维度分析**：
  - 表情：调用head_matcher分析
  - 动作：调用body_matcher分析
  - 服装、手拿、头戴、背景：AI智能提取

### 3. 多阶段图片生成
- **步骤1-3**：基础图片生成（头像+身体组合）
- **步骤4-5**：添加服装（带质量检查和重试）
- **步骤6-7**：添加手拿物品（带质量检查和重试）
- **步骤8-9**：添加头戴物品（带质量检查和重试）
- **步骤10**：展示最终图片，支持下载

### 4. 图片详情页
- 大图预览，支持缩放
- 显示生成参数
- 支持分享和下载
- 相关图片推荐

## 技术栈

### 后端
- **Flask**: Web框架
- **OpenAI API**: 内容分析和合规检查
- **OpenCV**: 图片处理
- **自定义Matcher**: 表情和动作匹配

### 前端
- **Next.js 14**: React框架
- **TypeScript**: 类型安全
- **shadcn/ui**: UI组件库
- **Tailwind CSS**: 样式框架
- **Lucide React**: 图标库

## 项目结构

```
joy_ip_3D_new/
├── backend/
│   ├── app_new.py                 # 主应用入口
│   ├── content_agent.py           # 内容分析Agent
│   ├── generation_controller.py   # 生成流程控制器
│   ├── image_processor.py         # 图片处理器
│   ├── per-data.py               # 图片合成逻辑
│   ├── banana-clothes.py         # 服装生成
│   ├── banana-hands.py           # 手拿物品生成
│   ├── banana-hats.py            # 头戴物品生成
│   └── matchers/
│       ├── base_matcher.py       # 基础匹配器
│       ├── head_matcher.py       # 头像匹配器
│       └── body_matcher.py       # 身体匹配器
│
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx
    │   │   ├── page.tsx          # 主页（聊天界面）
    │   │   ├── detail/
    │   │   │   └── page.tsx      # 详情页
    │   │   └── globals.css
    │   ├── components/
    │   │   ├── ChatInterface.tsx # 聊天界面组件
    │   │   ├── DetailView.tsx    # 详情页组件
    │   │   └── ui/               # shadcn/ui组件
    │   └── lib/
    │       └── utils.ts
    ├── package.json
    ├── tsconfig.json
    ├── tailwind.config.ts
    └── next.config.js
```

## 安装和启动

### 后端安装

```bash
# 安装Python依赖
pip install flask flask-cors openai opencv-python numpy pandas pillow requests

# 启动后端服务
python app_new.py
```

后端将在 `http://localhost:6001` 启动

### 前端安装

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将在 `http://localhost:3000` 启动

## API文档

### POST /api/generate
生成图片

**请求体**:
```json
{
  "requirement": "创建一个开心站立的角色，穿着红色衣服，戴着帽子"
}
```

**响应**:
```json
{
  "success": true,
  "images": ["/output/image1.png", "/output/image2.png"],
  "analysis": {
    "表情": "开心",
    "动作": "站姿",
    "服装": "红色衣服",
    "手拿": "",
    "头戴": "帽子",
    "背景": ""
  },
  "total": 2
}
```

### POST /api/analyze
仅分析内容，不生成图片

**请求体**:
```json
{
  "requirement": "创建一个角色"
}
```

**响应**:
```json
{
  "success": true,
  "compliant": true,
  "analysis": {
    "表情": "...",
    "动作": "...",
    "服装": "...",
    "手拿": "...",
    "头戴": "...",
    "背景": "..."
  }
}
```

### GET /api/health
健康检查

**响应**:
```json
{
  "status": "healthy",
  "service": "Joy IP 3D Generation System"
}
```

## 使用流程

1. **输入描述**：在聊天界面输入角色描述，或使用预设按钮快速插入内容
2. **内容分析**：系统自动进行合规检查和多维度内容分析
3. **图片生成**：
   - 匹配最佳的头像和身体姿势
   - 生成基础组合图片
   - 依次添加服装、手拿、头戴配饰
   - 每步都进行质量检查，失败自动重试
4. **查看结果**：在聊天界面查看生成的图片
5. **下载或查看详情**：
   - Hover图片显示下载按钮
   - 点击图片进入详情页查看大图

## 预设内容

### 表情
- 大笑
- 微笑
- 陶醉
- 眨眼

### 动作
- 站姿
- 坐姿
- 跳跃
- 跑动
- 动态

### 风格
- 人像摄影
- 电影写真
- 中国风
- 动漫
- 3D渲染
- 赛博朋克

## 合规规则

系统会自动屏蔽以下内容：
- 指定违规词：跪着、抽烟、女装、裸、生肉、logo
- 通用违规内容：暴力、血腥、色情、赌博、毒品等

## 注意事项

1. 确保已安装所有依赖包
2. 后端需要OpenAI API访问权限
3. 图片生成需要一定时间，请耐心等待
4. 生成的图片保存在`output`目录

## 开发者

本系统由AI助手开发，基于用户需求定制。

## License

MIT License

