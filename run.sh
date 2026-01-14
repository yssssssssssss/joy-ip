#!/bin/bash

# Joy IP 3D 图片生成系统 - Linux 启动脚本
# 确保脚本在项目根目录下运行

echo "===================================================="
echo "正在启动 Joy IP 3D 图片生成系统..."
echo "===================================================="

# 1. 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3，请先安装 Python 3.8+"
    exit 1
fi

# 2. 创建并激活虚拟环境 (可选，建议使用)
if [ ! -d "venv" ]; then
    echo "正在创建虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate

# 3. 安装依赖
echo "正在检查/安装依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. 检查配置文件
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "警告: 未找到 .env 文件，正在从 .env.example 创建默认配置..."
        cp .env.example .env
    else
        echo "错误: 未找到 .env 或 .env.example 文件"
        exit 1
    fi
fi

# 5. 确保输出目录存在
mkdir -p output
mkdir -p generated_images
mkdir -p logs

# 6. 启动程序
echo "===================================================="
echo "服务即将启动，监听端口: 28888"
echo "访问地址: http://localhost:28888"
echo "===================================================="

# 使用 nohup 运行或直接运行
# 如果需要后台运行，请取消下面行的注释并注释掉最后一行
# nohup python3 app_new.py > logs/app.log 2>&1 &
python3 app_new.py
