#!/bin/bash

# ============================================
# 环境检查脚本
# ============================================
# 检查当前环境配置是否正确

echo "=== Joy IP 3D 环境检查 ==="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0
WARNING=0

# 检查函数
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNING++))
}

# 1. 检测环境类型
echo "1. 检测环境类型..."
if [ -f .env ]; then
    DEPLOYMENT_ENV=$(grep "^DEPLOYMENT_ENV=" .env | cut -d'=' -f2)
    if [ "$DEPLOYMENT_ENV" == "cloud" ]; then
        echo "   环境类型: 云服务器生产环境"
        IS_CLOUD=true
    elif [ "$DEPLOYMENT_ENV" == "local" ]; then
        echo "   环境类型: 本地开发环境"
        IS_CLOUD=false
    else
        check_warn "未设置DEPLOYMENT_ENV，假定为本地环境"
        IS_CLOUD=false
    fi
else
    check_fail ".env 文件不存在"
    echo ""
    echo "请创建 .env 文件："
    if [ -f .env.cloud.example ]; then
        echo "  云服务器: cp .env.cloud.example .env"
    fi
    if [ -f .env.local.example ]; then
        echo "  本地环境: cp .env.local.example .env"
    fi
    exit 1
fi
echo ""

# 2. 检查Python环境
echo "2. 检查Python环境..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    check_pass "Python已安装: $PYTHON_VERSION"
else
    check_fail "Python未安装"
fi

if python3 -c "import flask" 2>/dev/null; then
    check_pass "Flask已安装"
else
    check_fail "Flask未安装，请运行: pip install -r requirements.txt"
fi
echo ""

# 3. 检查Node.js环境
echo "3. 检查Node.js环境..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    check_pass "Node.js已安装: $NODE_VERSION"
else
    check_fail "Node.js未安装"
fi

if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    check_pass "npm已安装: $NPM_VERSION"
else
    check_fail "npm未安装"
fi

if [ -d frontend/node_modules ]; then
    check_pass "前端依赖已安装"
else
    check_fail "前端依赖未安装，请运行: cd frontend && npm install"
fi
echo ""

# 4. 检查配置文件
echo "4. 检查配置文件..."
if [ -f .env ]; then
    check_pass ".env 文件存在"
    
    # 检查SECRET_KEY
    if grep -q "your-cloud-secret-key-change-this" .env || grep -q "your-secret-key-here" .env; then
        check_warn "SECRET_KEY 使用默认值，建议修改"
    else
        check_pass "SECRET_KEY 已自定义"
    fi
    
    # 检查端口配置
    PORT=$(grep "^PORT=" .env | cut -d'=' -f2)
    if [ -n "$PORT" ]; then
        check_pass "端口配置: $PORT"
    else
        check_warn "未配置PORT"
    fi
else
    check_fail ".env 文件不存在"
fi
echo ""

# 5. 云服务器特定检查
if [ "$IS_CLOUD" = true ]; then
    echo "5. 云服务器特定检查..."
    
    # 检查前端构建
    if [ -d frontend_dist ] && [ -f frontend_dist/index.html ]; then
        check_pass "前端已构建"
    else
        check_fail "前端未构建，请运行: cd frontend && npm run export"
    fi
    
    # 检查防火墙
    if command -v ufw &> /dev/null; then
        if sudo ufw status | grep -q "28888.*ALLOW"; then
            check_pass "UFW防火墙已开放28888端口"
        else
            check_warn "UFW防火墙未开放28888端口，请运行: sudo ufw allow 28888/tcp"
        fi
    elif command -v firewall-cmd &> /dev/null; then
        if sudo firewall-cmd --list-ports | grep -q "28888"; then
            check_pass "firewalld已开放28888端口"
        else
            check_warn "firewalld未开放28888端口，请运行: sudo firewall-cmd --permanent --add-port=28888/tcp"
        fi
    else
        check_warn "未检测到防火墙，请手动确认端口开放"
    fi
    
    # 检查systemd服务
    if [ -f /etc/systemd/system/joy-ip-3d.service ]; then
        check_pass "systemd服务已配置"
        
        if sudo systemctl is-enabled joy-ip-3d &> /dev/null; then
            check_pass "systemd服务已设置自启"
        else
            check_warn "systemd服务未设置自启，请运行: sudo systemctl enable joy-ip-3d"
        fi
    else
        check_warn "systemd服务未配置"
    fi
    
    echo ""
    echo "   云服务器部署提醒："
    echo "   - 确保云服务商安全组已开放28888端口"
    echo "   - 使用 'curl ifconfig.me' 获取公网IP"
    echo "   - 访问地址: http://YOUR_SERVER_IP:28888"
fi

# 6. 本地环境特定检查
if [ "$IS_CLOUD" = false ]; then
    echo "5. 本地环境特定检查..."
    
    # 检查前端配置
    if [ -f frontend/.env.local ]; then
        check_pass "前端配置文件存在"
        
        if grep -q "NEXT_PUBLIC_BACKEND_ORIGIN" frontend/.env.local; then
            BACKEND_ORIGIN=$(grep "^NEXT_PUBLIC_BACKEND_ORIGIN=" frontend/.env.local | cut -d'=' -f2)
            check_pass "后端地址配置: $BACKEND_ORIGIN"
        else
            check_warn "未配置NEXT_PUBLIC_BACKEND_ORIGIN"
        fi
    else
        check_fail "前端配置文件不存在，请运行: cp frontend/.env.local.example frontend/.env.local"
    fi
    
    # 检查开发配置
    if [ -f frontend/next.config.dev.js ]; then
        check_pass "前端开发配置存在"
    else
        check_warn "前端开发配置不存在"
    fi
    
    echo ""
    echo "   本地开发提醒："
    echo "   - 后端端口: 6001"
    echo "   - 前端端口: 3000"
    echo "   - 启动后端: PORT=6001 python app_new.py"
    echo "   - 启动前端: cd frontend && npm run dev:local"
    echo "   - 访问地址: http://localhost:3000"
fi

echo ""

# 7. 检查目录结构
echo "6. 检查目录结构..."
REQUIRED_DIRS=("data" "utils" "frontend" "doc")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        check_pass "目录存在: $dir/"
    else
        check_warn "目录不存在: $dir/"
    fi
done
echo ""

# 8. 检查关键文件
echo "7. 检查关键文件..."
REQUIRED_FILES=("app_new.py" "config.py" "requirements.txt" "frontend/package.json")
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        check_pass "文件存在: $file"
    else
        check_fail "文件不存在: $file"
    fi
done
echo ""

# 9. 检查日志目录
echo "8. 检查日志目录..."
if [ -d logs ]; then
    check_pass "日志目录存在"
else
    check_warn "日志目录不存在，将自动创建"
    mkdir -p logs
fi
echo ""

# 10. 总结
echo "=== 检查结果 ==="
echo -e "通过: ${GREEN}$PASSED${NC}"
echo -e "警告: ${YELLOW}$WARNING${NC}"
echo -e "失败: ${RED}$FAILED${NC}"
echo "总计: $((PASSED + WARNING + FAILED))"
echo ""

if [ $FAILED -eq 0 ] && [ $WARNING -eq 0 ]; then
    echo -e "${GREEN}✓ 环境配置完美！可以开始部署${NC}"
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}⚠ 环境基本正常，但有一些警告需要注意${NC}"
    exit 0
else
    echo -e "${RED}✗ 环境配置有问题，请修复后再部署${NC}"
    exit 1
fi
