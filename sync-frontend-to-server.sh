#!/bin/bash
# 在服务器上执行此脚本来同步前端代码
# 使用方法：在服务器上执行 bash sync-frontend-to-server.sh

set -e  # 遇到错误立即退出

echo "=========================================="
echo "同步前端代码到服务器"
echo "=========================================="

# 服务器项目路径
PROJECT_PATH="/data/joy-ip"

# 切换到项目目录
cd "$PROJECT_PATH" || exit 1
echo "✓ 切换到项目目录: $PROJECT_PATH"

# 显示当前分支
echo ""
echo "当前分支信息："
git branch -v

# 拉取最新代码
echo ""
echo "正在从 GitHub 拉取最新代码..."
git fetch origin
git pull origin main

echo ""
echo "✓ 代码同步完成！"

# 显示前端目录状态
echo ""
echo "前端目录状态："
if [ -d "frontend" ]; then
    echo "✓ frontend/ 目录存在"
    echo "  文件数量: $(find frontend -type f | wc -l)"
    echo "  目录大小: $(du -sh frontend | cut -f1)"
else
    echo "✗ frontend/ 目录不存在"
fi

# 显示 frontend_dist 目录状态
if [ -d "frontend_dist" ]; then
    echo "✓ frontend_dist/ 目录存在（构建产物）"
else
    echo "✗ frontend_dist/ 目录不存在"
fi

echo ""
echo "=========================================="
echo "同步完成！"
echo "=========================================="
echo ""
echo "下一步操作："
echo "1. 如果需要重新构建前端："
echo "   cd frontend && npm install && npm run build && npm run export"
echo ""
echo "2. 如果需要重启后端服务："
echo "   # 根据你的服务管理方式重启"
echo "   # 例如: systemctl restart joy-ip"
echo "   # 或者: pm2 restart joy-ip"
echo ""
