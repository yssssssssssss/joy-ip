#!/bin/bash

# ============================================
# 云服务器部署脚本
# ============================================
# 在云服务器上执行此脚本

set -e  # 遇到错误立即退出

echo "=== Joy IP 3D 云服务器部署 ==="
echo ""

# 检查是否在云服务器上
if [ "$DEPLOYMENT_ENV" != "cloud" ]; then
    echo "警告：DEPLOYMENT_ENV 不是 'cloud'"
    read -p "确认在云服务器上执行？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 1. 检查.env配置
echo "1. 检查环境配置..."
if [ ! -f .env ]; then
    echo "错误：.env 文件不存在"
    echo "请复制 .env.cloud.example 为 .env："
    echo "  cp .env.cloud.example .env"
    echo "  nano .env  # 修改配置"
    exit 1
fi

# 检查SECRET_KEY是否修改
if grep -q "your-cloud-secret-key-change-this" .env; then
    echo "错误：请修改 .env 中的 SECRET_KEY"
    exit 1
fi

echo "✓ 环境配置检查通过"
echo ""

# 2. 安装Python依赖
echo "2. 安装Python依赖..."
pip3 install -r requirements.txt
echo "✓ Python依赖安装完成"
echo ""

# 3. 安装前端依赖
echo "3. 安装前端依赖..."
cd frontend
npm install
cd ..
echo "✓ 前端依赖安装完成"
echo ""

# 4. 构建前端
echo "4. 构建前端..."
cd frontend
npm run build
npm run export
cd ..

# 验证构建
if [ ! -f frontend_dist/index.html ]; then
    echo "错误：前端构建失败，index.html 不存在"
    exit 1
fi

echo "✓ 前端构建完成"
echo ""

# 5. 创建日志目录
echo "5. 创建日志目录..."
mkdir -p logs
echo "✓ 日志目录创建完成"
echo ""

# 6. 配置防火墙
echo "6. 配置防火墙..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 28888/tcp
    echo "✓ UFW防火墙配置完成"
elif command -v firewall-cmd &> /dev/null; then
    sudo firewall-cmd --permanent --add-port=28888/tcp
    sudo firewall-cmd --reload
    echo "✓ firewalld防火墙配置完成"
else
    echo "警告：未检测到防火墙，请手动配置"
fi
echo ""

# 7. 配置systemd服务
echo "7. 配置systemd服务..."
WORK_DIR=$(pwd)

sudo tee /etc/systemd/system/joy-ip-3d.service > /dev/null << EOF
[Unit]
Description=Joy IP 3D Generation System (Cloud)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$WORK_DIR
Environment="PATH=/usr/bin:/usr/local/bin"
EnvironmentFile=$WORK_DIR/.env
ExecStart=/usr/bin/python3 $WORK_DIR/app_new.py
Restart=always
RestartSec=10
StandardOutput=append:$WORK_DIR/logs/systemd.log
StandardError=append:$WORK_DIR/logs/systemd_error.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
echo "✓ systemd服务配置完成"
echo ""

# 8. 启动服务
echo "8. 启动服务..."
sudo systemctl enable joy-ip-3d
sudo systemctl restart joy-ip-3d

# 等待服务启动
sleep 3

# 检查服务状态
if sudo systemctl is-active --quiet joy-ip-3d; then
    echo "✓ 服务启动成功"
else
    echo "错误：服务启动失败"
    echo "查看日志："
    echo "  sudo journalctl -u joy-ip-3d -n 50"
    exit 1
fi
echo ""

# 9. 验证部署
echo "9. 验证部署..."
sleep 2

# 测试健康检查
if curl -s http://localhost:28888/api/health > /dev/null; then
    echo "✓ 健康检查通过"
else
    echo "错误：健康检查失败"
    exit 1
fi

# 获取服务器IP
SERVER_IP=$(curl -s ifconfig.me || echo "无法获取")

echo ""
echo "=== 部署完成 ==="
echo ""
echo "访问地址："
echo "  - 本地测试: http://localhost:28888"
echo "  - 远程访问: http://$SERVER_IP:28888"
echo ""
echo "管理命令："
echo "  - 查看状态: sudo systemctl status joy-ip-3d"
echo "  - 查看日志: sudo journalctl -u joy-ip-3d -f"
echo "  - 重启服务: sudo systemctl restart joy-ip-3d"
echo "  - 停止服务: sudo systemctl stop joy-ip-3d"
echo ""
echo "注意事项："
echo "  1. 确保云服务商安全组已开放28888端口"
echo "  2. 定期备份 generated_images/ 和 output/ 目录"
echo "  3. 定期更新系统和依赖"
echo ""
