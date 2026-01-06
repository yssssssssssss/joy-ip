# 安装与测试指南

本指南将帮助你从零开始安装和测试Joy IP 3D图片生成系统。

## 前置检查

### 检查Python版本
```bash
python --version
# 应该显示: Python 3.8.x 或更高版本
```

如果没有Python或版本过低，请从[python.org](https://www.python.org/downloads/)下载安装。

### 检查Node.js版本
```bash
node --version
# 应该显示: v18.x.x 或更高版本

npm --version
# 应该显示: 9.x.x 或更高版本
```

如果没有Node.js，请从[nodejs.org](https://nodejs.org/)下载安装。

## 安装步骤

### 步骤1: 下载/克隆项目

```bash
# 如果使用git
git clone <repository-url>
cd joy_ip_3D_new

# 或者直接解压下载的ZIP文件
cd joy_ip_3D_new
```

### 步骤2: 安装Python依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

如果遇到安装错误，尝试：
```bash
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir
```

### 步骤3: 安装前端依赖

```bash
cd frontend
npm install
```

如果速度很慢，可以使用淘宝镜像：
```bash
npm config set registry https://registry.npmmirror.com
npm install
```

如果遇到错误，尝试清除缓存：
```bash
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

## 准备数据（可选）

### 创建测试数据目录

```bash
# 返回项目根目录
cd ..

# 创建数据目录
mkdir -p data/body_stand
mkdir -p data/body_happy
mkdir -p data/body_sit
mkdir -p data/body_jump
mkdir -p data/body_run
mkdir -p data/face_front_per
mkdir -p data/face_left_turn_per
```

### 添加测试图片

将你的图片文件复制到相应目录：
- `data/body_stand/` - 放置站姿身体图片
- `data/body_happy/` - 放置欢快身体图片
- `data/body_sit/` - 放置坐姿身体图片
- `data/body_jump/` - 放置跳跃身体图片
- `data/body_run/` - 放置跑动身体图片
- `data/face_front_per/` - 放置正面头像图片
- `data/face_left_turn_per/` - 放置侧面头像图片

**注意**: 如果暂时没有图片，系统仍可启动，但生成功能可能无法正常工作。

## 启动系统

### 方式一: 使用启动脚本（Windows）

#### 启动后端
1. 双击 `start_backend.bat`
2. 等待显示 "Running on http://0.0.0.0:6001"

#### 启动前端
1. 双击 `start_frontend.bat`
2. 等待显示 "Ready in xxms"
3. 系统会自动打开浏览器

### 方式二: 命令行启动

#### 终端1 - 启动后端
```bash
# 确保在项目根目录
python app_new.py
```

看到以下信息表示启动成功：
```
============================================================
启动 Joy IP 3D 图片生成系统...
============================================================
后端服务地址: http://0.0.0.0:6001
...
* Running on http://0.0.0.0:6001
```

#### 终端2 - 启动前端
```bash
cd frontend
npm run dev
```

看到以下信息表示启动成功：
```
- ready started server on 0.0.0.0:3000
- Local:        http://localhost:3000
```

## 访问系统

打开浏览器访问：
```
http://localhost:3000
```

你应该看到聊天界面。

## 基础测试

### 测试1: 健康检查

```bash
curl http://localhost:6001/api/health
```

预期响应：
```json
{
  "status": "healthy",
  "service": "Joy IP 3D Generation System"
}
```

### 测试2: 内容分析

```bash
curl -X POST http://localhost:6001/api/analyze \
  -H "Content-Type: application/json" \
  -d "{\"requirement\": \"创建一个开心站立的角色\"}"
```

预期响应：
```json
{
  "success": true,
  "compliant": true,
  "analysis": {
    "表情": "...",
    "动作": "...",
    ...
  }
}
```

### 测试3: 违规内容检测

```bash
curl -X POST http://localhost:6001/api/analyze \
  -H "Content-Type: application/json" \
  -d "{\"requirement\": \"创建一个跪着的角色\"}"
```

预期响应：
```json
{
  "success": false,
  "compliant": false,
  "reason": "包含违规关键词: 跪着"
}
```

### 测试4: 前端功能测试

1. **测试预设按钮**
   - 点击"表情"按钮
   - 选择"微笑"
   - 检查输入框是否显示"微笑"

2. **测试消息发送**
   - 在输入框输入："测试消息"
   - 点击发送按钮
   - 检查消息是否显示在聊天区域

3. **测试图片生成（需要数据）**
   - 输入："创建一个开心站立的角色"
   - 点击发送
   - 等待生成结果
   - 检查是否显示图片

4. **测试图片下载**
   - 鼠标悬停在生成的图片上
   - 检查是否显示下载按钮
   - 点击下载按钮
   - 检查图片是否下载

5. **测试详情页**
   - 点击生成的图片
   - 检查是否跳转到详情页
   - 测试缩放功能
   - 测试下载功能

## 常见问题排查

### 问题1: 后端启动失败

**错误**: `ModuleNotFoundError: No module named 'flask'`

**解决**:
```bash
pip install -r requirements.txt
```

---

**错误**: `Address already in use`

**解决**: 端口6001被占用，关闭占用进程或修改端口：
```python
# 编辑 app_new.py 最后一行
app.run(debug=True, host='0.0.0.0', port=6002)  # 改为其他端口
```

---

### 问题2: 前端启动失败

**错误**: `Error: Cannot find module ...`

**解决**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

**错误**: `Port 3000 is already in use`

**解决**:
```bash
npm run dev -- -p 3001  # 使用其他端口
```

---

### 问题3: API请求失败

**错误**: 前端显示 "错误: Network Error"

**检查**:
1. 后端是否正常运行
2. 检查浏览器控制台（F12）的Network选项卡
3. 检查`frontend/next.config.js`的代理配置

**解决**:
```javascript
// frontend/next.config.js
async rewrites() {
  return [
    {
      source: '/api/:path*',
      destination: 'http://localhost:6001/api/:path*',
    },
  ]
}
```

---

### 问题4: 图片无法生成

**可能原因**:
1. 数据目录为空
2. OpenAI API配置错误
3. 网络连接问题

**检查**:
```bash
# 检查数据目录
ls data/body_stand/
ls data/face_front_per/

# 检查后端日志
# 查看终端输出的错误信息
```

---

### 问题5: 图片无法显示

**检查**:
1. 图片是否成功生成（检查`output`目录）
2. 浏览器控制台是否有404错误
3. 后端静态文件服务是否正常

**测试**:
```bash
# 直接访问静态文件
http://localhost:6001/output/test.png
```

---

## 性能测试

### 测试并发请求

```bash
# 安装工具
pip install locust

# 创建测试文件 locustfile.py
```

```python
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def analyze(self):
        self.client.post("/api/analyze", json={
            "requirement": "创建一个开心的角色"
        })
```

```bash
# 运行测试
locust -f locustfile.py
# 访问 http://localhost:8089 配置测试
```

### 测试响应时间

```bash
# 使用curl测试
time curl -X POST http://localhost:6001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"requirement": "创建一个开心的角色"}'
```

## 日志检查

### 查看后端日志

后端日志直接输出到终端。关键日志包括：
- 请求信息
- 步骤进度
- 错误堆栈

### 查看前端日志

1. 打开浏览器开发者工具（F12）
2. 切换到Console选项卡
3. 查看JavaScript错误和日志

### 查看Network请求

1. 打开浏览器开发者工具（F12）
2. 切换到Network选项卡
3. 查看API请求和响应

## 调试模式

### 启用Python调试

```python
# app_new.py
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=6001)
```

### 启用前端调试

```bash
# 前端默认已启用开发模式
npm run dev
```

在浏览器中使用React DevTools查看组件状态。

## 测试清单

完成以下测试以确保系统正常：

- [ ] 后端成功启动
- [ ] 前端成功启动
- [ ] 健康检查API正常
- [ ] 内容分析API正常
- [ ] 违规检测正常工作
- [ ] 预设按钮功能正常
- [ ] 消息发送功能正常
- [ ] 图片生成功能正常（需要数据）
- [ ] 图片hover下载正常
- [ ] 详情页跳转正常
- [ ] 详情页缩放功能正常
- [ ] 详情页下载功能正常

## 下一步

完成安装和测试后：

1. **准备生产数据**: 添加完整的头像和身体图片
2. **实现Gate检查**: 完善gate-*.py的检查逻辑
3. **性能优化**: 根据测试结果优化性能
4. **生产部署**: 参考`DEPLOYMENT.md`进行生产部署

## 获取帮助

如果遇到问题：

1. 查看`README.md` - 功能说明
2. 查看`QUICKSTART.md` - 快速开始
3. 查看`ARCHITECTURE.md` - 技术架构
4. 查看`DEPLOYMENT.md` - 部署指南
5. 查看`CHECKLIST.md` - 实现清单

---

**最后更新**: 2025年11月7日
**测试环境**: Windows 10, Python 3.10, Node.js 18

