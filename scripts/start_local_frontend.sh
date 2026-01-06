#!/bin/bash

# ============================================
# 本地前端启动脚本
# ============================================

echo "=== 启动本地前端开发服务器 ==="

# 进入前端目录
cd frontend || exit 1

# 检查.env.local文件
if [ ! -f .env.local ]; then
    echo "警告：.env.local 文件不存在"
    echo "创建默认配置..."
    cat > .env.local << 'EOF'
# 后端API地址
NEXT_PUBLIC_BACKEND_ORIGIN=http://127.0.0.1:6001
EOF
    echo "已创建 frontend/.env.local"
fi

# 检查node_modules
if [ ! -d node_modules ]; then
    echo "错误：node_modules 不存在"
    echo "请安装依赖："
    echo "  cd frontend && npm install"
    exit 1
fi

# 检查开发配置文件
if [ ! -f next.config.dev.js ]; then
    echo "错误：next.config.dev.js 不存在"
    echo "请确保该文件存在"
    exit 1
fi

echo "前端配置："
echo "  - 端口: 3000"
echo "  - 后端代理: http://127.0.0.1:6001"
echo "  - 配置文件: next.config.dev.js"
echo ""
echo "启动中..."
echo ""

# 使用开发配置启动
NEXT_CONFIG_FILE=next.config.dev.js npm run dev
