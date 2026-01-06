#!/bin/bash

# ============================================
# 本地后端启动脚本
# ============================================

echo "=== 启动本地后端服务 ==="

# 检查.env文件
if [ ! -f .env ]; then
    echo "错误：.env 文件不存在"
    echo "请复制 .env.local.example 为 .env："
    echo "  cp .env.local.example .env"
    exit 1
fi

# 检查Python依赖
if ! python -c "import flask" 2>/dev/null; then
    echo "错误：Flask未安装"
    echo "请安装依赖："
    echo "  pip install -r requirements.txt"
    exit 1
fi

# 创建日志目录
mkdir -p logs

# 设置环境变量
export PORT=6001
export HOST=127.0.0.1
export DEPLOYMENT_ENV=local

echo "后端配置："
echo "  - 端口: 6001"
echo "  - 主机: 127.0.0.1"
echo "  - 环境: local"
echo ""
echo "启动中..."
echo ""

# 启动后端
python app_new.py
