#!/bin/bash
# Joy IP 3D 完整重建部署脚本
# 用法: ./rebuild.sh

set -e

echo "=========================================="
echo "🔄 Joy IP 3D 完整重建部署"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo ""
echo -e "${YELLOW}📁 工作目录: $PROJECT_DIR${NC}"

UNAME="$(uname -s 2>/dev/null || echo unknown)"
if [[ "$OS" == "Windows_NT" || "$UNAME" == MINGW* || "$UNAME" == MSYS* || "$UNAME" == CYGWIN* ]]; then
    echo -e "${RED}当前为 Windows 环境，已禁止运行本脚本。请使用 rebuild_and_start.bat${NC}"
    exit 1
fi

# 步骤 1: 停止旧服务
echo ""
echo -e "${YELLOW}🛑 步骤 1/6: 停止旧服务...${NC}"
pkill -f "python.*app_new.py" 2>/dev/null || true
sleep 2
pkill -9 -f "python.*app_new.py" 2>/dev/null || true
echo -e "${GREEN}✓ 旧服务已停止${NC}"

# 步骤 2: 清除旧的前端构建文件
echo ""
echo -e "${YELLOW}🗑️  步骤 2/6: 清除旧的前端构建文件...${NC}"
rm -rf frontend_dist/* 2>/dev/null || true
rm -rf frontend/.next 2>/dev/null || true
rm -rf frontend/out 2>/dev/null || true
echo -e "${GREEN}✓ 旧构建文件已清除${NC}"

# 步骤 3: 构建前端
echo ""
echo -e "${YELLOW}📦 步骤 3/6: 构建前端...${NC}"
cd frontend
npm run build
echo -e "${GREEN}✓ 前端构建完成${NC}"

# 步骤 4: 导出静态文件
echo ""
echo -e "${YELLOW}📤 步骤 4/6: 导出静态文件...${NC}"
if [ ! -d "out" ]; then
    npm run export
fi
export FRONTEND_BUILD_DIR="${PROJECT_DIR}/frontend/out"
cd "$PROJECT_DIR"
echo -e "${GREEN}✓ 静态文件目录设置为: ${FRONTEND_BUILD_DIR}${NC}"

# 步骤 5: 验证构建
echo ""
echo -e "${YELLOW}✅ 步骤 5/6: 验证构建...${NC}"
if [ -f "$FRONTEND_BUILD_DIR/index.html" ]; then
    echo -e "${GREEN}✓ index.html 存在${NC}"
else
    echo -e "${RED}✗ 错误: index.html 不存在（目录: $FRONTEND_BUILD_DIR）${NC}"
    exit 1
fi

if [ -d "$FRONTEND_BUILD_DIR/_next" ]; then
    echo -e "${GREEN}✓ _next 目录存在${NC}"
else
    echo -e "${RED}✗ 错误: _next 目录不存在（目录: $FRONTEND_BUILD_DIR）${NC}"
    exit 1
fi

if [ -d "$FRONTEND_BUILD_DIR/three-editor" ]; then
    echo -e "${GREEN}✓ three-editor 目录存在${NC}"
else
    echo -e "${YELLOW}⚠ 警告: three-editor 目录不存在，3D编辑器可能无法使用${NC}"
fi

LAST_UPDATE=$(stat -c %y "$FRONTEND_BUILD_DIR/index.html" 2>/dev/null || stat -f %Sm "$FRONTEND_BUILD_DIR/index.html" 2>/dev/null)
echo "   最后更新: $LAST_UPDATE"

# 步骤 6: 启动新服务
echo ""
echo -e "${YELLOW}🚀 步骤 6/6: 启动新服务...${NC}"
mkdir -p logs
nohup env FRONTEND_BUILD_DIR="$FRONTEND_BUILD_DIR" python app_new.py > logs/app.log 2>&1 &
NEW_PID=$!
echo "   新进程 PID: $NEW_PID"

# 等待服务启动
echo "   等待服务启动..."
sleep 3

# 健康检查
HEALTH_CHECK=$(curl -s http://localhost:28888/api/health 2>/dev/null || echo "failed")
if echo "$HEALTH_CHECK" | grep -q "healthy"; then
    echo -e "${GREEN}✓ 健康检查通过${NC}"
    echo "   响应: $HEALTH_CHECK"
else
    echo -e "${RED}✗ 健康检查失败${NC}"
    echo "   查看日志: tail -f logs/app.log"
    exit 1
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ 重建部署完成！${NC}"
echo "=========================================="
echo ""
echo "📊 服务信息:"
echo "   - 服务地址: http://YOUR_SERVER_IP:28888"
echo "   - 进程 PID: $NEW_PID"
echo "   - 日志文件: logs/app.log"
echo ""
echo "📝 后续操作:"
echo "   1. 查看日志: tail -f logs/app.log"
echo "   2. 检查状态: ./check_deployment.sh"
echo ""
echo -e "${YELLOW}⚠️  重要提醒:${NC}"
echo "   请通知用户清除浏览器缓存（Ctrl+Shift+R）"
echo ""
