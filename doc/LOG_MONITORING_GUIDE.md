# 日志监控指南

## 当前运行状态

### ✅ 服务已在后台运行
- **进程状态**: 后台运行（daemon）
- **终端要求**: 不需要保持终端打开
- **日志输出**: 自动写入 `logs/app.log`
- **进程管理**: 使用 `nohup` 或系统服务

---

## 📊 日志文件位置

### 主日志文件
```bash
logs/app.log          # 主应用日志（Flask + 业务逻辑）
logs/app_cloud.log    # 云服务器日志（如果配置了）
```

### 日志配置
在 `.env` 文件中配置：
```bash
LOG_FILE=logs/app.log
LOG_LEVEL=INFO
```

---

## 🔍 实时监控日志

### 方法1: tail -f（推荐）
```bash
# 实时查看日志（最常用）
tail -f logs/app.log

# 查看最近100行并持续监控
tail -100f logs/app.log

# 彩色输出（如果安装了 ccze）
tail -f logs/app.log | ccze -A
```

**使用技巧**:
- 按 `Ctrl + C` 退出监控
- 日志会实时滚动显示
- 适合长时间监控

---

### 方法2: less +F（交互式）
```bash
# 交互式实时查看
less +F logs/app.log
```

**使用技巧**:
- 按 `Ctrl + C` 暂停滚动
- 按 `F` 恢复实时滚动
- 按 `q` 退出
- 可以向上滚动查看历史

---

### 方法3: watch（定时刷新）
```bash
# 每2秒刷新最后30行
watch -n 2 'tail -30 logs/app.log'

# 高亮变化
watch -n 2 -d 'tail -30 logs/app.log'
```

---

## 📝 查看历史日志

### 查看最近的日志
```bash
# 最近50行
tail -50 logs/app.log

# 最近100行
tail -100 logs/app.log

# 最近1000行
tail -1000 logs/app.log
```

### 查看全部日志
```bash
# 使用 less 查看（可翻页）
less logs/app.log

# 使用 cat 查看（一次性输出）
cat logs/app.log

# 使用 more 查看（分页）
more logs/app.log
```

---

## 🔎 搜索和过滤日志

### 搜索特定内容
```bash
# 搜索错误
grep -i error logs/app.log

# 搜索警告
grep -i warning logs/app.log

# 搜索特定任务ID
grep "job_id=abc123" logs/app.log

# 搜索特定IP的请求
grep "172.17.255.253" logs/app.log
```

### 搜索并显示上下文
```bash
# 显示匹配行的前后5行
grep -C 5 "error" logs/app.log

# 显示匹配行的前5行
grep -B 5 "error" logs/app.log

# 显示匹配行的后5行
grep -A 5 "error" logs/app.log
```

### 实时搜索
```bash
# 实时监控并过滤错误
tail -f logs/app.log | grep -i error

# 实时监控并过滤多个关键词
tail -f logs/app.log | grep -E "error|warning|failed"

# 实时监控并高亮关键词
tail -f logs/app.log | grep --color=always -E "error|warning|$"
```

---

## 📈 日志分析

### 统计信息
```bash
# 统计错误数量
grep -c "error" logs/app.log

# 统计不同状态码
grep "HTTP/1.1" logs/app.log | awk '{print $9}' | sort | uniq -c

# 统计最活跃的IP
grep -oP '\d+\.\d+\.\d+\.\d+' logs/app.log | sort | uniq -c | sort -rn | head -10

# 统计API调用次数
grep "/api/" logs/app.log | awk '{print $7}' | sort | uniq -c | sort -rn
```

### 按时间过滤
```bash
# 查看今天的日志
grep "$(date +%d/%b/%Y)" logs/app.log

# 查看最近1小时的日志
find logs/ -name "app.log" -mmin -60 -exec tail -100 {} \;

# 查看特定时间段
grep "09/Dec/2025 11:" logs/app.log
```

---

## 🚨 监控关键指标

### 监控错误和异常
```bash
# 实时监控错误
tail -f logs/app.log | grep -i "error\|exception\|failed"

# 统计最近的错误
tail -1000 logs/app.log | grep -i error | tail -20
```

### 监控性能
```bash
# 监控慢请求（假设日志包含响应时间）
tail -f logs/app.log | grep -E "took [0-9]{3,}"

# 监控内存使用
ps aux | grep "[p]ython.*app_new.py" | awk '{print $6/1024 " MB"}'
```

### 监控任务状态
```bash
# 监控任务启动
tail -f logs/app.log | grep "start_generate"

# 监控任务完成
tail -f logs/app.log | grep "succeeded\|failed"

# 监控任务进度
tail -f logs/app.log | grep "progress"
```

---

## 🛠️ 日志管理

### 查看日志大小
```bash
# 查看日志文件大小
ls -lh logs/app.log

# 查看所有日志文件大小
du -sh logs/
```

### 清理日志
```bash
# 清空日志（保留文件）
> logs/app.log

# 备份并清空
cp logs/app.log logs/app.log.backup.$(date +%Y%m%d)
> logs/app.log

# 只保留最近1000行
tail -1000 logs/app.log > logs/app.log.tmp
mv logs/app.log.tmp logs/app.log
```

### 日志轮转（推荐）
创建 `/etc/logrotate.d/joy-ip-3d`:
```bash
/data/joy_ip_3D_new/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
```

---

## 🖥️ 进程管理

### 查看进程状态
```bash
# 查看进程
ps aux | grep "[p]ython.*app_new.py"

# 查看详细信息
ps -fp $(pgrep -f "python.*app_new.py")

# 查看进程树
pstree -p $(pgrep -f "python.*app_new.py")
```

### 查看资源使用
```bash
# CPU和内存使用
top -p $(pgrep -f "python.*app_new.py")

# 或使用 htop（更友好）
htop -p $(pgrep -f "python.*app_new.py")
```

### 重启服务
```bash
# 停止服务
pkill -f 'python.*app_new.py'

# 启动服务（后台运行）
nohup python app_new.py > logs/app.log 2>&1 &

# 或使用部署脚本
./deploy.sh
```

---

## 📱 远程监控

### SSH 连接后监控
```bash
# 连接到服务器
ssh user@your-server-ip

# 查看日志
tail -f /data/joy_ip_3D_new/logs/app.log
```

### 使用 tmux/screen（推荐）
```bash
# 创建 tmux 会话
tmux new -s monitor

# 在 tmux 中监控日志
tail -f logs/app.log

# 分离会话（按 Ctrl+B 然后按 D）
# 重新连接会话
tmux attach -t monitor
```

### 使用 journalctl（如果使用 systemd）
```bash
# 查看服务日志
journalctl -u joy-ip-3d -f

# 查看最近的日志
journalctl -u joy-ip-3d -n 100
```

---

## 🎯 常用监控命令组合

### 完整监控面板
```bash
# 在一个终端中运行
watch -n 1 '
echo "=== 服务状态 ==="
ps aux | grep "[p]ython.*app_new.py" | head -1
echo ""
echo "=== 最近的日志 ==="
tail -10 logs/app.log
echo ""
echo "=== 错误统计 ==="
tail -1000 logs/app.log | grep -c "error"
'
```

### 多窗口监控（使用 tmux）
```bash
# 创建多窗口会话
tmux new -s monitor

# 窗口1: 实时日志
tail -f logs/app.log

# 创建新窗口（Ctrl+B 然后按 C）
# 窗口2: 系统资源
htop -p $(pgrep -f "python.*app_new.py")

# 创建新窗口
# 窗口3: 错误监控
tail -f logs/app.log | grep -i error

# 切换窗口（Ctrl+B 然后按 数字键）
```

---

## 🔔 告警设置

### 简单的错误告警脚本
创建 `monitor_errors.sh`:
```bash
#!/bin/bash
LAST_CHECK=$(date +%s)
while true; do
    ERRORS=$(tail -100 logs/app.log | grep -c "error")
    if [ $ERRORS -gt 5 ]; then
        echo "警告: 发现 $ERRORS 个错误！"
        # 可以在这里添加邮件或消息通知
    fi
    sleep 60
done
```

### 使用 cron 定期检查
```bash
# 编辑 crontab
crontab -e

# 添加每5分钟检查一次
*/5 * * * * /data/joy_ip_3D_new/monitor_errors.sh
```

---

## 📚 快速参考

### 最常用的命令
```bash
# 实时查看日志
tail -f logs/app.log

# 查看最近50行
tail -50 logs/app.log

# 搜索错误
grep -i error logs/app.log

# 查看进程
ps aux | grep "[p]ython.*app_new.py"

# 重启服务
./deploy.sh
```

### 故障排查流程
```bash
# 1. 检查服务是否运行
ps aux | grep "[p]ython.*app_new.py"

# 2. 查看最近的日志
tail -50 logs/app.log

# 3. 搜索错误
grep -i error logs/app.log | tail -20

# 4. 检查API健康
curl http://localhost:28888/api/health

# 5. 如果需要，重启服务
./deploy.sh
```

---

## 💡 最佳实践

### 1. 使用日志级别
在 `.env` 中设置：
```bash
LOG_LEVEL=INFO    # 生产环境
LOG_LEVEL=DEBUG   # 开发环境
```

### 2. 定期清理日志
```bash
# 每周清理一次旧日志
0 0 * * 0 find /data/joy_ip_3D_new/logs -name "*.log" -mtime +7 -delete
```

### 3. 使用日志轮转
避免日志文件过大，使用 logrotate

### 4. 监控关键指标
- 错误率
- 响应时间
- 内存使用
- CPU使用

### 5. 设置告警
对关键错误设置告警通知

---

## 🆘 常见问题

### Q: 日志文件不存在？
```bash
# 创建日志目录
mkdir -p logs

# 重启服务
./deploy.sh
```

### Q: 日志没有更新？
```bash
# 检查服务是否运行
ps aux | grep "[p]ython.*app_new.py"

# 检查日志配置
cat .env | grep LOG_FILE
```

### Q: 日志文件太大？
```bash
# 查看大小
ls -lh logs/app.log

# 清理日志
> logs/app.log

# 或使用日志轮转
```

### Q: 如何在后台运行并保存日志？
```bash
# 使用 nohup
nohup python app_new.py > logs/app.log 2>&1 &

# 或使用部署脚本
./deploy.sh
```

---

**最后更新**: 2025-12-09  
**相关文档**: `QUICK_REFERENCE.md`, `DEVELOPMENT_WORKFLOW.md`
