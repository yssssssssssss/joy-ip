# 后台服务运行指南

## ✅ 当前状态

### 服务运行模式
- **运行方式**: 后台守护进程（daemon）
- **终端要求**: ❌ 不需要保持终端打开
- **日志输出**: ✅ 自动写入 `logs/app.log`
- **自动重启**: ❌ 需要手动重启（可配置 systemd）

### 进程信息
```bash
# 查看进程
ps aux | grep "[p]ython.*app_new.py"

# 输出示例
root  700032  1.5  0.1  31982412  1136824  ?  Sl  11:07  0:18  python app_new.py
```

**字段说明**:
- `700032`: 进程ID (PID)
- `1.5`: CPU使用率 (%)
- `0.1`: 内存使用率 (%)
- `?`: 后台运行（无控制终端）
- `Sl`: 进程状态（S=睡眠，l=多线程）

---

## 📊 监控方式

### 方法1: 快速监控脚本（推荐）
```bash
./monitor.sh
```

**显示内容**:
- ✅ 服务状态（PID、CPU、内存）
- 📝 日志文件信息（大小、行数）
- 🚨 最近的错误
- 📡 最近的请求

---

### 方法2: 实时查看日志
```bash
# 实时滚动查看（最常用）
tail -f logs/app.log

# 查看最近100行并持续监控
tail -100f logs/app.log

# 退出监控：按 Ctrl + C
```

---

### 方法3: 查看历史日志
```bash
# 最近50行
tail -50 logs/app.log

# 搜索错误
grep -i error logs/app.log

# 搜索特定任务
grep "job_id=abc123" logs/app.log
```

---

### 方法4: 完整部署检查
```bash
./check_deployment.sh
```

**检查内容**:
- 后端服务状态
- 端口监听状态
- API 健康检查
- 前端文件状态
- 环境配置

---

## 🔄 服务管理

### 启动服务
```bash
# 方法1: 使用部署脚本（推荐）
./deploy.sh

# 方法2: 手动启动
nohup python app_new.py > logs/app.log 2>&1 &
```

### 停止服务
```bash
# 停止服务
pkill -f 'python.*app_new.py'

# 确认已停止
ps aux | grep "[p]ython.*app_new.py"
```

### 重启服务
```bash
# 一键重启
./deploy.sh

# 或手动重启
pkill -f 'python.*app_new.py'
sleep 2
nohup python app_new.py > logs/app.log 2>&1 &
```

### 查看服务状态
```bash
# 检查进程
ps aux | grep "[p]ython.*app_new.py"

# 检查端口
netstat -tuln | grep 28888

# 健康检查
curl http://localhost:28888/api/health
```

---

## 📝 日志管理

### 日志文件位置
```
logs/
├── app.log          # 主日志文件
└── app_cloud.log    # 云服务器日志（如果配置）
```

### 日志配置
在 `.env` 文件中：
```bash
LOG_FILE=logs/app.log
LOG_LEVEL=INFO
```

### 查看日志大小
```bash
# 查看单个文件
ls -lh logs/app.log

# 查看所有日志
du -sh logs/
```

### 清理日志
```bash
# 清空日志（保留文件）
> logs/app.log

# 备份后清空
cp logs/app.log logs/app.log.backup.$(date +%Y%m%d)
> logs/app.log

# 只保留最近1000行
tail -1000 logs/app.log > logs/app.log.tmp
mv logs/app.log.tmp logs/app.log
```

---

## 🚨 常见问题

### Q1: 如何知道服务是否在运行？
```bash
# 方法1: 查看进程
ps aux | grep "[p]ython.*app_new.py"

# 方法2: 运行监控脚本
./monitor.sh

# 方法3: 健康检查
curl http://localhost:28888/api/health
```

### Q2: 服务崩溃了怎么办？
```bash
# 1. 查看最近的日志
tail -50 logs/app.log

# 2. 搜索错误
grep -i error logs/app.log | tail -20

# 3. 重启服务
./deploy.sh
```

### Q3: 如何查看实时日志？
```bash
# 实时查看
tail -f logs/app.log

# 实时查看并过滤错误
tail -f logs/app.log | grep -i error
```

### Q4: 日志文件太大怎么办？
```bash
# 查看大小
ls -lh logs/app.log

# 如果超过100MB，清理日志
> logs/app.log

# 或设置日志轮转（见下文）
```

### Q5: 关闭终端后服务会停止吗？
**不会！** 服务使用 `nohup` 在后台运行，关闭终端不影响服务。

---

## 🔧 高级配置

### 使用 systemd 管理服务（推荐）

创建服务文件 `/etc/systemd/system/joy-ip-3d.service`:
```ini
[Unit]
Description=Joy IP 3D Generation System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/data/joy_ip_3D_new
Environment="PATH=/root/miniconda3/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/root/miniconda3/bin/python app_new.py
Restart=always
RestartSec=10
StandardOutput=append:/data/joy_ip_3D_new/logs/app.log
StandardError=append:/data/joy_ip_3D_new/logs/app.log

[Install]
WantedBy=multi-user.target
```

**使用方法**:
```bash
# 重载配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start joy-ip-3d

# 停止服务
sudo systemctl stop joy-ip-3d

# 重启服务
sudo systemctl restart joy-ip-3d

# 查看状态
sudo systemctl status joy-ip-3d

# 开机自启
sudo systemctl enable joy-ip-3d

# 查看日志
sudo journalctl -u joy-ip-3d -f
```

---

### 配置日志轮转

创建 `/etc/logrotate.d/joy-ip-3d`:
```bash
/data/joy_ip_3D_new/logs/*.log {
    daily                # 每天轮转
    rotate 7             # 保留7天
    compress             # 压缩旧日志
    delaycompress        # 延迟压缩
    missingok            # 文件不存在不报错
    notifempty           # 空文件不轮转
    create 0644 root root  # 创建新文件的权限
}
```

**测试配置**:
```bash
sudo logrotate -d /etc/logrotate.d/joy-ip-3d
```

---

### 使用 tmux 持久化会话

```bash
# 创建会话
tmux new -s joy-monitor

# 在会话中监控日志
tail -f logs/app.log

# 分离会话（按 Ctrl+B 然后按 D）

# 重新连接
tmux attach -t joy-monitor

# 列出所有会话
tmux ls

# 删除会话
tmux kill-session -t joy-monitor
```

---

## 📈 性能监控

### 查看资源使用
```bash
# CPU和内存
top -p $(pgrep -f "python.*app_new.py")

# 或使用 htop（更友好）
htop -p $(pgrep -f "python.*app_new.py")

# 查看进程树
pstree -p $(pgrep -f "python.*app_new.py")
```

### 监控网络连接
```bash
# 查看监听端口
netstat -tuln | grep 28888

# 查看活动连接
netstat -anp | grep 28888

# 或使用 ss
ss -tuln | grep 28888
```

### 监控磁盘使用
```bash
# 查看磁盘空间
df -h

# 查看项目目录大小
du -sh /data/joy_ip_3D_new

# 查看各子目录大小
du -h --max-depth=1 /data/joy_ip_3D_new
```

---

## 🎯 快速参考

### 最常用命令
```bash
# 查看服务状态
./monitor.sh

# 实时查看日志
tail -f logs/app.log

# 重启服务
./deploy.sh

# 检查部署
./check_deployment.sh

# 健康检查
curl http://localhost:28888/api/health
```

### 故障排查流程
```bash
# 1. 检查服务
ps aux | grep "[p]ython.*app_new.py"

# 2. 查看日志
tail -50 logs/app.log

# 3. 搜索错误
grep -i error logs/app.log | tail -20

# 4. 重启服务
./deploy.sh

# 5. 验证恢复
curl http://localhost:28888/api/health
```

---

## 📚 相关文档

- **`LOG_MONITORING_GUIDE.md`** - 完整的日志监控指南
- **`QUICK_REFERENCE.md`** - 快速参考卡片
- **`DEVELOPMENT_WORKFLOW.md`** - 开发流程指南
- **`monitor.sh`** - 实时监控脚本
- **`check_deployment.sh`** - 部署检查脚本
- **`deploy.sh`** - 一键部署脚本

---

## 💡 最佳实践

### 1. 定期检查服务状态
```bash
# 每天运行一次
./monitor.sh
```

### 2. 监控日志大小
```bash
# 每周检查一次
ls -lh logs/app.log
```

### 3. 定期清理日志
```bash
# 每月清理一次
> logs/app.log
```

### 4. 使用 systemd 管理
- 自动重启
- 开机自启
- 统一管理

### 5. 配置日志轮转
- 避免日志过大
- 自动压缩旧日志
- 保留历史记录

---

## 🆘 紧急情况处理

### 服务无响应
```bash
# 1. 强制停止
pkill -9 -f 'python.*app_new.py'

# 2. 清理日志
> logs/app.log

# 3. 重启服务
./deploy.sh

# 4. 监控启动
tail -f logs/app.log
```

### 端口被占用
```bash
# 1. 查找占用进程
lsof -i :28888

# 2. 停止进程
kill -9 <PID>

# 3. 重启服务
./deploy.sh
```

### 磁盘空间不足
```bash
# 1. 检查磁盘
df -h

# 2. 清理日志
> logs/app.log

# 3. 清理生成的图片
find output/ -mtime +7 -delete
find generated_images/ -mtime +7 -delete
```

---

**最后更新**: 2025-12-09  
**维护者**: 开发团队  
**状态**: ✅ 服务正常运行
