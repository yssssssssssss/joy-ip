# 部署总结 - 云端与本地双环境方案

## 🎯 方案概述

本项目现在支持**云服务器生产环境**和**本地开发环境**同时运行，互不冲突。

---

## 📊 环境对比表

| 项目 | 云服务器（生产） | 本地环境（开发） |
|------|----------------|----------------|
| **目录** | `/data/joy_ip_3d_cloud/` | `~/projects/joy_ip_3d_local/` |
| **端口** | 28888 | 前端3000 + 后端6001 |
| **模式** | 单端口（整合） | 双端口（分离） |
| **前端** | 静态构建 | 开发服务器 |
| **配置** | `.env.cloud` → `.env` | `.env.local` → `.env` |
| **日志** | `logs/app_cloud.log` | `logs/app_local.log` |
| **访问** | `http://SERVER_IP:28888` | `http://localhost:3000` |
| **热重载** | ❌ | ✅ |
| **构建前端** | ✅ 必需 | ❌ 不需要 |

---

## 🚀 云服务器部署（3步）

### 方式1：自动部署（推荐）

```bash
# 1. SSH到云服务器
ssh username@YOUR_SERVER_IP

# 2. 克隆并配置
cd /data
git clone <repository-url> joy_ip_3d_cloud
cd joy_ip_3d_cloud
cp .env.cloud.example .env
nano .env  # 修改SECRET_KEY

# 3. 运行部署脚本
./scripts/deploy_cloud.sh
```

### 方式2：手动部署

```bash
# 安装依赖
pip3 install -r requirements.txt
cd frontend && npm install && cd ..

# 构建前端
cd frontend && npm run export && cd ..

# 配置防火墙
sudo ufw allow 28888/tcp

# 启动服务
python3 app_new.py
```

### 访问

```bash
# 获取IP
curl ifconfig.me

# 浏览器访问
http://YOUR_SERVER_IP:28888
```

---

## 💻 本地环境设置（2步）

### 终端1：后端

```bash
# 1. 克隆并配置
git clone <repository-url> joy_ip_3d_local
cd joy_ip_3d_local
pip install -r requirements.txt
cp .env.local.example .env

# 2. 启动后端
./scripts/start_local_backend.sh
# 或
PORT=6001 python app_new.py
```

### 终端2：前端

```bash
# 1. 安装并配置
cd joy_ip_3d_local/frontend
npm install
cp .env.local.example .env.local

# 2. 启动前端
npm run dev:local
# 或
cd .. && ./scripts/start_local_frontend.sh
```

### 访问

```
http://localhost:3000
```

---

## 📁 关键文件说明

### 配置文件

| 文件 | 用途 | 位置 |
|------|------|------|
| `.env.cloud.example` | 云服务器配置模板 | 项目根目录 |
| `.env.local.example` | 本地后端配置模板 | 项目根目录 |
| `frontend/.env.local.example` | 本地前端配置模板 | frontend目录 |
| `.env` | 实际配置（不提交Git） | 项目根目录 |
| `frontend/.env.local` | 前端实际配置（不提交Git） | frontend目录 |

### 前端配置

| 文件 | 用途 |
|------|------|
| `next.config.js` | 生产配置（静态导出） |
| `next.config.dev.js` | 开发配置（代理到后端） |

### 脚本文件

| 脚本 | 用途 |
|------|------|
| `scripts/deploy_cloud.sh` | 云服务器一键部署 |
| `scripts/start_local_backend.sh` | 启动本地后端 |
| `scripts/start_local_frontend.sh` | 启动本地前端 |

---

## 🔄 工作流程

### 日常开发（本地）

```bash
# 1. 拉取最新代码
git pull

# 2. 启动后端（终端1）
PORT=6001 python app_new.py

# 3. 启动前端（终端2）
cd frontend && npm run dev:local

# 4. 开发和测试
# 访问 http://localhost:3000

# 5. 提交代码
git add .
git commit -m "feat: 新功能"
git push
```

### 部署到云端

```bash
# 1. SSH到云服务器
ssh username@YOUR_SERVER_IP

# 2. 更新代码
cd /data/joy_ip_3d_cloud
git pull

# 3. 更新依赖（如果有变化）
pip3 install -r requirements.txt
cd frontend && npm install && cd ..

# 4. 重新构建前端
cd frontend && npm run export && cd ..

# 5. 重启服务
sudo systemctl restart joy-ip-3d

# 6. 验证
curl http://localhost:28888/api/health
```

---

## ⚠️ 重要注意事项

### 云服务器

1. ✅ **必须修改SECRET_KEY**：`.env` 中的 `SECRET_KEY` 必须改为强密码
2. ✅ **配置安全组**：在云服务商控制台开放28888端口
3. ✅ **构建前端**：必须运行 `npm run export` 构建前端
4. ✅ **使用systemd**：推荐使用systemd管理服务，支持自动重启

### 本地环境

1. ✅ **双端口模式**：前端3000，后端6001，不要混淆
2. ✅ **前端配置**：确保 `frontend/.env.local` 配置了后端地址
3. ✅ **使用开发配置**：前端使用 `npm run dev:local` 启动
4. ✅ **不需要构建**：本地开发不需要构建前端，直接热重载

### 避免冲突

1. ✅ **不同目录**：云端和本地使用不同的目录名
2. ✅ **不同端口**：云端28888，本地3000+6001
3. ✅ **不同配置**：使用不同的 `.env` 文件
4. ✅ **不同日志**：使用不同的日志文件名

---

## 🐛 常见问题

### Q1: 云服务器无法访问

**检查清单：**
```bash
# 1. 服务是否运行
sudo systemctl status joy-ip-3d

# 2. 本地能否访问
curl http://localhost:28888/api/health

# 3. 防火墙是否开放
sudo ufw status | grep 28888

# 4. 安全组是否配置（云服务商控制台）
```

### Q2: 本地前端无法连接后端

**检查清单：**
```bash
# 1. 后端是否运行
curl http://127.0.0.1:6001/api/health

# 2. 前端配置是否正确
cat frontend/.env.local
# 应该有: NEXT_PUBLIC_BACKEND_ORIGIN=http://127.0.0.1:6001

# 3. 是否使用开发配置启动
cd frontend && npm run dev:local
```

### Q3: 端口被占用

```bash
# 查找占用进程
lsof -i :28888  # 云端
lsof -i :6001   # 本地后端
lsof -i :3000   # 本地前端

# 终止进程
kill -9 <PID>
```

### Q4: 前端构建失败

```bash
# 清理并重新安装
cd frontend
rm -rf node_modules .next out
npm install
npm run build
npm run export
```

---

## 📚 文档索引

| 文档 | 说明 |
|------|------|
| `README_DUAL_ENV.md` | 双环境快速指南 |
| `doc/DUAL_ENVIRONMENT.md` | 详细双环境部署指南 |
| `doc/CLOUD_DEPLOYMENT.md` | 云服务器部署详解 |
| `doc/DEPLOYMENT.md` | 通用部署指南 |
| `doc/QUICKSTART.md` | 快速入门 |
| `TESTING.md` | 测试指南 |
| `AGENTS.md` | 开发规范 |

---

## ✅ 部署检查清单

### 云服务器

- [ ] 代码已克隆到 `/data/joy_ip_3d_cloud/`
- [ ] `.env` 已配置（SECRET_KEY已修改）
- [ ] Python依赖已安装
- [ ] 前端依赖已安装
- [ ] 前端已构建（`frontend_dist/` 存在）
- [ ] 防火墙已开放28888端口
- [ ] 云服务商安全组已配置
- [ ] systemd服务已启动并设置自启
- [ ] 可以访问 `http://SERVER_IP:28888`
- [ ] API健康检查通过

### 本地环境

- [ ] 代码已克隆到本地
- [ ] `.env` 已配置
- [ ] `frontend/.env.local` 已配置
- [ ] Python依赖已安装
- [ ] 前端依赖已安装
- [ ] 后端在6001端口运行
- [ ] 前端在3000端口运行
- [ ] 可以访问 `http://localhost:3000`
- [ ] 前端可以调用后端API
- [ ] 热重载功能正常

---

## 🎉 总结

通过这个方案，你可以：

✅ **云端生产环境**：稳定运行在28888端口，前后端整合
✅ **本地开发环境**：支持热重载，前后端分离，快速开发
✅ **完全隔离**：两个环境互不影响，使用不同的配置和端口
✅ **代码同步**：通过Git管理代码，配置通过环境变量区分
✅ **简单部署**：提供自动化脚本，一键部署

**开始使用：**
- 云端部署：查看 `README_DUAL_ENV.md` 的"云服务器部署"章节
- 本地开发：查看 `README_DUAL_ENV.md` 的"本地环境设置"章节

**需要帮助？**
- 详细文档：`doc/DUAL_ENVIRONMENT.md`
- 故障排查：查看各文档的"常见问题"章节

祝部署顺利！🚀
