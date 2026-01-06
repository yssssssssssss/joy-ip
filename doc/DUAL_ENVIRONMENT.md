# 双环境部署指南

本文档说明如何同时在云服务器和本地环境运行项目，避免冲突。

## 架构概述

- **云服务器**：生产环境，单端口模式（28888），前后端整合
- **本地环境**：开发/测试环境，双端口模式（前端3000，后端6001），支持热重载

## 方案：使用环境变量区分

通过环境变量 `DEPLOYMENT_ENV` 来区分云端和本地环境。

---

## 云服务器部署步骤

### 1. 连接到云服务器

```bash
ssh username@YOUR_SERVER_IP
```

### 2. 克隆或更新代码

```bash
# 首次部署
cd /data
git clone <repository-url> joy_ip_3d_cloud
cd joy_ip_3d_cloud

# 或更新代码
cd /data/joy_ip_3d_cloud
git pull
```

### 3. 安装依赖

```bash
# Python依赖
pip3 install -r requirements.txt

# 前端依赖
cd frontend
npm install
cd ..
```

### 4. 配置云服务器环境变量

创建 `.env.cloud` 文件：

```bash
cat > .env.cloud << 'EOF'
# ============================================
# 云服务器生产环境配置
# ============================================

# 环境标识
DEPLOYMENT_ENV=cloud

# 服务器配置
PORT=28888
HOST=0.0.0.0

# 前端构建目录
FRONTEND_BUILD_DIR=frontend_dist

# 安全配置
SECRET_KEY=your-cloud-secret-key-change-this

# OpenAI API配置
OPENAI_API_KEY=your-openai-api-key
OPENAI_API_BASE=http://gpt-proxy.jd.com/gateway/azure

# 脚本执行配置
SCRIPT_TIMEOUT=120

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app_cloud.log
EOF
```

复制为 `.env`：

```bash
cp .env.cloud .env
```

**重要：编辑 `.env` 文件，修改 `SECRET_KEY` 为强密码！**

```bash
nano .env
# 修改 SECRET_KEY=your-cloud-secret-key-change-this
```

### 5. 构建前端

```bash
cd frontend
npm run build
npm run export
cd ..
```

验证构建：

```bash
ls -la frontend_dist/
# 应该看到 index.html 和 _next/ 目录
```

### 6. 配置防火墙

```bash
# 开放28888端口
sudo ufw allow 28888/tcp
sudo ufw status
```

**同时配置云服务商安全组**（阿里云/腾讯云/AWS控制台）：
- 协议：TCP
- 端口：28888
- 源：0.0.0.0/0

### 7. 启动应用

**方式1：直接启动（测试用）**

```bash
python3 app_new.py
```

**方式2：使用systemd（推荐）**

创建服务文件：

```bash
sudo tee /etc/systemd/system/joy-ip-3d.service > /dev/null << 'EOF'
[Unit]
Description=Joy IP 3D Generation System (Cloud)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/data/joy_ip_3d_cloud
Environment="PATH=/usr/bin:/usr/local/bin"
EnvironmentFile=/data/joy_ip_3d_cloud/.env
ExecStart=/usr/bin/python3 app_new.py
Restart=always
RestartSec=10
StandardOutput=append:/data/joy_ip_3d_cloud/logs/systemd.log
StandardError=append:/data/joy_ip_3d_cloud/logs/systemd_error.log

[Install]
WantedBy=multi-user.target
EOF
```

启动服务：

```bash
# 创建日志目录
mkdir -p logs

# 重新加载systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start joy-ip-3d

# 设置开机自启
sudo systemctl enable joy-ip-3d

# 查看状态
sudo systemctl status joy-ip-3d

# 查看日志
sudo journalctl -u joy-ip-3d -f
```

### 8. 验证部署

```bash
# 获取服务器IP
SERVER_IP=$(curl -s ifconfig.me)
echo "云服务器访问地址: http://$SERVER_IP:28888"

# 本地测试
curl http://localhost:28888/api/health

# 远程测试（从本地电脑执行）
curl http://YOUR_SERVER_IP:28888/api/health
```

在浏览器访问：`http://YOUR_SERVER_IP:28888`

---

## 本地环境部署步骤

### 1. 克隆代码到本地

```bash
# 在本地电脑上
cd ~/projects
git clone <repository-url> joy_ip_3d_local
cd joy_ip_3d_local
```

### 2. 安装依赖

```bash
# Python依赖
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
cd ..
```

### 3. 配置本地环境变量

创建 `.env.local` 文件：

```bash
cat > .env.local << 'EOF'
# ============================================
# 本地开发/测试环境配置
# ============================================

# 环境标识
DEPLOYMENT_ENV=local

# 服务器配置（后端）
PORT=6001
HOST=127.0.0.1

# 前端构建目录（本地测试时可选）
FRONTEND_BUILD_DIR=frontend_dist

# 安全配置
SECRET_KEY=local-dev-secret-key

# OpenAI API配置
OPENAI_API_KEY=your-openai-api-key
OPENAI_API_BASE=http://gpt-proxy.jd.com/gateway/azure

# 脚本执行配置
SCRIPT_TIMEOUT=120

# 日志配置
LOG_LEVEL=DEBUG
LOG_FILE=logs/app_local.log
EOF
```

复制为 `.env`：

```bash
cp .env.local .env
```

### 4. 启动本地后端

```bash
# 方式1：直接启动
python app_new.py

# 方式2：使用环境变量
PORT=6001 python app_new.py
```

后端将在 `http://127.0.0.1:6001` 运行。

### 5. 启动本地前端（开发模式）

**创建本地前端开发配置：**

在 `frontend/` 目录创建 `.env.local` 文件：

```bash
cd frontend
cat > .env.local << 'EOF'
# 本地开发环境配置
NEXT_PUBLIC_BACKEND_ORIGIN=http://127.0.0.1:6001
EOF
```

**临时修改 `next.config.js` 添加开发模式支持：**

```bash
# 备份原配置
cp next.config.js next.config.js.backup

# 创建开发配置
cat > next.config.dev.js << 'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // 开发模式：启用代理
  async rewrites() {
    const backendOrigin = process.env.NEXT_PUBLIC_BACKEND_ORIGIN || 'http://127.0.0.1:6001'
    return [
      {
        source: '/api/:path*',
        destination: `${backendOrigin}/api/:path*`,
      },
      {
        source: '/output/:path*',
        destination: `${backendOrigin}/output/:path*`,
      },
      {
        source: '/generated_images/:path*',
        destination: `${backendOrigin}/generated_images/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
EOF
```

**启动前端开发服务器：**

```bash
# 使用开发配置启动
NEXT_CONFIG_FILE=next.config.dev.js npm run dev

# 或者直接启动（如果已修改package.json）
npm run dev
```

前端将在 `http://localhost:3000` 运行。

### 6. 访问本地应用

在浏览器访问：`http://localhost:3000`

---

## 环境隔离策略

### 1. 目录隔离

```
云服务器：/data/joy_ip_3d_cloud/
本地环境：~/projects/joy_ip_3d_local/
```

### 2. 端口隔离

| 环境 | 后端端口 | 前端端口 | 访问方式 |
|------|---------|---------|---------|
| 云服务器 | 28888 | - | http://YOUR_SERVER_IP:28888 |
| 本地环境 | 6001 | 3000 | http://localhost:3000 |

### 3. 配置文件隔离

| 环境 | 配置文件 | 日志文件 |
|------|---------|---------|
| 云服务器 | `.env.cloud` → `.env` | `logs/app_cloud.log` |
| 本地环境 | `.env.local` → `.env` | `logs/app_local.log` |

### 4. Git忽略配置

确保 `.gitignore` 包含：

```gitignore
# 环境配置
.env
.env.local
.env.cloud
.env.*.local

# 日志
logs/

# 构建产物
frontend_dist/
frontend/.next/
frontend/out/

# 依赖
node_modules/
__pycache__/

# 生成的图片
generated_images/
output/
```

---

## 代码同步策略

### 方案1：使用Git分支

```bash
# 云服务器使用main分支
git checkout main
git pull origin main

# 本地使用dev分支
git checkout dev
git pull origin dev
```

### 方案2：使用相同代码，不同配置

```bash
# 两边都使用main分支
git checkout main
git pull origin main

# 但使用不同的.env配置文件
# 云端：.env.cloud
# 本地：.env.local
```

**推荐方案2**，代码保持一致，只通过环境变量区分。

---

## 更新流程

### 云服务器更新

```bash
# SSH到云服务器
ssh username@YOUR_SERVER_IP

# 进入项目目录
cd /data/joy_ip_3d_cloud

# 拉取最新代码
git pull

# 更新依赖
pip3 install -r requirements.txt
cd frontend && npm install && cd ..

# 重新构建前端
cd frontend && npm run export && cd ..

# 重启服务
sudo systemctl restart joy-ip-3d

# 查看状态
sudo systemctl status joy-ip-3d
```

### 本地环境更新

```bash
# 进入本地项目目录
cd ~/projects/joy_ip_3d_local

# 拉取最新代码
git pull

# 更新依赖
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 重启后端（Ctrl+C停止，然后重新启动）
python app_new.py

# 前端会自动热重载
```

---

## 常见问题

### Q1: 本地前端无法连接后端

**A:** 检查：

1. 后端是否在6001端口运行：
```bash
curl http://127.0.0.1:6001/api/health
```

2. 前端环境变量是否正确：
```bash
cat frontend/.env.local
# 应该有 NEXT_PUBLIC_BACKEND_ORIGIN=http://127.0.0.1:6001
```

3. 前端代理配置是否正确（使用 `next.config.dev.js`）

### Q2: 云服务器无法访问

**A:** 检查：

1. 服务是否运行：
```bash
sudo systemctl status joy-ip-3d
curl http://localhost:28888/api/health
```

2. 防火墙是否开放：
```bash
sudo ufw status | grep 28888
```

3. 云服务商安全组是否配置

### Q3: 两个环境的数据会冲突吗？

**A:** 不会，因为：

1. 运行在不同的机器上
2. 使用不同的目录
3. 生成的图片保存在各自的 `generated_images/` 和 `output/` 目录

### Q4: 如何在本地测试云端配置？

**A:** 可以在本地构建前端并测试单端口模式：

```bash
# 在本地
cd frontend
npm run export
cd ..

# 使用28888端口启动（避免与云端冲突，可以用其他端口）
PORT=28889 python app_new.py

# 访问
curl http://localhost:28889/api/health
```

### Q5: 本地开发时需要构建前端吗？

**A:** 不需要。本地开发使用前端开发服务器（`npm run dev`），支持热重载，无需构建。

---

## 快速命令参考

### 云服务器

```bash
# 启动
sudo systemctl start joy-ip-3d

# 停止
sudo systemctl stop joy-ip-3d

# 重启
sudo systemctl restart joy-ip-3d

# 查看状态
sudo systemctl status joy-ip-3d

# 查看日志
sudo journalctl -u joy-ip-3d -f
tail -f logs/app_cloud.log
```

### 本地环境

```bash
# 启动后端
python app_new.py

# 启动前端（新终端）
cd frontend && npm run dev

# 查看日志
tail -f logs/app_local.log
```

---

## 安全建议

1. **云服务器**：
   - 使用强密码的 `SECRET_KEY`
   - 定期更新系统和依赖
   - 配置防火墙和安全组
   - 使用HTTPS（配置Nginx + SSL）

2. **本地环境**：
   - 不要将本地 `.env` 提交到Git
   - 使用不同的API密钥（如果可能）
   - 本地测试数据不要上传到云端

3. **代码管理**：
   - 敏感信息使用环境变量
   - `.env` 文件加入 `.gitignore`
   - 定期备份云服务器数据

---

## 总结

通过这个方案，你可以：

✅ 在云服务器上运行生产环境（28888端口，单端口模式）
✅ 在本地运行开发环境（前端3000，后端6001，双端口模式）
✅ 两个环境完全隔离，互不影响
✅ 代码通过Git同步，配置通过环境变量区分
✅ 本地支持热重载，云端稳定运行

如有问题，请参考 `doc/DEPLOYMENT.md` 和 `doc/CLOUD_DEPLOYMENT.md`。
