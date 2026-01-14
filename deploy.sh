#!/bin/bash
# 部署脚本 - 将本地代码部署到服务器

set -e  # 遇到错误立即退出

# ==========================================
# 配置区域（根据实际情况修改）
# ==========================================
SERVER_USER="your_username"
SERVER_HOST="your_server_ip"
SERVER_PATH="/path/to/project"
SERVICE_NAME="your-service-name"  # systemd服务名

# ==========================================
# 颜色输出
# ==========================================
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}开始部署流程${NC}"
echo -e "${GREEN}========================================${NC}"

# ==========================================
# 1. 本地检查
# ==========================================
echo -e "\n${YELLOW}[1/6] 检查本地Git状态...${NC}"
if [[ -n $(git status -s) ]]; then
    echo -e "${RED}错误: 有未提交的更改，请先提交${NC}"
    git status -s
    exit 1
fi
echo -e "${GREEN}✓ Git状态正常${NC}"

# ==========================================
# 2. 推送到GitHub
# ==========================================
echo -e "\n${YELLOW}[2/6] 推送到GitHub...${NC}"
git push origin main
echo -e "${GREEN}✓ 推送成功${NC}"

# ==========================================
# 3. 构建前端（如果存在）
# ==========================================
if [ -d "frontend" ]; then
    echo -e "\n${YELLOW}[3/6] 构建前端...${NC}"
    cd frontend
    npm run build
    npm run export
    cd ..
    echo -e "${GREEN}✓ 前端构建完成${NC}"
else
    echo -e "\n${YELLOW}[3/6] 跳过前端构建（目录不存在）${NC}"
fi

# ==========================================
# 4. 服务器备份
# ==========================================
echo -e "\n${YELLOW}[4/6] 服务器备份...${NC}"
ssh ${SERVER_USER}@${SERVER_HOST} "cd ${SERVER_PATH} && cp -r . ../backup-\$(date +%Y%m%d-%H%M%S)"
echo -e "${GREEN}✓ 备份完成${NC}"

# ==========================================
# 5. 部署代码
# ==========================================
echo -e "\n${YELLOW}[5/6] 部署代码到服务器...${NC}"

# 拉取后端代码
ssh ${SERVER_USER}@${SERVER_HOST} "cd ${SERVER_PATH} && git pull origin main"

# 上传前端构建产物
if [ -d "frontend_dist" ]; then
    rsync -av --delete frontend_dist/ ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/frontend_dist/
    echo -e "${GREEN}✓ 前端部署完成${NC}"
fi

echo -e "${GREEN}✓ 代码部署完成${NC}"

# ==========================================
# 6. 重启服务
# ==========================================
echo -e "\n${YELLOW}[6/6] 重启服务...${NC}"
ssh ${SERVER_USER}@${SERVER_HOST} "sudo systemctl restart ${SERVICE_NAME}"
echo -e "${GREEN}✓ 服务重启完成${NC}"

# ==========================================
# 完成
# ==========================================
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}部署成功！${NC}"
echo -e "${GREEN}========================================${NC}"
