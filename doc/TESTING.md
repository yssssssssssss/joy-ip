# 测试指南

本文档描述如何在云服务器上测试应用功能。

## 测试前准备

1. 确保所有依赖已安装
2. 配置环境变量
3. 准备测试数据

## 重要说明：云服务器访问

**本项目部署在云服务器上，需要通过公网IP或域名访问。**

### 访问地址说明

- **服务器本地测试：** `http://localhost:28888` 或 `http://127.0.0.1:28888`
- **远程访问（从浏览器）：** `http://YOUR_SERVER_IP:28888` 或 `http://your-domain.com:28888`

### 获取服务器IP地址

```bash
# 查看服务器公网IP
curl ifconfig.me

# 或者
curl ipinfo.io/ip

# 或者查看网络接口
ip addr show
```

### 防火墙配置

确保端口28888已开放：

```bash
# 检查防火墙状态
sudo ufw status

# 开放28888端口
sudo ufw allow 28888/tcp

# 或使用firewalld
sudo firewall-cmd --permanent --add-port=28888/tcp
sudo firewall-cmd --reload
```

### 云服务商安全组配置

如果使用云服务器（阿里云、腾讯云、AWS等），需要在控制台配置安全组规则：

1. 登录云服务商控制台
2. 找到安全组设置
3. 添加入站规则：
   - 协议：TCP
   - 端口：28888
   - 源地址：0.0.0.0/0（允许所有IP）或指定IP段

### 测试时的地址替换

在以下所有测试命令中：

- **服务器本地测试：** 使用 `localhost` 或 `127.0.0.1`
- **远程访问测试：** 使用服务器的公网IP，例如 `http://123.45.67.89:28888`

**示例：**
```bash
# 本地测试（在服务器上执行）
curl http://localhost:28888/api/health

# 远程测试（从其他机器执行）
curl http://YOUR_SERVER_IP:28888/api/health
```

## 测试清单

### ✅ 1. 前端构建测试

**目的：** 验证前端可以成功构建为静态文件

**步骤：**

1. 构建前端：
```bash
cd frontend
npm run build
```

2. 导出静态文件：
```bash
npm run export
```

3. 验证输出：
```bash
ls -la ../frontend_dist/
# 应该看到: index.html, _next/, 等文件
```

4. 检查关键文件：
```bash
# 检查index.html存在
test -f ../frontend_dist/index.html && echo "✓ index.html exists"

# 检查静态资源目录
test -d ../frontend_dist/_next && echo "✓ _next directory exists"
```

**预期结果：** 
- 构建成功，无错误
- `frontend_dist/` 目录包含所有必要文件
- `index.html` 文件存在

---

### ✅ 2. 应用启动测试

**目的：** 验证应用正常启动

**步骤：**

1. 确保前端已构建（参考测试1）

2. 配置环境变量：
```bash
export PORT=28888
```

3. 启动应用：
```bash
python app_new.py
```

4. 验证启动信息：
   - 应显示"前端构建目录已找到"
   - 端口应为28888
   - 应显示"Running on http://0.0.0.0:28888"

5. 测试前端访问：
```bash
# 测试根路径
curl -I http://localhost:28888/
# 应返回 200 OK

# 测试其他前端路由
curl -I http://localhost:28888/detail
curl -I http://localhost:28888/joyai
```

6. 测试API访问：
```bash
curl http://localhost:28888/api/health
```

7. 在浏览器中访问 `http://YOUR_SERVER_IP:28888`，验证：
   - 页面正常加载
   - 样式正确显示
   - 可以进行交互

**预期结果：** 
- 应用在28888端口运行
- 前端和API都可访问
- 无错误信息

---

### ✅ 3. API端点测试

**目的：** 验证所有API端点正常工作

**步骤：**

1. 测试健康检查：
```bash
curl http://localhost:28888/api/health
```

2. 测试内容分析：
```bash
curl -X POST http://localhost:28888/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"requirement":"生成一个微笑的香蕉"}'
```

3. 测试异步生成：
```bash
# 启动任务
curl -X POST http://localhost:28888/api/start_generate \
  -H "Content-Type: application/json" \
  -d '{"requirement":"生成一个微笑的香蕉，穿红色衣服"}' \
  | jq .

# 获取job_id后查询状态
curl http://localhost:28888/api/job/<job_id>/status | jq .
```

4. 测试图片上传（如果有测试图片）：
```bash
curl -X POST http://localhost:28888/api/upload-image \
  -H "Content-Type: application/json" \
  -d '{"image":"/path/to/test/image.png","customName":"test_img"}'
```

5. 在浏览器中测试完整流程：
   - 输入需求描述
   - 等待生成
   - 查看结果
   - 点击详情
   - 测试背景添加
   - 测试角度变换

**预期结果：** 
- 所有API返回正确的响应格式
- 错误情况返回适当的错误信息
- 生成流程完整执行

---

### ✅ 4. 错误处理测试

**目的：** 验证各种错误情况的处理

**测试场景：**

1. **前端构建目录不存在：**
```bash
# 临时重命名构建目录
mv frontend_dist frontend_dist_backup
python app_new.py
# 应显示警告信息
mv frontend_dist_backup frontend_dist
```

2. **无效的API请求：**
```bash
# 缺少必需参数
curl -X POST http://localhost:28888/api/analyze \
  -H "Content-Type: application/json" \
  -d '{}'
# 应返回错误信息

# 不存在的API端点
curl http://localhost:28888/api/nonexistent
# 应返回404
```

3. **脚本执行超时：**
```bash
# 设置很短的超时时间
export SCRIPT_TIMEOUT=1
python app_new.py
# 然后测试生成，应该超时
```

4. **404错误：**
```bash
# API路径404
curl http://localhost:28888/api/invalid-endpoint

# 前端路由（应返回index.html）
curl http://localhost:28888/some-random-path
```

**预期结果：** 
- 所有错误都有适当的处理
- 返回友好的错误信息
- 不会导致应用崩溃

---

### ✅ 5. 完整用户流程测试

**目的：** 验证端到端的用户体验

**流程：**

1. **基本生成流程：**
   - 访问首页
   - 输入："生成一个微笑的香蕉，穿红色衣服，手拿气球"
   - 等待生成
   - 验证图片显示

2. **使用预设：**
   - 点击表情预设（如"大笑"）
   - 点击动作预设（如"跳跃"）
   - 点击配饰预设
   - 发送生成
   - 验证结果

3. **详情页功能：**
   - 点击生成的图片
   - 进入详情页
   - 测试下载功能
   - 测试添加背景
   - 测试优化形象
   - 测试角度变换

4. **3D编辑器：**
   - 访问 `/joyai`
   - 调整香蕉姿态
   - 点击渲染
   - 输入需求
   - 生成图片

5. **错误处理：**
   - 输入违规内容
   - 验证错误提示
   - 输入空内容
   - 验证验证提示

**预期结果：** 
- 所有功能正常工作
- 用户体验流畅
- 错误提示清晰

---

## 自动化测试脚本

创建 `test_deployment.sh`：

```bash
#!/bin/bash

echo "=== 云服务器部署测试 ==="

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 测试计数
PASSED=0
FAILED=0

# 测试函数
test_endpoint() {
    local name=$1
    local url=$2
    local expected=$3
    
    echo -n "测试 $name... "
    response=$(curl -s -o /dev/null -w "%{http_code}" $url)
    
    if [ "$response" == "$expected" ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC} (期望: $expected, 实际: $response)"
        ((FAILED++))
    fi
}

# 等待服务启动
echo "等待服务启动..."
sleep 3

# 执行测试
test_endpoint "健康检查" "http://localhost:28888/api/health" "200"
test_endpoint "前端首页" "http://localhost:28888/" "200"
test_endpoint "详情页" "http://localhost:28888/detail" "200"
test_endpoint "3D编辑器" "http://localhost:28888/joyai" "200"
test_endpoint "不存在的API" "http://localhost:28888/api/nonexistent" "404"

# 测试API功能
echo -n "测试内容分析API... "
response=$(curl -s -X POST http://localhost:28888/api/analyze \
    -H "Content-Type: application/json" \
    -d '{"requirement":"测试"}' | jq -r '.compliant')

if [ "$response" != "null" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAILED${NC}"
    ((FAILED++))
fi

# 输出结果
echo ""
echo "=== 测试结果 ==="
echo -e "通过: ${GREEN}$PASSED${NC}"
echo -e "失败: ${RED}$FAILED${NC}"
echo "总计: $((PASSED + FAILED))"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}所有测试通过！${NC}"
    exit 0
else
    echo -e "\n${RED}部分测试失败${NC}"
    exit 1
fi
```

运行测试：

```bash
chmod +x test_deployment.sh
./test_deployment.sh
```

---

## 性能测试

### 并发测试

使用 `ab` (Apache Bench) 测试并发性能：

```bash
# 安装ab
sudo apt-get install apache2-utils

# 测试健康检查端点
ab -n 1000 -c 10 http://localhost:28888/api/health

# 测试前端页面
ab -n 100 -c 5 http://localhost:28888/
```

### 负载测试

使用 `wrk` 进行负载测试：

```bash
# 安装wrk
sudo apt-get install wrk

# 测试API
wrk -t4 -c100 -d30s http://localhost:28888/api/health
```

---

## 测试报告模板

```markdown
# 测试报告

**日期：** YYYY-MM-DD
**测试人员：** [姓名]
**版本：** [版本号]

## 测试环境
- OS: [操作系统]
- Python: [版本]
- Node.js: [版本]
- 服务器IP: [公网IP]

## 测试结果

### 1. 前端构建
- [ ] 构建成功
- [ ] 导出成功
- [ ] 文件完整

### 2. 应用启动
- [ ] 应用启动成功
- [ ] 前端可访问
- [ ] API可访问

### 3. API端点
- [ ] /api/health
- [ ] /api/analyze
- [ ] /api/start_generate
- [ ] /api/job/<id>/status
- [ ] /api/run-banana
- [ ] /api/run-jimeng4
- [ ] /api/upload-image
- [ ] /api/save-render

### 4. 错误处理
- [ ] 前端目录不存在
- [ ] 无效请求
- [ ] 超时处理
- [ ] 404处理

### 5. 用户流程
- [ ] 基本生成
- [ ] 预设使用
- [ ] 详情页功能
- [ ] 3D编辑器
- [ ] 错误提示

## 问题记录

[记录发现的问题]

## 总结

[测试总结]
```

---

## 注意事项

1. **测试顺序：** 按照1 -> 2 -> 3的顺序进行
2. **环境隔离：** 每次测试前确保环境干净
3. **日志检查：** 测试时注意查看日志输出
4. **数据备份：** 测试前备份重要数据
5. **端口冲突：** 确保测试端口未被占用

## 故障排查

如果测试失败，检查：

1. 依赖是否完整安装
2. 环境变量是否正确配置
3. 端口是否被占用
4. 日志文件中的错误信息
5. 文件权限是否正确
6. 防火墙和安全组是否配置正确
