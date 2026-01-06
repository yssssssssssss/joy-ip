# 部署指南

本文档描述如何在云服务器上部署 Joy IP 3D 图片生成系统。

## 目录

- [云服务器部署](#云服务器部署)
- [使用Gunicorn部署](#使用gunicorn部署)
- [使用Nginx反向代理](#使用nginx反向代理)
- [环境变量配置](#环境变量配置)

## 云服务器部署

云服务器部署模式将前端和后端整合到一个Flask应用中，在单一端口（28888）上提供完整服务。

### 前置要求

- Python 3.8+
- Node.js 18+
- pip
- npm
- 云服务器公网IP
- 开放端口：28888

### 步骤1：安装后端依赖

```bash
pip install -r requirements.txt
```

### 步骤2：配置环境变量

复制环境变量示例文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置必要的配置：

```bash
# 服务器端口
PORT=28888

# 服务器主机地址
HOST=0.0.0.0

# 前端构建目录
FRONTEND_BUILD_DIR=frontend_dist

# 安全密钥（生产环境必须修改）
SECRET_KEY=your-secret-key-here-change-in-production

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### 步骤3：构建前端

```bash
cd frontend
npm install
npm run build
npm run export
cd ..
```

这将生成静态文件到 `frontend_dist` 目录。

### 步骤4：配置防火墙和安全组

**开放端口28888：**

```bash
# Ubuntu/Debian (使用ufw)
sudo ufw allow 28888/tcp
sudo ufw status

# CentOS/RHEL (使用firewalld)
sudo firewall-cmd --permanent --add-port=28888/tcp
sudo firewall-cmd --reload
```

**云服务器安全组配置：**

如果使用云服务器，需要在云服务商控制台配置安全组：

1. 登录云服务商控制台（阿里云、腾讯云、AWS等）
2. 找到ECS实例的安全组设置
3. 添加入站规则：
   - 协议类型：TCP
   - 端口范围：28888
   - 授权对象：0.0.0.0/0（允许所有IP访问）

### 步骤5：启动应用

```bash
python app_new.py
```

应用将在 `http://0.0.0.0:28888` 上运行。

### 验证部署

**获取服务器IP：**

```bash
# 查看公网IP
curl ifconfig.me
# 或
curl ipinfo.io/ip
```

**访问应用：**

- 前端页面：`http://YOUR_SERVER_IP:28888/`
- API健康检查：`http://YOUR_SERVER_IP:28888/api/health`

**本地测试（在服务器上）：**

```bash
curl http://localhost:28888/api/health
```

**远程测试（从浏览器或其他机器）：**

```bash
curl http://YOUR_SERVER_IP:28888/api/health
```

## 使用Gunicorn部署

Gunicorn是推荐的生产环境WSGI服务器。

### 安装Gunicorn

```bash
pip install gunicorn
```

### 启动应用

```bash
# 基本启动
gunicorn -w 4 -b 0.0.0.0:28888 app_new:app

# 带超时配置
gunicorn -w 4 -b 0.0.0.0:28888 --timeout 120 app_new:app

# 后台运行
gunicorn -w 4 -b 0.0.0.0:28888 --timeout 120 --daemon app_new:app
```

参数说明：
- `-w 4`：4个工作进程
- `-b 0.0.0.0:28888`：绑定到所有接口的28888端口
- `--timeout 120`：请求超时时间120秒
- `--daemon`：后台运行

### 使用配置文件

创建 `gunicorn.conf.py`：

```python
# Gunicorn配置文件
import os

# 绑定地址
bind = f"0.0.0.0:{os.environ.get('PORT', 28888)}"

# 工作进程数
workers = 4

# 工作模式
worker_class = 'sync'

# 超时时间
timeout = 120

# 日志
accesslog = 'logs/gunicorn_access.log'
errorlog = 'logs/gunicorn_error.log'
loglevel = 'info'

# 进程名称
proc_name = 'joy_ip_3d'
```

启动：

```bash
gunicorn -c gunicorn.conf.py app_new:app
```

### 使用systemd管理

创建服务文件 `/etc/systemd/system/joy-ip-3d.service`：

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

## 使用Nginx反向代理

Nginx可以作为反向代理，提供负载均衡、SSL终止等功能。

### 安装Nginx

```bash
# Ubuntu/Debian
sudo apt-get install nginx

# CentOS/RHEL
sudo yum install nginx
```

### 配置Nginx

创建配置文件 `/etc/nginx/sites-available/joy-ip-3d`：

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # 客户端最大请求体大小
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://127.0.0.1:28888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 增加超时时间以支持长时间运行的脚本
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
    }
    
    # 静态文件缓存
    location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
        proxy_pass http://127.0.0.1:28888;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/joy-ip-3d /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL配置（可选）

使用Let's Encrypt获取免费SSL证书：

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 环境变量配置

### 必需的环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `PORT` | 服务器端口 | 28888 |
| `HOST` | 服务器主机地址 | 0.0.0.0 |
| `FRONTEND_BUILD_DIR` | 前端构建目录 | frontend_dist |
| `SECRET_KEY` | Flask密钥 | - |

### 可选的环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `LOG_LEVEL` | 日志级别 | INFO |
| `LOG_FILE` | 日志文件路径 | logs/app.log |
| `SCRIPT_TIMEOUT` | 脚本执行超时（秒） | 120 |
| `OPENAI_API_KEY` | OpenAI API密钥 | - |
| `OPENAI_API_BASE` | OpenAI API基础URL | - |

### 设置环境变量

**方法1：使用.env文件**

```bash
cp .env.example .env
# 编辑.env文件
```

**方法2：直接导出**

```bash
export PORT=28888
export SECRET_KEY=your-secret-key
```

**方法3：在启动命令中指定**

```bash
PORT=28888 SECRET_KEY=your-secret-key python app_new.py
```

## 故障排查

### 前端构建目录不存在

**错误信息：**
```
警告：前端构建目录不存在！
```

**解决方法：**
```bash
cd frontend
npm run build
npm run export
cd ..
```

### 端口已被占用

**错误信息：**
```
Address already in use
```

**解决方法：**
```bash
# 查找占用端口的进程
lsof -i :28888

# 终止进程
kill -9 <PID>
```

### 脚本执行超时

**错误信息：**
```
脚本执行超时（120秒）
```

**解决方法：**
```bash
# 增加超时时间
export SCRIPT_TIMEOUT=300
```

### 日志查看

```bash
# 查看实时日志
tail -f logs/app.log

# 查看Gunicorn日志
tail -f logs/gunicorn_error.log
```

## 性能优化

### 1. 使用多个工作进程

```bash
gunicorn -w 8 -b 0.0.0.0:28888 app_new:app
```

工作进程数建议：`2 * CPU核心数 + 1`

### 2. 启用Nginx缓存

在Nginx配置中添加：

```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:10m max_size=1g inactive=60m;

location / {
    proxy_cache my_cache;
    proxy_cache_valid 200 60m;
    # ...
}
```

### 3. 使用CDN

将生成的图片上传到CDN，减轻服务器负载。

## 安全建议

1. **修改默认密钥**：生产环境必须设置强密码的`SECRET_KEY`
2. **使用HTTPS**：配置SSL证书，启用HTTPS
3. **限制访问**：使用防火墙限制不必要的端口访问
4. **定期更新**：保持依赖包更新到最新版本
5. **备份数据**：定期备份生成的图片和配置文件

## 监控和维护

### 健康检查

```bash
curl http://YOUR_SERVER_IP:28888/api/health
```

### 进程监控

使用systemd管理应用进程（参见上文）。

### 日志监控

```bash
# 实时查看日志
tail -f logs/app.log

# 查看systemd日志
sudo journalctl -u joy-ip-3d -f
```

## 更新部署

### 更新代码

```bash
# 拉取最新代码
git pull

# 更新依赖
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 重新构建前端
cd frontend && npm run export && cd ..

# 重启应用
sudo systemctl restart joy-ip-3d
```

## 支持

如有问题，请查看：
- [快速入门指南](QUICKSTART.md)
- [云服务器部署指南](CLOUD_DEPLOYMENT.md)
- [开发指南](AGENTS.md)
