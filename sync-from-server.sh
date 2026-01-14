#!/bin/bash
# 从服务器同步代码到本地

set -e

# ==========================================
# 配置区域
# ==========================================
SERVER_USER="your_username"
SERVER_HOST="your_server_ip"
SERVER_PATH="/path/to/project"

# ==========================================
# 颜色输出
# ==========================================
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}从服务器同步代码${NC}"
echo -e "${BLUE}========================================${NC}"

# ==========================================
# 1. 检查本地状态
# ==========================================
echo -e "\n${YELLOW}[1/5] 检查本地状态...${NC}"
if [[ -n $(git status -s) ]]; then
    echo -e "${RED}警告: 本地有未提交的更改${NC}"
    git status -s
    read -p "是否先备份本地更改? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        STASH_NAME="本地备份-$(date +%Y%m%d-%H%M%S)"
        git stash save "$STASH_NAME"
        echo -e "${GREEN}✓ 本地更改已暂存: $STASH_NAME${NC}"
    fi
fi

# ==========================================
# 2. 服务器提交更改
# ==========================================
echo -e "\n${YELLOW}[2/5] 在服务器上提交更改...${NC}"
ssh ${SERVER_USER}@${SERVER_HOST} << 'ENDSSH'
cd ${SERVER_PATH}
git add .
if [[ -n $(git status -s) ]]; then
    git commit -m "服务器端修改 - $(date +%Y%m%d-%H%M%S)"
    echo "✓ 服务器更改已提交"
else
    echo "✓ 服务器无更改"
fi
ENDSSH

# ==========================================
# 3. 服务器推送到GitHub
# ==========================================
echo -e "\n${YELLOW}[3/5] 服务器推送到GitHub...${NC}"
ssh ${SERVER_USER}@${SERVER_HOST} "cd ${SERVER_PATH} && git push origin main"
echo -e "${GREEN}✓ 推送完成${NC}"

# ==========================================
# 4. 本地拉取更新
# ==========================================
echo -e "\n${YELLOW}[4/5] 本地拉取更新...${NC}"
git fetch origin main
git merge origin/main
echo -e "${GREEN}✓ 本地代码已更新${NC}"

# ==========================================
# 5. 恢复本地更改（如果有）
# ==========================================
if git stash list | grep -q "本地备份"; then
    echo -e "\n${YELLOW}[5/5] 恢复本地暂存的更改...${NC}"
    read -p "是否恢复之前暂存的本地更改? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git stash pop
        echo -e "${GREEN}✓ 本地更改已恢复${NC}"
    fi
else
    echo -e "\n${YELLOW}[5/5] 无需恢复本地更改${NC}"
fi

# ==========================================
# 完成
# ==========================================
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}同步完成！${NC}"
echo -e "${BLUE}========================================${NC}"
