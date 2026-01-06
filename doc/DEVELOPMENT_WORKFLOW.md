# 开发与部署工作流程指南

## 📋 目录
1. [开发环境设置](#开发环境设置)
2. [前端开发流程](#前端开发流程)
3. [后端开发流程](#后端开发流程)
4. [生产部署流程](#生产部署流程)
5. [常见场景](#常见场景)
6. [故障排查](#故障排查)

---

## 🔧 开发环境设置

### 初次设置

```bash
# 1. 克隆项目
git clone <repository-url>
cd joy_ip_3D_new

# 2. 安装后端依赖
pip install -r requirements.txt

# 3. 安装前端依赖
cd frontend
npm install
cd ..

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置必要的配置

# 5. 创建必要目录
mkdir -p output generated_images logs
```

---

## 🎨 前端开发流程

### 场景1: 本地开发（推荐）

**适用于**: 日常开发、调试、快速迭代

```bash
# 1. 启动后端服务（终端1）
python app_new.py

# 2. 启动前端开发服务器（终端2）
cd frontend
npm run dev:local
# 访问: http://localhost:3000
```

**特点**:
- ✅ 热重载（修改代码自动刷新）
- ✅ 无需重新编译
- ✅ 实时查看效果
- ✅ 开发者工具友好
- ⚠️ 前后端分离，需要两个终端

**修改流程**:
1. 修改 `frontend/src/` 下的任何文件
2. 保存文件
3. 浏览器自动刷新 ✨
4. 无需任何额外操作

---

### 场景2: 云服务器开发

**适用于**: 在云服务器上直接开发

```bash
# 1. 启动后端服务（终端1）
python app_new.py

# 2. 启动前端开发服务器（终端2）
cd frontend
npm run dev
# 访问: http://YOUR_SERVER_IP:4000
```

**特点**:
- ✅ 热重载
- ✅ 可从外网访问
- ⚠️ 需要开放端口 4000

---

### 场景3: 生产环境测试

**适用于**: 测试生产环境的实际效果

```bash
# 1. 构建前端
cd frontend
npm run export
cd ..

# 2. 重启后端服务
pkill -f 'python.*app_new.py'
python app_new.py
# 访问: http://YOUR_SERVER_IP:28888
```

**特点**:
- ✅ 与生产环境完全一致
- ✅ 单端口部署
- ⚠️ 每次修改都需要重新构建

---

## 🔄 前端修改的完整流程

### 步骤详解

#### 1️⃣ 修改代码
```bash
# 编辑任何前端文件，例如:
vim frontend/src/components/ChatInterface.tsx
vim frontend/src/components/DetailView.tsx
vim frontend/src/app/page.tsx
```

**常见修改类型**:
- 修改弹窗位置
- 调整按钮样式
- 添加表单验证
- 修改布局
- 更新文案

#### 2️⃣ 本地测试（开发模式）
```bash
# 如果开发服务器未运行，启动它
cd frontend
npm run dev:local

# 在浏览器中测试
# http://localhost:3000
```

#### 3️⃣ 构建生产版本
```bash
# 清理旧的构建文件（可选但推荐）
cd frontend
rm -rf .next out node_modules/.cache

# 构建并导出
npm run export

# 返回项目根目录
cd ..
```

**构建过程**:
```
✓ 编译 TypeScript
✓ 检查类型
✓ 运行 ESLint
✓ 优化代码
✓ 生成静态文件
✓ 复制到 frontend_dist/
```

#### 4️⃣ 验证构建结果
```bash
# 检查文件是否更新
ls -la frontend_dist/index.html
ls -la frontend_dist/_next/static/chunks/app/

# 应该看到最新的时间戳
```

#### 5️⃣ 重启后端服务
```bash
# 方法1: 手动重启
pkill -f 'python.*app_new.py'
python app_new.py

# 方法2: 使用后台运行
pkill -f 'python.*app_new.py'
nohup python app_new.py > logs/app.log 2>&1 &
```

#### 6️⃣ 验证部署
```bash
# 运行部署检查脚本
./check_deployment.sh

# 或手动检查
curl http://localhost:28888/api/health
```

#### 7️⃣ 清除浏览器缓存
```
用户端操作:
1. 打开网站
2. 按 Ctrl + Shift + R (硬刷新)
3. 或清除浏览器缓存
```

---

## 🐍 后端开发流程

### 修改后端代码

```bash
# 1. 修改 Python 文件
vim app_new.py
vim content_agent.py
vim generation_controller.py

# 2. 重启服务
pkill -f 'python.*app_new.py'
python app_new.py

# 3. 测试 API
python test_start_generate.py
curl http://localhost:28888/api/health
```

**注意**: 后端修改**不需要**重新构建前端！

---

## 🚀 生产部署流程

### 完整部署检查清单

```bash
# ✅ 1. 拉取最新代码
git pull origin main

# ✅ 2. 更新依赖（如果有变化）
pip install -r requirements.txt
cd frontend && npm install && cd ..

# ✅ 3. 构建前端
cd frontend
rm -rf .next out node_modules/.cache
npm run export
cd ..

# ✅ 4. 验证构建
./check_deployment.sh

# ✅ 5. 备份当前服务（可选）
# cp app_new.py app_new.py.backup

# ✅ 6. 重启服务
pkill -f 'python.*app_new.py'
python app_new.py

# ✅ 7. 验证服务
sleep 3
curl http://localhost:28888/api/health

# ✅ 8. 查看日志
tail -f logs/app_cloud.log
```

---

## 📝 常见场景

### 场景A: 修改了弹窗位置

```bash
# 1. 编辑组件
vim frontend/src/components/ChatInterface.tsx

# 2. 本地测试（开发模式）
cd frontend && npm run dev:local

# 3. 确认效果后，构建生产版本
npm run export && cd ..

# 4. 重启服务
pkill -f 'python.*app_new.py' && python app_new.py

# 5. 通知用户清除缓存
```

---

### 场景B: 修改了按钮验证逻辑

```bash
# 1. 编辑组件
vim frontend/src/components/ChatInput.tsx

# 2. 如果涉及后端验证，同时修改
vim app_new.py

# 3. 本地测试
cd frontend && npm run dev:local
# 在另一个终端: python app_new.py

# 4. 构建前端
npm run export && cd ..

# 5. 重启服务
pkill -f 'python.*app_new.py' && python app_new.py
```

---

### 场景C: 只修改了样式（CSS/Tailwind）

```bash
# 1. 编辑样式
vim frontend/src/components/ui/button.tsx
vim frontend/src/app/globals.css

# 2. 本地测试（自动热重载）
cd frontend && npm run dev:local

# 3. 构建生产版本
npm run export && cd ..

# 4. 重启服务
pkill -f 'python.*app_new.py' && python app_new.py
```

---

### 场景D: 只修改了后端逻辑

```bash
# 1. 编辑后端代码
vim app_new.py

# 2. 重启服务（无需构建前端！）
pkill -f 'python.*app_new.py'
python app_new.py

# 3. 测试 API
python test_start_generate.py
```

---

### 场景E: 修改了环境变量

```bash
# 1. 编辑 .env
vim .env

# 2. 如果修改了前端相关的环境变量（NEXT_PUBLIC_*）
cd frontend && npm run export && cd ..

# 3. 重启服务
pkill -f 'python.*app_new.py'
python app_new.py
```

---

## 🔍 故障排查

### 问题1: 前端修改没有生效

**原因**: 浏览器缓存或构建未更新

**解决方案**:
```bash
# 1. 确认构建时间
ls -la frontend_dist/index.html

# 2. 如果时间不是最新的，重新构建
cd frontend
rm -rf .next out
npm run export
cd ..

# 3. 清除浏览器缓存
# Ctrl + Shift + R
```

---

### 问题2: 构建失败

**常见错误**:
```
Error: TypeScript compilation failed
Error: ESLint errors found
```

**解决方案**:
```bash
# 1. 查看详细错误
cd frontend
npm run build

# 2. 修复 TypeScript 错误
npm run lint

# 3. 如果是依赖问题
rm -rf node_modules package-lock.json
npm install
```

---

### 问题3: 服务启动失败

**解决方案**:
```bash
# 1. 检查端口占用
netstat -tuln | grep 28888
lsof -i :28888

# 2. 杀死占用进程
pkill -f 'python.*app_new.py'

# 3. 检查日志
tail -50 logs/app_cloud.log

# 4. 重新启动
python app_new.py
```

---

## 📊 快速参考表

| 修改类型 | 需要重新构建前端 | 需要重启后端 | 需要清除缓存 |
|---------|----------------|-------------|-------------|
| 前端组件 | ✅ 是 | ✅ 是 | ✅ 是 |
| 前端样式 | ✅ 是 | ✅ 是 | ✅ 是 |
| 前端逻辑 | ✅ 是 | ✅ 是 | ✅ 是 |
| 后端 API | ❌ 否 | ✅ 是 | ❌ 否 |
| 后端逻辑 | ❌ 否 | ✅ 是 | ❌ 否 |
| 环境变量 | ⚠️ 视情况 | ✅ 是 | ❌ 否 |
| 静态资源 | ✅ 是 | ✅ 是 | ✅ 是 |

---

## 🛠️ 实用脚本

### 一键部署脚本

创建 `deploy.sh`:
```bash
#!/bin/bash
set -e

echo "🚀 开始部署..."

# 1. 构建前端
echo "📦 构建前端..."
cd frontend
rm -rf .next out node_modules/.cache
npm run export
cd ..

# 2. 验证构建
echo "✅ 验证构建..."
./check_deployment.sh

# 3. 重启服务
echo "🔄 重启服务..."
pkill -f 'python.*app_new.py' || true
sleep 2
nohup python app_new.py > logs/app.log 2>&1 &

# 4. 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 5. 健康检查
echo "🏥 健康检查..."
curl -f http://localhost:28888/api/health || {
    echo "❌ 健康检查失败！"
    exit 1
}

echo "✅ 部署完成！"
echo "📝 请通知用户清除浏览器缓存"
```

使用方法:
```bash
chmod +x deploy.sh
./deploy.sh
```

---

### 快速重启脚本

创建 `restart.sh`:
```bash
#!/bin/bash
pkill -f 'python.*app_new.py'
sleep 2
python app_new.py
```

---

## 📚 相关文档

- `USER_ACTION_GUIDE.md` - 用户清除缓存指南
- `FRONTEND_REBUILD_REPORT.md` - 前端重建报告
- `check_deployment.sh` - 部署状态检查
- `test_start_generate.py` - API 测试脚本

---

## 💡 最佳实践

### 1. 开发时使用开发模式
```bash
# 前端热重载，无需重新构建
cd frontend && npm run dev:local
```

### 2. 提交前测试生产构建
```bash
# 确保生产环境能正常构建
cd frontend && npm run export && cd ..
```

### 3. 使用版本控制
```bash
# 提交前检查
git status
git diff

# 提交时写清楚修改内容
git commit -m "feat: 调整弹窗位置到输入框上方"
```

### 4. 保持依赖更新
```bash
# 定期更新依赖
cd frontend
npm outdated
npm update
```

### 5. 监控日志
```bash
# 实时查看日志
tail -f logs/app_cloud.log

# 查看错误
grep -i error logs/app_cloud.log
```

---

## ⚠️ 重要提醒

### ❗ 前端修改必须重新构建
**任何前端文件的修改（组件、样式、逻辑、配置）都需要执行 `npm run export` 才能在生产环境生效！**

### ❗ 构建后必须重启服务
**重新构建前端后，必须重启 Flask 服务才能加载新的静态文件！**

### ❗ 用户必须清除缓存
**部署后，必须通知用户清除浏览器缓存（Ctrl+Shift+R）才能看到最新版本！**

---

## 🎯 总结

### 前端开发的黄金法则

```
修改代码 → 本地测试 → 构建生产版本 → 重启服务 → 清除缓存
   ↓           ↓            ↓              ↓           ↓
  编辑      npm run      npm run        重启       Ctrl+Shift+R
  .tsx     dev:local      export      app_new.py
```

### 记住这个流程

```bash
# 完整的前端修改流程（一行命令）
cd frontend && npm run export && cd .. && pkill -f 'python.*app_new.py' && python app_new.py
```

---

**最后更新**: 2025-12-09  
**维护者**: 开发团队
