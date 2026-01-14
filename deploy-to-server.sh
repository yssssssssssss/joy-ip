#!/bin/bash
# 智能部署脚本 - 同步本地代码到云端服务器

set -e

# ==========================================
# 配置区域（请修改为你的实际配置）
# ==========================================
SERVER_USER="your_username"
SERVER_HOST="your_server_ip"
SERVER_PATH="/path/to/project"
SERVICE_NAME="your-service"  # systemd服务名或进程名

# ==========================================
# 颜色输出
# ==========================================
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}智能部署脚本 v1.0${NC}"
echo -e "${BLUE}========================================${NC}"

# ==========================================
# 1. 检查本地状态
# ==========================================
echo -e "\n${YELLOW}[1/8] 检查本地Git状态...${NC}"
if [[ -n $(git status -s) ]]; then
    echo -e "${RED}警告: 有未提交的更改${NC}"
    git status -s
    read -p "是否继续部署? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo -e "${GREEN}✓ 本地状态检查完成${NC}"

# ==========================================
# 2. 推送到GitHub
# ==========================================
echo -e "\n${YELLOW}[2/8] 推送到GitHub...${NC}"
CURRENT_BRANCH=$(git branch --show-current)
git push origin $CURRENT_BRANCH
echo -e "${GREEN}✓ 推送成功 (分支: $CURRENT_BRANCH)${NC}"

# ==========================================
# 3. 检查是否需要构建前端
# ==========================================
echo -e "\n${YELLOW}[3/8] 检查前端更新...${NC}"
NEED_BUILD=false

if [ -d "frontend" ]; then
    # 检查frontend/是否有更新
    if git diff --name-only HEAD~1 HEAD | grep -q "^frontend/"; then
        NEED_BUILD=true
        echo -e "${YELLOW}检测到前端代码更新，需要重新构建${NC}"
    else
        echo -e "${GREEN}前端代码无更新，跳过构建${NC}"
    fi
fi

# ==========================================
# 4. 构建前端（如果需要）
# ==========================================
if [ "$NEED_BUILD" = true ]; then
    echo -e "\n${YELLOW}[4/8] 构建前端...${NC}"
    cd frontend
    
    # 检查是否需要安装依赖
    if [ ! -d "node_modules" ]; then
        echo "安装前端依赖..."
        npm install
    fi
    
    npm run build
    npm run export
    cd ..
    echo -e "${GREEN}✓ 前端构建完成${NC}"
else
    echo -e "\n${YELLOW}[4/8] 跳过前端构建${NC}"
fi

# ==========================================
# 5. 服务器备份
# ==========================================
echo -e "\n${YELLOW}[5/8] 服务器备份...${NC}"
BACKUP_NAME="backup-$(date +%Y%m%d-%H%M%S)"
ssh ${SERVER_USER}@${SERVER_HOST} "cd ${SERVER_PATH}/.. && cp -r $(basename ${SERVER_PATH}) ${BACKUP_NAME}"
echo -e "${GREEN}✓ 备份完成: ${BACKUP_NAME}${NC}"

# ==========================================
# 6. 拉取后端代码
# ==========================================
echo -e "\n${YELLOW}[6/8] 更新服务器后端代码...${NC}"
ssh ${SERVER_USER}@${SERVER_HOST} "cd ${SERVER_PATH} && git fetch origin && git reset --hard origin/$CURRENT_BRANCH"
echo -e "${GREEN}✓ 后端代码更新完成${NC}"

# ==========================================
# 7. 上传前端构建产物（如果需要）
# ==========================================
if [ "$NEED_BUILD" = true ] && [ -d "frontend_dist" ]; then
    echo -e "\n${YELLOW}[7/8] 上传前端构建产物...${NC}"
    rsync -av --delete frontend_dist/ ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/frontend_dist/
    echo -e "${GREEN}✓ 前端部署完成${NC}"
else
    echo -e "\n${YELLOW}[7/8] 跳过前端上传${NC}"
fi

# ==========================================
# 8. 重启服务
# ==========================================
echo -e "\n${YELLOW}[8/8] 重启服务...${NC}"

# 尝试使用systemd重启
if ssh ${SERVER_USER}@${SERVER_HOST} "systemctl is-active --quiet ${SERVICE_NAME}"; then
    ssh ${SERVER_USER}@${SERVER_HOST} "sudo systemctl restart ${SERVICE_NAME}"
    echo -e "${GREEN}✓ 服务重启完成 (systemd)${NC}"
else
    # 如果不是systemd服务，尝试杀死进程并重启
    echo -e "${YELLOW}尝试手动重启进程...${NC}"
    ssh ${SERVER_USER}@${SERVER_HOST} "pkill -f app_new.py || true"
    ssh ${SERVER_USER}@${SERVER_HOST} "cd ${SERVER_PATH} && nohup python app_new.py > logs/app.log 2>&1 &"
    echo -e "${GREEN}✓ 服务重启完成 (手动)${NC}"
fi

# ==========================================
# 9. 健康检查
# ==========================================
echo -e "\n${YELLOW}等待服务启动...${NC}"
sleep 5

echo -e "${YELLOW}执行健康检查...${NC}"
HEALTH_CHECK=$(ssh ${SERVER_USER}@${SERVER_HOST} "curl -s http://localhost:28888/api/health" || echo "failed")

if [[ $HEALTH_CHECK == *"healthy"* ]]; then
    echo -e "${GREEN}✓ 服务健康检查通过${NC}"
else
    echo -e "${RED}✗ 服务健康检查失败${NC}"
    echo -e "${YELLOW}请检查服务器日志: ssh ${SERVER_USER}@${SERVER_HOST} 'tail -f ${SERVER_PATH}/logs/app.log'${NC}"
fi

# ==========================================
# 完成
# ==========================================
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "分支: ${CURRENT_BRANCH}"
echo -e "备份: ${BACKUP_NAME}"
echo -e "前端构建: $([ "$NEED_BUILD" = true ] && echo "是" || echo "否")"
echo -e "${BLUE}========================================${NC}"
