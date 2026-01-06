# 云服务器部署指南

本文档专门针对云服务器（阿里云、腾讯云、AWS、GCP等）的部署说明。

## 目录

- [前置要求](#前置要求)
- [获取服务器信息](#获取服务器信息)
- [部署步骤](#部署步骤)
- [网络配置](#网络配置)
- [访问应用](#访问应用)
- [常见问题](#常见问题)

## 前置要求

### 服务器配置建议

- **CPU：** 2核或以上
- **内存：** 4GB或以上
- **磁盘：** 20GB或以上
- **操作系统：** Ubuntu 20.04/22.04 或 CentOS 7/8
- **Python：** 3.8+
- **Node.js：** 18+

### 网络要求

- 公网IP地址
- 开放端口：28888（应用端口）
- 可选：80/443（如果使用Nginx反向代理）

## 获取服务器信息

### 1. 查看公网IP

```bash
# 方法1：使用curl
curl ifconfig.me

# 方法2：使用ipinfo
curl ipinfo.io/ip

# 方法3：查看网络接口
ip addr show | grep inet
```

记录下你的公网IP，例如：`123.45.67.89`

### 2. 查看内网IP

```bash
hostname -I
```

### 3. 验证端口监听

```bash
# 查看28888端口是否被占用
sudo lsof -i :28888

# 或使用netstat
sudo netstat -tlnp | grep 28888
```

## 部署步骤

### 1. 连接到服务器

```bash
# 使用SSH连接
ssh username@YOUR_SERVER_IP

# 或使用密钥
ssh -i /path/to/key.pem username@YOUR_SERVER_IP
```

### 2. 安装依赖

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
# 或
sudo yum update -y  # CentOS/RHEL

# 安装Python 3.8+
sudo apt install python3 python3-pip -y  # Ubuntu/Debian
# 或
sudo yum install python3 python3-pip -y  # CentOS/RHEL

# 安装Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs  # Ubuntu/Debian
# 或
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs  # CentOS/RHEL

# 验证安装
python3 --version
node --version
npm --version
```

### 3. 克隆项目

```bash
cd /data  # 或其他目录
git clone <repository-url>
cd joy_ip_3D_new
```

### 4. 安装项目依赖

```bash
# 安装Python依赖
pip3 install -r requirements.txt

# 安装前端依赖
cd frontend
npm install
cd ..
```

### 5. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置
nano .env  # 或使用 vi .env
```

**关键配置：**

```bash
# 服务器端口
PORT=28888

# 单端口模式
SINGLE_PORT_MODE=true

# 运行环境
FLASK_ENV=production

# 安全密钥（必须修改！）
SECRET_KEY=your-very-secure-secret-key-here

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### 6. 构建前端

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

## 网络配置

### 1. 配置防火墙

#### Ubuntu/Debian (UFW)

```bash
# 检查防火墙状态
sudo ufw status

# 如果未启用，先启用
sudo ufw enable

# 允许SSH（重要！避免被锁定）
sudo ufw allow 22/tcp

# 允许应用端口
sudo ufw allow 28888/tcp

# 如果使用Nginx
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 重新加载
sudo ufw reload

# 查看规则
sudo ufw status numbered
```

#### CentOS/RHEL (firewalld)

```bash
# 检查防火墙状态
sudo firewall-cmd --state

# 添加端口
sudo firewall-cmd --permanent --add-port=28888/tcp
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp

# 重新加载
sudo firewall-cmd --reload

# 查看规则
sudo firewall-cmd --list-all
```

### 2. 配置云服务商安全组

#### 阿里云 ECS

1. 登录阿里云控制台
2. 进入 **云服务器ECS** > **实例**
3. 点击实例ID，进入详情页
4. 点击 **安全组** 标签
5. 点击安全组ID，进入安全组规则
6. 点击 **添加安全组规则**
7. 配置入站规则：
   - **规则方向：** 入方向
   - **授权策略：** 允许
   - **协议类型：** 自定义TCP
   - **端口范围：** 28888/28888
   - **授权对象：** 0.0.0.0/0
   - **描述：** Joy IP 3D应用端口

#### 腾讯云 CVM

1. 登录腾讯云控制台
2. 进入 **云服务器** > **实例**
3. 点击实例ID
4. 选择 **安全组** 标签
5. 点击 **编辑规则**
6. 添加入站规则：
   - **类型：** 自定义
   - **来源：** 0.0.0.0/0
   - **协议端口：** TCP:28888
   - **策略：** 允许

#### AWS EC2

1. 登录AWS控制台
2. 进入 **EC2** > **实例**
3. 选择实例，点击 **安全组**
4. 点击安全组ID
5. 选择 **入站规则** > **编辑入站规则**
6. 添加规则：
   - **类型：** 自定义TCP
   - **端口范围：** 28888
   - **源：** 0.0.0.0/0
   - **描述：** Joy IP 3D Application

### 3. 验证网络配置

```bash
# 在服务器上测试本地访问
curl http://localhost:28888/api/health

# 从其他机器测试远程访问
curl http://YOUR_SERVER_IP:28888/api/health
```

## 启动应用

### 方法1：直接启动（测试用）

```bash
python3 app_new.py
```

### 方法2：后台运行（使用nohup）

```bash
nohup python3 app_new.py > logs/app.log 2>&1 &

# 查看进程
ps aux | grep app_new.py

# 查看日志
tail -f logs/app.log
```

### 方法3：使用Gunicorn（推荐）

```bash
# 安装Gunicorn
pip3 install gunicorn

# 启动应用
gunicorn -w 4 -b 0.0.0.0:28888 --timeout 120 --daemon app_new:app

# 查看进程
ps aux | grep gunicorn

# 停止
pkill gunicorn
```

### 方法4：使用systemd（生产推荐）

创建服务文件：

```bash
sudo nano /etc/systemd/system/joy-ip-3d.service
```

内容：

```ini
[Unit]
Description=Joy IP 3D Generation System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/data/joy_ip_3D_new
Environment="PATH=/usr/bin:/usr/local/bin"
Environment="PORT=28888"
Environment="SINGLE_PORT_MODE=true"
Environment="FLASK_ENV=production"
ExecStart=/usr/bin/python3 app_new.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
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

## 访问应用

### 获取访问地址

```bash
# 获取公网IP
SERVER_IP=$(curl -s ifconfig.me)
echo "应用访问地址: http://$SERVER_IP:28888"
```

### 浏览器访问

打开浏览器，访问：

```
http://YOUR_SERVER_IP:28888
```

例如：`http://123.45.67.89:28888`

### API测试

```bash
# 健康检查
curl http://YOUR_SERVER_IP:28888/api/health

# 内容分析
curl -X POST http://YOUR_SERVER_IP:28888/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"requirement":"生成一个微笑的香蕉"}'
```

## 使用域名访问（可选）

### 1. 配置DNS

在域名服务商处添加A记录：

```
类型: A
主机记录: @ 或 www
记录值: YOUR_SERVER_IP
TTL: 600
```

### 2. 配置Nginx反向代理

安装Nginx：

```bash
sudo apt install nginx -y  # Ubuntu/Debian
# 或
sudo yum install nginx -y  # CentOS/RHEL
```

创建配置文件：

```bash
sudo nano /etc/nginx/sites-available/joy-ip-3d
```

内容：

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://127.0.0.1:28888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/joy-ip-3d /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 3. 配置SSL（推荐）

```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx -y

# 获取证书
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

访问：`https://your-domain.com`

## 常见问题

### Q1: 无法从外网访问

**检查清单：**

1. 服务是否正常运行？
```bash
sudo systemctl status joy-ip-3d
curl http://localhost:28888/api/health
```

2. 防火墙是否开放端口？
```bash
sudo ufw status | grep 28888
```

3. 云服务商安全组是否配置？
   - 登录控制台检查安全组规则

4. 应用是否监听0.0.0.0？
```bash
sudo netstat -tlnp | grep 28888
# 应该显示 0.0.0.0:28888 而不是 127.0.0.1:28888
```

### Q2: 端口被占用

```bash
# 查看占用端口的进程
sudo lsof -i :28888

# 终止进程
sudo kill -9 <PID>

# 或修改端口
export PORT=28889
```

### Q3: 前端页面无法加载

```bash
# 检查前端构建目录
ls -la frontend_dist/

# 如果不存在，重新构建
cd frontend
npm run build
npm run export
cd ..

# 重启应用
sudo systemctl restart joy-ip-3d
```

### Q4: 图片生成失败

```bash
# 检查日志
tail -f logs/app.log

# 检查磁盘空间
df -h

# 检查Python脚本
ls -la *.py

# 检查权限
chmod +x *.py
```

### Q5: 内存不足

```bash
# 查看内存使用
free -h

# 创建swap（如果内存小于4GB）
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永久启用
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 监控和维护

### 查看日志

```bash
# 应用日志
tail -f logs/app.log

# systemd日志
sudo journalctl -u joy-ip-3d -f

# Nginx日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 性能监控

```bash
# 查看CPU和内存
htop

# 查看磁盘IO
iostat -x 1

# 查看网络
iftop
```

### 定期维护

```bash
# 清理旧日志
find logs/ -name "*.log" -mtime +30 -delete

# 清理临时文件
find generated_images/ -name "tmp_*" -mtime +7 -delete

# 更新系统
sudo apt update && sudo apt upgrade -y
```

## 安全建议

1. **修改默认端口**（可选）
2. **使用强密码**
3. **启用防火墙**
4. **配置SSL证书**
5. **定期更新系统和依赖**
6. **限制SSH访问**（使用密钥认证）
7. **配置fail2ban防止暴力破解**
8. **定期备份数据**

## 备份和恢复

### 备份

```bash
# 创建备份目录
mkdir -p /backup/joy_ip_3d

# 备份应用
tar -czf /backup/joy_ip_3d/app_$(date +%Y%m%d).tar.gz \
  --exclude='node_modules' \
  --exclude='frontend_dist' \
  --exclude='__pycache__' \
  /data/joy_ip_3D_new

# 备份生成的图片
tar -czf /backup/joy_ip_3d/images_$(date +%Y%m%d).tar.gz \
  /data/joy_ip_3D_new/generated_images \
  /data/joy_ip_3D_new/output
```

### 恢复

```bash
# 恢复应用
tar -xzf /backup/joy_ip_3d/app_20240101.tar.gz -C /

# 恢复图片
tar -xzf /backup/joy_ip_3d/images_20240101.tar.gz -C /
```

## 获取帮助

如遇到问题：

1. 查看日志文件
2. 检查防火墙和安全组配置
3. 验证网络连接
4. 查阅本文档的常见问题部分
5. 提交Issue并附上日志信息
