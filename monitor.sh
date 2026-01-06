#!/bin/bash
# 实时监控脚本 - Joy IP 3D 项目

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 清屏
clear

echo -e "${BLUE}=========================================="
echo "Joy IP 3D 实时监控"
echo -e "==========================================${NC}"
echo ""

# 检查服务状态
echo -e "${YELLOW}📊 服务状态${NC}"
if ps aux | grep -q "[p]ython.*app_new.py"; then
    PID=$(ps aux | grep "[p]ython.*app_new.py" | awk '{print $2}')
    CPU=$(ps aux | grep "[p]ython.*app_new.py" | awk '{print $3}')
    MEM=$(ps aux | grep "[p]ython.*app_new.py" | awk '{print $4}')
    echo -e "   ${GREEN}✓${NC} 服务运行中"
    echo "   PID: $PID"
    echo "   CPU: ${CPU}%"
    echo "   内存: ${MEM}%"
else
    echo -e "   ${RED}✗${NC} 服务未运行"
fi
echo ""

# 日志文件信息
echo -e "${YELLOW}📝 日志文件${NC}"
if [ -f "logs/app.log" ]; then
    LOG_SIZE=$(du -h logs/app.log | cut -f1)
    LOG_LINES=$(wc -l < logs/app.log)
    echo -e "   ${GREEN}✓${NC} logs/app.log"
    echo "   大小: $LOG_SIZE"
    echo "   行数: $LOG_LINES"
else
    echo -e "   ${RED}✗${NC} 日志文件不存在"
fi
echo ""

# 最近的错误
echo -e "${YELLOW}🚨 最近的错误 (最近100行)${NC}"
if [ -f "logs/app.log" ]; then
    ERROR_COUNT=$(tail -100 logs/app.log | grep -ci "error")
    if [ $ERROR_COUNT -gt 0 ]; then
        echo -e "   ${RED}发现 $ERROR_COUNT 个错误${NC}"
        echo ""
        tail -100 logs/app.log | grep -i "error" | tail -5 | sed 's/^/   | /'
    else
        echo -e "   ${GREEN}✓${NC} 无错误"
    fi
else
    echo "   无日志文件"
fi
echo ""

# 最近的请求
echo -e "${YELLOW}📡 最近的请求 (最后10条)${NC}"
if [ -f "logs/app.log" ]; then
    tail -10 logs/app.log | grep "HTTP/1.1" | tail -5 | sed 's/^/   | /'
else
    echo "   无日志文件"
fi
echo ""

echo -e "${BLUE}=========================================="
echo "监控选项"
echo -e "==========================================${NC}"
echo ""
echo "1. 实时查看日志:     tail -f logs/app.log"
echo "2. 查看错误:         grep -i error logs/app.log"
echo "3. 查看最近50行:     tail -50 logs/app.log"
echo "4. 重启服务:         ./deploy.sh"
echo "5. 检查部署状态:     ./check_deployment.sh"
echo ""
echo -e "${YELLOW}提示: 运行 'tail -f logs/app.log' 实时监控日志${NC}"
echo ""
