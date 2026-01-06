# Joy IP 3D - 双环境部署快速指南

本项目支持同时在云服务器和本地环境运行，互不冲突。

## 📋 目录

- [云服务器部署](#云服务器部署)
- [本地环境设置](#本地环境设置)
- [常用命令](#常用命令)
- [故障排查](#故障排查)

---

## ☁️ 云服务器部署

### 快速部署（推荐）

```bash
# 1. SSH到云服务器
ssh username@YOUR_SERVER_IP

# 2. 克隆代码
cd /data
git clone <repository-url> joy_ip_3d_cloud
cd joy_ip_3d_cloud

# 3. 配置环境
cp .env.cloud.example .env
nano .env  # 修改 SECRET_KEY

# 4. 运行部署脚本
chmod +x scripts/deploy_cloud.sh
./scripts/deploy_cloud.sh
```

### 手动部署

```bash
# 1. 安装依赖
pip3 install -r requirements.txt
cd frontend && npm install && cd ..

# 2. 构建前端
cd frontend && npm run export && cd ..

# 3. 配置防火墙
sudo ufw allow 28888/tcp

# 4. 启动服务
python3 app_new.py
```

### 访问云服务器应用

```bash
# 获取服务器IP
curl ifconfig.me

# 浏览器访问
http://YOUR_SERVER_IP:28888
```

---

## 💻 本地环境设置

### 快速启动

**终端1 - 启动后端：**

```bash
# 1. 克隆代码到本地
git clone <repository-url> joy_ip_3d_local
cd joy_ip_3d_local

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境
cp .env.local.example .env

# 4. 启动后端
chmod +x scripts/start_local_backend.sh
./scripts/start_local_backend.sh

# 或直接运行
PORT=6001 python app_new.py
```

**终端2 - 启动前端：**

```bash
# 1. 进入项目目录
cd joy_ip_3d_local

# 2. 安装前端依赖
cd frontend
npm install

# 3. 配置前端环境
cp .env.local.example .env.local

# 4. 启动前端
npm run dev:local

# 或使用脚本
cd ..
chmod +x scripts/start_local_frontend.sh
./scripts/start_local_frontend.sh
```

### 访问本地应用

```
http://localhost:3000
```

---

## 🎯 环境对比

| 特性 | 云服务器 | 本地环境 |
|------|---------|---------|
| **用途** | 生产环境 | 开发/测试 |
| **端口** | 28888 | 前端3000 + 后端6001 |
| **模式** | 单端口（前后端整合） | 双端口（前后端分离） |
| **前端** | 静态构建 | 开发服务器（热重载） |
| **访问** | http://SERVER_IP:28888 | http://localhost:3000 |
| **配置文件** | .env.cloud → .env | .env.local → .env |
| **日志** | logs/app_cloud.log | logs/app_local.log |

---

## 📝 常用命令

### 云服务器

```bash
# 查看服务状态
sudo systemctl status joy-ip-3d

# 启动服务
sudo systemctl start joy-ip-3d

# 停止服务
sudo systemctl stop joy-ip-3d

# 重启服务
sudo systemctl restart joy-ip-3d

# 查看日志
sudo journalctl -u joy-ip-3d -f
tail -f logs/app_cloud.log

# 更新部署
git pull
pip3 install -r requirements.txt
cd frontend && npm install && npm run export && cd ..
sudo systemctl restart joy-ip-3d
```

### 本地环境

```bash
# 启动后端（终端1）
PORT=6001 python app_new.py

# 启动前端（终端2）
cd frontend && npm run dev:local

# 查看日志
tail -f logs/app_local.log

# 更新代码
git pull
pip install -r requirements.txt
cd frontend && npm install && cd ..
# 重启后端和前端
```

---

## 🔧 故障排查

### 云服务器问题

**Q: 无法从外网访问**

```bash
# 1. 检查服务是否运行
sudo systemctl status joy-ip-3d
curl http://localhost:28888/api/health

# 2. 检查防火墙
sudo ufw status | grep 28888

# 3. 检查云服务商安全组（在控制台配置）
```

**Q: 前端页面404**

```bash
# 检查前端是否构建
ls -la frontend_dist/

# 如果不存在，重新构建
cd frontend && npm run export && cd ..
sudo systemctl restart joy-ip-3d
```

### 本地环境问题

**Q: 前端无法连接后端**

```bash
# 1. 检查后端是否运行
curl http://127.0.0.1:6001/api/health

# 2. 检查前端配置
cat frontend/.env.local
# 应该有: NEXT_PUBLIC_BACKEND_ORIGIN=http://127.0.0.1:6001

# 3. 确保使用开发配置启动
cd frontend && npm run dev:local
```

**Q: 端口被占用**

```bash
# 查找占用端口的进程
lsof -i :6001  # 后端
lsof -i :3000  # 前端

# 终止进程
kill -9 <PID>
```

---

## 📂 文件结构

```
项目根目录/
├── .env.cloud.example      # 云服务器配置模板
├── .env.local.example      # 本地环境配置模板
├── .env                    # 实际配置（不提交到Git）
├── app_new.py              # Flask主应用
├── config.py               # 配置文件
├── scripts/
│   ├── deploy_cloud.sh     # 云服务器部署脚本
│   ├── start_local_backend.sh   # 本地后端启动脚本
│   └── start_local_frontend.sh  # 本地前端启动脚本
├── frontend/
│   ├── .env.local.example  # 前端本地配置模板
│   ├── .env.local          # 前端实际配置（不提交）
│   ├── next.config.js      # 生产配置（静态导出）
│   └── next.config.dev.js  # 开发配置（代理）
└── doc/
    ├── DUAL_ENVIRONMENT.md # 详细双环境指南
    ├── DEPLOYMENT.md       # 部署指南
    └── CLOUD_DEPLOYMENT.md # 云服务器部署指南
```

---

## 🔐 安全提示

1. **云服务器**：
   - ✅ 修改 `.env` 中的 `SECRET_KEY` 为强密码
   - ✅ 配置云服务商安全组，开放28888端口
   - ✅ 定期更新系统和依赖
   - ✅ 使用HTTPS（配置Nginx + SSL）

2. **本地环境**：
   - ✅ 不要将 `.env` 和 `.env.local` 提交到Git
   - ✅ 使用不同的API密钥（如果可能）
   - ✅ 本地测试数据不要上传到云端

3. **代码管理**：
   - ✅ 敏感信息使用环境变量
   - ✅ 定期备份云服务器数据
   - ✅ 使用Git管理代码版本

---

## 📚 更多文档

- [详细双环境部署指南](doc/DUAL_ENVIRONMENT.md)
- [云服务器部署指南](doc/CLOUD_DEPLOYMENT.md)
- [部署指南](doc/DEPLOYMENT.md)
- [快速入门](doc/QUICKSTART.md)
- [测试指南](TESTING.md)
- [开发指南](AGENTS.md)

---

## 🆘 获取帮助

如遇到问题：

1. 查看日志文件
2. 检查环境变量配置
3. 参考文档中的故障排查章节
4. 提交Issue并附上日志信息

---

## ✅ 快速检查清单

### 云服务器部署

- [ ] 代码已克隆到 `/data/joy_ip_3d_cloud/`
- [ ] `.env` 文件已配置（SECRET_KEY已修改）
- [ ] Python依赖已安装
- [ ] 前端依赖已安装
- [ ] 前端已构建（`frontend_dist/` 存在）
- [ ] 防火墙已开放28888端口
- [ ] 云服务商安全组已配置
- [ ] systemd服务已启动
- [ ] 可以访问 `http://SERVER_IP:28888`

### 本地环境设置

- [ ] 代码已克隆到本地
- [ ] `.env` 文件已配置
- [ ] `frontend/.env.local` 文件已配置
- [ ] Python依赖已安装
- [ ] 前端依赖已安装
- [ ] 后端在6001端口运行
- [ ] 前端在3000端口运行
- [ ] 可以访问 `http://localhost:3000`
- [ ] 前端可以调用后端API

---

**祝部署顺利！** 🚀
