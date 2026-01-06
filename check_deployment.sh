#!/bin/bash
# 部署状态检查脚本

echo "=========================================="
echo "Joy IP 3D 部署状态检查"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 检查后端服务
echo "1. 检查后端服务..."
if ps aux | grep -q "[p]ython.*app_new.py"; then
    PID=$(ps aux | grep "[p]ython.*app_new.py" | awk '{print $2}')
    echo -e "   ${GREEN}✓${NC} 后端服务运行中 (PID: $PID)"
else
    echo -e "   ${RED}✗${NC} 后端服务未运行"
fi
echo ""

# 2. 检查端口监听
echo "2. 检查端口 28888..."
if netstat -tuln 2>/dev/null | grep -q ":28888 " || ss -tuln 2>/dev/null | grep -q ":28888 "; then
    echo -e "   ${GREEN}✓${NC} 端口 28888 正在监听"
else
    echo -e "   ${RED}✗${NC} 端口 28888 未监听"
fi
echo ""

# 3. 健康检查
echo "3. API 健康检查..."
HEALTH_RESPONSE=$(curl -s http://127.0.0.1:28888/api/health 2>/dev/null)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "   ${GREEN}✓${NC} API 健康检查通过"
    echo "   响应: $HEALTH_RESPONSE"
else
    echo -e "   ${RED}✗${NC} API 健康检查失败"
    echo "   响应: $HEALTH_RESPONSE"
fi
echo ""

# 4. 检查前端静态文件
echo "4. 检查前端静态文件..."
if [ -f "frontend_dist/index.html" ]; then
    FRONTEND_TIME=$(stat -c %y frontend_dist/index.html 2>/dev/null || stat -f "%Sm" frontend_dist/index.html 2>/dev/null)
    echo -e "   ${GREEN}✓${NC} 前端文件存在"
    echo "   最后更新: $FRONTEND_TIME"
else
    echo -e "   ${RED}✗${NC} 前端文件不存在"
fi
echo ""

# 5. 检查前端源码与构建文件时间差
echo "5. 检查前端文件同步状态..."
if [ -f "frontend/src/components/ChatInterface.tsx" ] && [ -f "frontend_dist/index.html" ]; then
    SOURCE_TIME=$(stat -c %Y frontend/src/components/ChatInterface.tsx 2>/dev/null || stat -f "%m" frontend/src/components/ChatInterface.tsx 2>/dev/null)
    BUILD_TIME=$(stat -c %Y frontend_dist/index.html 2>/dev/null || stat -f "%m" frontend_dist/index.html 2>/dev/null)
    
    if [ "$SOURCE_TIME" -gt "$BUILD_TIME" ]; then
        TIME_DIFF=$((SOURCE_TIME - BUILD_TIME))
        echo -e "   ${YELLOW}⚠${NC} 前端源码比构建文件新 ${TIME_DIFF} 秒"
        echo -e "   ${YELLOW}建议执行: cd frontend && npm run export && cd ..${NC}"
    else
        echo -e "   ${GREEN}✓${NC} 前端文件已同步"
    fi
else
    echo -e "   ${YELLOW}⚠${NC} 无法比较文件时间"
fi
echo ""

# 6. 检查必要目录
echo "6. 检查必要目录..."
DIRS=("output" "generated_images" "data" "logs")
for dir in "${DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "   ${GREEN}✓${NC} $dir/"
    else
        echo -e "   ${RED}✗${NC} $dir/ (不存在)"
    fi
done
echo ""

# 7. 检查环境变量
echo "7. 检查环境配置..."
if [ -f ".env" ]; then
    echo -e "   ${GREEN}✓${NC} .env 文件存在"
    
    # 检查关键配置
    if grep -q "PORT=28888" .env; then
        echo -e "   ${GREEN}✓${NC} PORT=28888"
    else
        echo -e "   ${YELLOW}⚠${NC} PORT 配置可能不正确"
    fi
    
    if grep -q "FRONTEND_BUILD_DIR=frontend_dist" .env; then
        echo -e "   ${GREEN}✓${NC} FRONTEND_BUILD_DIR=frontend_dist"
    else
        echo -e "   ${YELLOW}⚠${NC} FRONTEND_BUILD_DIR 配置可能不正确"
    fi
else
    echo -e "   ${RED}✗${NC} .env 文件不存在"
fi
echo ""

# 8. 检查日志文件
echo "8. 检查日志文件..."
if [ -f "logs/app_cloud.log" ]; then
    LOG_SIZE=$(du -h logs/app_cloud.log | cut -f1)
    LOG_LINES=$(wc -l < logs/app_cloud.log)
    echo -e "   ${GREEN}✓${NC} 日志文件存在"
    echo "   大小: $LOG_SIZE, 行数: $LOG_LINES"
    
    # 显示最后5行日志
    echo ""
    echo "   最近日志:"
    tail -5 logs/app_cloud.log | sed 's/^/   | /'
else
    echo -e "   ${YELLOW}⚠${NC} 日志文件不存在"
fi
echo ""

# 总结
echo "=========================================="
echo "检查完成"
echo "=========================================="
echo ""
echo "快速命令:"
echo "  重新构建前端: cd frontend && npm run export && cd .."
echo "  重启后端: pkill -f 'python.*app_new.py' && python app_new.py &"
echo "  查看日志: tail -f logs/app_cloud.log"
echo "  测试API: python test_start_generate.py"
echo ""
