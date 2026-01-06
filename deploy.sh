#!/bin/bash
# 一键部署脚本 - Joy IP 3D 项目

set -e  # 遇到错误立即退出

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================="
echo "🚀 Joy IP 3D 一键部署"
echo -e "==========================================${NC}"
echo ""

# 1. 构建前端
echo -e "${YELLOW}📦 步骤 1/5: 构建前端...${NC}"
cd frontend
rm -rf .next out node_modules/.cache
npm run export
cd ..
echo -e "${GREEN}✓ 前端构建完成${NC}"
echo ""

# 2. 验证构建
echo -e "${YELLOW}✅ 步骤 2/5: 验证构建...${NC}"
if [ -f "frontend_dist/index.html" ]; then
    BUILD_TIME=$(stat -c %y frontend_dist/index.html 2>/dev/null || stat -f "%Sm" frontend_dist/index.html 2>/dev/null)
    echo -e "${GREEN}✓ 前端文件存在${NC}"
    echo "   最后更新: $BUILD_TIME"
else
    echo -e "${RED}✗ 前端文件不存在！${NC}"
    exit 1
fi
echo ""

# 3. 停止旧服务
echo -e "${YELLOW}🛑 步骤 3/5: 停止旧服务...${NC}"
if ps aux | grep -q "[p]ython.*app_new.py"; then
    OLD_PID=$(ps aux | grep "[p]ython.*app_new.py" | awk '{print $2}')
    echo "   停止进程: $OLD_PID"
    pkill -f 'python.*app_new.py' || true
    sleep 2
    echo -e "${GREEN}✓ 旧服务已停止${NC}"
else
    echo "   没有运行中的服务"
fi
echo ""

# 4. 启动新服务
echo -e "${YELLOW}🚀 步骤 4/5: 启动新服务...${NC}"
nohup python app_new.py > logs/app.log 2>&1 &
NEW_PID=$!
echo "   新进程 PID: $NEW_PID"
echo -e "${GREEN}✓ 新服务已启动${NC}"
echo ""

# 5. 等待服务启动并进行健康检查
echo -e "${YELLOW}🏥 步骤 5/5: 健康检查...${NC}"
echo "   等待服务启动..."
sleep 5

# 尝试健康检查（最多3次）
for i in {1..3}; do
    if curl -f -s http://localhost:28888/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 健康检查通过${NC}"
        HEALTH_RESPONSE=$(curl -s http://localhost:28888/api/health)
        echo "   响应: $HEALTH_RESPONSE"
        break
    else
        if [ $i -eq 3 ]; then
            echo -e "${RED}✗ 健康检查失败！${NC}"
            echo "   请检查日志: tail -f logs/app.log"
            exit 1
        fi
        echo "   重试 $i/3..."
        sleep 3
    fi
done
echo ""

# 部署完成
echo -e "${BLUE}=========================================="
echo -e "${GREEN}✅ 部署完成！${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""
echo "📊 服务信息:"
echo "   - 服务地址: http://YOUR_SERVER_IP:28888"
echo "   - 进程 PID: $NEW_PID"
echo "   - 日志文件: logs/app.log"
echo ""
echo "📝 后续操作:"
echo "   1. 查看日志: tail -f logs/app.log"
echo "   2. 检查状态: ./check_deployment.sh"
echo "   3. 测试 API: python test_start_generate.py"
echo ""
echo -e "${YELLOW}⚠️  重要提醒:${NC}"
echo "   请通知用户清除浏览器缓存（Ctrl+Shift+R）"
echo "   详细指南: cat USER_ACTION_GUIDE.md"
echo ""
