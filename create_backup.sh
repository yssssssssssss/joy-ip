#!/bin/bash

# Joy IP 3D项目备份脚本
# 创建完整的项目zip备份，排除不必要的文件

# 设置备份文件名（包含时间戳）
BACKUP_NAME="joy_ip_3d_backup_$(date +%Y%m%d_%H%M%S).zip"
PROJECT_DIR="."

echo "🚀 开始创建Joy IP 3D项目备份..."
echo "备份文件名: $BACKUP_NAME"

# 创建临时排除文件列表
EXCLUDE_FILE=$(mktemp)

# 定义要排除的文件和目录
cat > "$EXCLUDE_FILE" << 'EOF'
# 临时文件和缓存
__pycache__/*
*.pyc
*.pyo
*.pyd
.Python
*.so
.pytest_cache/*
.coverage
htmlcov/*

# 日志文件
logs/*
*.log
tmp_run_output.txt

# 生成的图片（可选择性备份）
generated_images/*
output/*

# Node.js相关
node_modules/*
.next/*
frontend_dist/*
.npm
.yarn-integrity

# IDE和编辑器文件
.vscode/*
.idea/*
*.swp
*.swo
*~

# 系统文件
.DS_Store
Thumbs.db
desktop.ini

# Git相关
.git/*
.gitignore

# 环境变量文件（包含敏感信息）
.env
.env.local
.env.production

# 压缩文件
*.zip
*.tar.gz
*.rar

# Jupyter Notebook检查点
.ipynb_checkpoints/*

# 临时文件
*.tmp
*.temp
EOF

echo "📁 正在压缩项目文件..."

# 使用zip命令创建备份，排除指定文件
zip -r "$BACKUP_NAME" "$PROJECT_DIR" \
    -x@"$EXCLUDE_FILE" \
    -x "create_backup.sh" \
    -x "$BACKUP_NAME"

# 清理临时文件
rm "$EXCLUDE_FILE"

# 检查备份是否成功创建
if [ -f "$BACKUP_NAME" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_NAME" | cut -f1)
    echo "✅ 备份创建成功！"
    echo "📦 备份文件: $BACKUP_NAME"
    echo "📏 文件大小: $BACKUP_SIZE"
    echo ""
    echo "📋 备份内容概览:"
    echo "   ✓ 源代码文件 (.py, .js, .tsx, .ts)"
    echo "   ✓ 配置文件 (config.py, requirements.txt, package.json)"
    echo "   ✓ 文档文件 (doc/目录下的所有文档)"
    echo "   ✓ 数据文件 (data/目录)"
    echo "   ✓ 前端源码 (frontend/src/)"
    echo "   ✓ 脚本文件 (.sh文件)"
    echo "   ✓ 测试文件 (test_*.py)"
    echo ""
    echo "❌ 已排除的内容:"
    echo "   ✗ 生成的图片 (generated_images/, output/)"
    echo "   ✗ 日志文件 (logs/, *.log)"
    echo "   ✗ 缓存文件 (__pycache__, node_modules/)"
    echo "   ✗ 环境变量文件 (.env)"
    echo "   ✗ IDE配置文件 (.vscode/, .idea/)"
    echo ""
    echo "🔒 安全提醒:"
    echo "   - API密钥等敏感信息已排除"
    echo "   - 请妥善保管备份文件"
    echo "   - 恢复时需要重新配置环境变量"
else
    echo "❌ 备份创建失败！"
    exit 1
fi