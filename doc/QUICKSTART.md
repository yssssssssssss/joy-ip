# 快速入门指南

本指南帮助你快速在云服务器上部署 Joy IP 3D 图片生成系统。

## 目录

- [云服务器部署](#云服务器部署)
- [基本使用](#基本使用)
- [常见问题](#常见问题)

## 云服务器部署

### 1. 克隆项目

```bash
git clone <repository-url>
cd joy_ip_3d
```

### 2. 安装依赖

**后端依赖：**
```bash
pip install -r requirements.txt
```

**前端依赖：**
```bash
cd frontend
npm install
cd ..
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少设置以下变量：

```bash
PORT=28888
SECRET_KEY=your-secret-key-here
```

### 4. 构建前端

```bash
cd frontend
npm run build
npm run export
cd ..
```

### 5. 配置防火墙（必需）

```bash
# 开放28888端口
sudo ufw allow 28888/tcp

# 查看服务器公网IP
curl ifconfig.me
```

**云服务器还需要配置安全组：**
- 登录云服务商控制台（阿里云、腾讯云、AWS等）
- 在安全组中添加入站规则：TCP 端口 28888

### 6. 启动应用

```bash
python app_new.py
```

### 7. 访问应用

**获取服务器IP：**
```bash
curl ifconfig.me
```

**从浏览器访问：**
- 应用首页：`http://YOUR_SERVER_IP:28888`（将YOUR_SERVER_IP替换为实际IP）
- API健康检查：`http://YOUR_SERVER_IP:28888/api/health`

**在服务器上测试：**
```bash
curl http://localhost:28888/api/health
```

## 基本使用

### 1. 生成图片

1. 在聊天界面输入需求描述，例如：
   ```
   生成一个微笑的香蕉，穿着红色衣服，手拿气球
   ```

2. 点击发送或按Enter键

3. 等待系统生成图片

4. 查看生成的结果

### 2. 使用预设

系统提供了快捷预设：

- **表情**：大笑、微笑、陶醉、眨眼
- **动作**：站姿、坐姿、跳跃、跑动、动态
- **配饰**：帽子、眼镜、围巾等

点击预设按钮快速添加到输入框。

### 3. 查看详情

点击生成的图片可以查看详情页面，支持：

- 下载图片
- 添加背景
- 优化形象
- 角度变换

### 4. 3D编辑器

访问 `/joyai` 路径使用3D编辑器：

1. 调整香蕉的姿态和角度
2. 点击"渲染"生成预览
3. 输入需求描述
4. 生成最终图片

## 环境变量说明

```bash
# 服务器端口（固定28888）
PORT=28888

# 服务器主机地址
HOST=0.0.0.0

# 前端构建目录
FRONTEND_BUILD_DIR=frontend_dist

# 安全密钥（必须修改）
SECRET_KEY=your-secret-key-here

# 脚本执行超时时间（秒）
SCRIPT_TIMEOUT=120

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# OpenAI API配置
OPENAI_API_KEY=your-openai-api-key
OPENAI_API_BASE=http://gpt-proxy.jd.com/gateway/azure
```

## 目录结构

```
joy_ip_3d/
├── app_new.py              # Flask主应用
├── config.py               # 配置文件
├── requirements.txt        # Python依赖
├── .env.example           # 环境变量示例
├── utils/                 # 工具模块
│   ├── script_executor.py # 脚本执行器
│   ├── image_uploader.py  # 图片上传器
│   └── remote_downloader.py # 文件下载器
├── frontend/              # 前端应用
│   ├── src/
│   │   ├── app/          # Next.js页面
│   │   ├── components/   # React组件
│   │   └── lib/          # 工具库
│   ├── package.json
│   └── next.config.js
├── data/                  # 数据文件
├── output/                # 输出目录
├── generated_images/      # 生成的图片
└── doc/                   # 文档
```

## API端点

### 核心API

- `POST /api/start_generate` - 启动生成任务（异步）
- `GET /api/job/<id>/status` - 查询任务状态
- `POST /api/generate` - 同步生成图片
- `POST /api/analyze` - 分析内容
- `GET /api/health` - 健康检查

### 图像处理API

- `POST /api/run-banana` - 添加背景（banana-background）
- `POST /api/run-jimeng4` - 添加背景（即梦API）
- `POST /api/run-3d-banana` - 3D渲染处理
- `POST /api/run-banana-pro-img-jd` - 优化形象
- `POST /api/run-turn` - 角度变换
- `POST /api/upload-image` - 上传图片到图床
- `POST /api/save-render` - 保存渲染图片

## 常见问题

### Q: 前端构建失败

**A:** 确保Node.js版本 >= 18，然后：

```bash
cd frontend
rm -rf node_modules .next
npm install
npm run build
```

### Q: 端口被占用

**A:** 检查并终止占用端口的进程：

```bash
# 查找占用端口的进程
sudo lsof -i :28888

# 终止进程
sudo kill -9 <PID>
```

### Q: 图片生成失败

**A:** 检查以下几点：

1. 确保Python脚本存在（如`banana-background.py`）
2. 检查日志文件：`tail -f logs/app.log`
3. 验证API密钥配置正确
4. 确保有足够的磁盘空间

### Q: 无法从外网访问

**A:** 检查：

1. 防火墙是否开放28888端口
2. 云服务商安全组是否配置正确
3. 应用是否正常运行：`curl http://localhost:28888/api/health`

### Q: 如何查看日志

**A:** 

```bash
# 实时查看日志
tail -f logs/app.log

# 查看最近100行
tail -n 100 logs/app.log

# 搜索错误
grep ERROR logs/app.log
```

### Q: 如何更新应用

**A:** 

```bash
# 拉取最新代码
git pull

# 更新后端依赖
pip install -r requirements.txt

# 更新前端依赖
cd frontend && npm install && cd ..

# 重新构建前端
cd frontend && npm run export && cd ..

# 重启应用
# 如果使用systemd
sudo systemctl restart joy-ip-3d

# 如果直接运行
# 先停止当前进程，然后重新启动
python app_new.py
```

## 性能优化建议

### 1. 使用Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:28888 --timeout 120 app_new:app
```

### 2. 启用日志文件

```bash
export LOG_FILE=logs/app.log
```

### 3. 调整超时时间

```bash
export SCRIPT_TIMEOUT=300  # 5分钟
```

### 4. 使用Nginx反向代理

参见 [DEPLOYMENT.md](DEPLOYMENT.md#使用nginx反向代理)

## 下一步

- 查看 [云服务器部署指南](CLOUD_DEPLOYMENT.md) 了解详细部署步骤
- 查看 [部署指南](DEPLOYMENT.md) 了解高级配置
- 查看 [开发指南](AGENTS.md) 了解开发规范

## 获取帮助

如遇到问题：

1. 查看日志文件
2. 检查环境变量配置
3. 验证依赖安装完整
4. 查阅文档
5. 提交Issue
