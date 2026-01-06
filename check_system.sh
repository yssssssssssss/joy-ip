#!/bin/bash
# 系统状态检查脚本

echo "================================"
echo "Joy IP 3D 系统状态检查"
echo "================================"
echo ""

# 1. 检查进程
echo "1. 检查应用进程..."
if ps aux | grep -v grep | grep "python app_new.py" > /dev/null; then
    echo "   ✅ 应用正在运行"
    ps aux | grep -v grep | grep "python app_new.py" | awk '{print "   进程 ID: " $2 ", CPU: " $3 "%, 内存: " $4 "%"}'
else
    echo "   ❌ 应用未运行"
fi
echo ""

# 2. 检查端口
echo "2. 检查端口 28888..."
if command -v lsof &> /dev/null; then
    if lsof -i :28888 > /dev/null 2>&1; then
        echo "   ✅ 端口 28888 正在监听"
    else
        echo "   ❌ 端口 28888 未监听"
    fi
elif command -v netstat &> /dev/null; then
    if netstat -tlnp 2>/dev/null | grep ":28888" > /dev/null; then
        echo "   ✅ 端口 28888 正在监听"
    else
        echo "   ❌ 端口 28888 未监听"
    fi
else
    echo "   ⚠️  无法检查端口（lsof 和 netstat 都不可用）"
fi
echo ""

# 3. 检查健康状态
echo "3. 检查 API 健康状态..."
if command -v curl &> /dev/null; then
    response=$(curl -s -w "\n%{http_code}" http://localhost:28888/api/health 2>/dev/null)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ]; then
        echo "   ✅ API 健康检查通过"
        echo "   响应: $body"
    else
        echo "   ❌ API 健康检查失败 (HTTP $http_code)"
    fi
else
    echo "   ⚠️  curl 不可用，无法检查 API"
fi
echo ""

# 4. 检查前端构建
echo "4. 检查前端构建..."
if [ -d "frontend_dist" ]; then
    file_count=$(find frontend_dist -type f | wc -l)
    echo "   ✅ 前端构建目录存在"
    echo "   文件数量: $file_count"
    if [ -f "frontend_dist/index.html" ]; then
        echo "   ✅ index.html 存在"
    else
        echo "   ❌ index.html 不存在"
    fi
else
    echo "   ❌ 前端构建目录不存在"
fi
echo ""

# 5. 检查配置文件
echo "5. 检查配置文件..."
if [ -f ".env" ]; then
    echo "   ✅ .env 文件存在"
else
    echo "   ❌ .env 文件不存在"
fi

if [ -f "config.py" ]; then
    echo "   ✅ config.py 文件存在"
else
    echo "   ❌ config.py 文件不存在"
fi
echo ""

# 6. 检查日志
echo "6. 检查日志文件..."
if [ -f "logs/app_cloud.log" ]; then
    echo "   ✅ 日志文件存在"
    echo "   最后 5 行:"
    tail -5 logs/app_cloud.log 2>/dev/null | sed 's/^/   /'
else
    echo "   ⚠️  日志文件不存在（可能未配置）"
fi
echo ""

# 7. 磁盘空间
echo "7. 检查磁盘空间..."
df -h . | tail -1 | awk '{print "   使用: " $3 " / " $2 " (" $5 ")"}'
echo ""

echo "================================"
echo "检查完成"
echo "================================"
