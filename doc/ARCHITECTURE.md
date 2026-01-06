# 系统架构文档

## 整体架构

Joy IP 3D图片生成系统采用前后端分离的架构设计：

```
┌──────────────────────────────────────────────────────────┐
│                        用户界面                           │
│              (React + Next.js + shadcn/ui)               │
└────────────────────┬─────────────────────────────────────┘
                     │ HTTP/HTTPS
                     ▼
┌──────────────────────────────────────────────────────────┐
│                      API Gateway                         │
│                     (Flask + CORS)                       │
└────────────────────┬─────────────────────────────────────┘
                     │
      ┌──────────────┼──────────────┐
      ▼              ▼               ▼
┌─────────┐  ┌─────────────┐  ┌───────────────┐
│ Content │  │ Generation  │  │    Matcher    │
│  Agent  │  │ Controller  │  │   System      │
└─────────┘  └─────────────┘  └───────────────┘
      │              │               │
      ▼              ▼               ▼
┌──────────────────────────────────────────────────────────┐
│               Image Processing Layer                     │
│   (OpenCV, PIL, per-data.py, banana-*.py)               │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
          ┌──────────────────┐
          │   File System    │
          │ (output/, data/) │
          └──────────────────┘
```

## 核心模块

### 1. 前端层 (Frontend)

#### 技术栈
- **Next.js 14**: React框架，提供SSR和路由
- **TypeScript**: 类型安全
- **shadcn/ui**: 高质量UI组件
- **Tailwind CSS**: 实用优先的CSS框架
- **Axios**: HTTP客户端

#### 主要组件

**ChatInterface.tsx**
- 职责：主聊天界面
- 功能：
  - 消息收发
  - 预设内容选择
  - 图片展示和下载
  - 加载状态管理

**DetailView.tsx**
- 职责：图片详情页
- 功能：
  - 大图预览
  - 缩放控制
  - 分享和下载
  - 相关推荐

### 2. API层 (Backend API)

#### 技术栈
- **Flask**: 轻量级Web框架
- **Flask-CORS**: 跨域资源共享
- **OpenAI API**: AI内容分析

#### 核心端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/generate` | POST | 完整图片生成流程 |
| `/api/analyze` | POST | 仅内容分析 |
| `/api/health` | GET | 健康检查 |
| `/output/<file>` | GET | 静态文件服务 |

### 3. 业务逻辑层 (Business Logic)

#### ContentAgent
```python
content_agent.py
├── check_compliance()     # 合规检查
├── analyze_content()      # 内容分析
└── process_content()      # 完整处理流程
```

**职责**：
- 违规内容过滤
- 多维度内容分析（表情、动作、服装等）
- 调用AI进行智能分析

**流程**：
```
用户输入 → 关键词检测 → AI深度分析 → 返回分析结果
```

#### GenerationController
```python
generation_controller.py
├── generate_step1_images()  # 基础图片生成
├── process_clothes()        # 服装处理
├── process_hands()          # 手拿物品处理
├── process_hats()           # 头戴物品处理
└── generate_complete_flow() # 完整流程控制
```

**职责**：
- 协调多阶段图片生成
- 质量检查和重试机制
- 错误处理和恢复

**流程**：
```
Step 1-3: 基础图片 (head + body)
    ↓
Step 4-5: 添加服装 → Gate检查 → 重试（如失败）
    ↓
Step 6-7: 添加手拿 → Gate检查 → 重试（如失败）
    ↓
Step 8-9: 添加头戴 → Gate检查 → 重试（如失败）
    ↓
返回最终图片
```

#### Matcher System
```
matchers/
├── base_matcher.py   # 基础匹配器
├── head_matcher.py   # 头像/表情匹配
└── body_matcher.py   # 身体/动作匹配
```

**BaseMatcher**：
- OpenAI API集成
- 特征分析基础功能
- 分数计算逻辑

**HeadMatcher**：
- 五维度表情分析：眼睛形状、嘴型、表情、脸部动态、情感强度
- 从文件夹或Excel匹配头像
- 返回最佳匹配结果

**BodyMatcher**：
- 五维度动作分析：手部姿势、腿部姿势、整体姿势、姿势意义、情感偏向
- 动作类型分类：站姿、欢快、坐姿、跳跃、跑动
- 从指定文件夹选择身体图片

### 4. 图片处理层 (Image Processing)

#### ImageProcessor
```python
image_processor.py
├── select_body_images()     # 选择身体图片
├── select_head_images()     # 选择头像图片
├── combine_images()         # 组合图片
└── process_user_requirement() # 处理用户需求
```

**动作类型映射**：
```python
{
    "站姿": "data/body_stand",
    "欢快": "data/body_happy",
    "坐姿": "data/body_sit",
    "跳跃": "data/body_jump",
    "跑动": "data/body_run"
}
```

#### per-data.py
高级图片合成逻辑：
1. 识别body图中红色区域角度
2. 反向旋转使红色区域水平
3. 对齐face图到红色区域中心
4. 组合图片
5. 恢复原始角度
6. 裁剪并居中到2000x2000画布
7. 生成1024x1200白色背景版本

#### banana-*.py
配饰生成模块：
- **banana-clothes.py**: 添加服装
- **banana-hands.py**: 添加手拿物品
- **banana-hats.py**: 添加头戴物品

每个模块都调用AI图片生成API，prompt格式：
```
保持角色[动作/表情/姿态]不变，添加[配饰描述]
```

## 数据流

### 完整生成流程

```
1. 用户输入
   "创建一个开心站立的角色，穿着红色衣服，戴着帽子"
   │
   ▼
2. 合规检查 (ContentAgent)
   检查关键词 → AI深度分析 → 通过
   │
   ▼
3. 内容分析 (ContentAgent)
   {
     表情: "开心",
     动作: "站姿",
     服装: "红色衣服",
     手拿: "",
     头戴: "帽子",
     背景: ""
   }
   │
   ▼
4. 匹配资源 (Matcher + ImageProcessor)
   HeadMatcher → 选2张最佳头像
   BodyMatcher → 选2张最佳身体
   │
   ▼
5. 基础组合 (per-data.py)
   2头像 × 2身体 = 4张基础图
   │
   ▼
6. 添加服装 (banana-clothes.py)
   每张图 → AI生成 → Gate检查 → (重试) → 4张图
   │
   ▼
7. 添加头戴 (banana-hats.py)
   每张图 → AI生成 → Gate检查 → (重试) → 4张图
   │
   ▼
8. 返回结果
   ["/output/img1.png", "/output/img2.png", ...]
```

## 文件结构

```
joy_ip_3D_new/
├── backend/                     # 后端代码
│   ├── app_new.py              # 主应用
│   ├── content_agent.py        # 内容Agent
│   ├── generation_controller.py # 生成控制器
│   ├── image_processor.py      # 图片处理器
│   ├── per-data.py            # 图片合成
│   ├── banana-clothes.py      # 服装生成
│   ├── banana-hands.py        # 手拿生成
│   ├── banana-hats.py         # 头戴生成
│   └── matchers/              # 匹配器
│       ├── base_matcher.py
│       ├── head_matcher.py
│       └── body_matcher.py
│
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── app/              # Next.js页面
│   │   ├── components/       # React组件
│   │   └── lib/              # 工具函数
│   ├── package.json
│   └── next.config.js
│
├── data/                       # 数据文件
│   ├── body_stand/           # 站姿身体图
│   ├── body_happy/           # 欢快身体图
│   ├── body_sit/             # 坐姿身体图
│   ├── body_jump/            # 跳跃身体图
│   ├── body_run/             # 跑动身体图
│   ├── face_front_per/       # 正面头像
│   └── face_left_turn_per/   # 侧面头像
│
├── output/                     # 生成输出
└── generated_images/          # 临时图片
```

## 扩展性设计

### 添加新的配饰类型

1. 创建新的处理模块：`banana-{type}.py`
2. 在`GenerationController`中添加处理方法
3. 在`ContentAgent`中添加分析维度

### 添加新的动作类型

1. 在`data/`下创建新文件夹
2. 更新`ImageProcessor`的映射配置
3. 更新`BodyMatcher`的分类逻辑

### 添加新的AI服务提供商

1. 创建新的API适配器
2. 在配置中添加选项
3. 更新调用逻辑以支持多提供商

## 性能考虑

### 瓶颈点
1. **AI API调用**：每次生成需要多次调用
2. **图片处理**：OpenCV操作耗时
3. **文件I/O**：大量图片读写

### 优化方案
1. **缓存机制**：对相同输入缓存结果
2. **异步处理**：使用任务队列（Celery）
3. **CDN**：静态资源使用CDN
4. **负载均衡**：多实例部署

## 安全考虑

### 输入验证
- 内容合规检查
- 文件大小限制
- 请求频率限制

### 数据安全
- 敏感信息使用环境变量
- API密钥加密存储
- 用户数据隔离

### 访问控制
- CORS配置
- API认证（可选）
- 文件访问权限

## 监控指标

### 业务指标
- 生成请求数
- 成功率
- 平均生成时间
- 重试次数

### 技术指标
- API响应时间
- 错误率
- 内存使用
- CPU使用
- 磁盘空间

## 未来规划

1. **用户系统**：添加用户账号和历史记录
2. **批量生成**：支持一次生成多个角色
3. **风格迁移**：支持更多艺术风格
4. **实时预览**：WebSocket实时推送生成进度
5. **社区功能**：用户分享和作品展示
6. **API开放**：提供公开API供第三方调用

