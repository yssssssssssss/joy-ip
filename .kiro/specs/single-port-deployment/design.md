# 设计文档：单端口部署整合

## 概述

本设计文档描述了如何将当前的前后端分离架构（Next.js前端 + Flask后端）整合为单一Flask应用，在单一端口28888上提供完整服务。整合方案包括：

1. 将Next.js应用静态导出为纯HTML/CSS/JS文件
2. 配置Flask应用提供静态文件服务
3. 将所有Next.js API路由迁移到Flask
4. 更新前端代码使用相对路径调用API
5. 保留开发模式的前后端分离能力

整合后的架构将消除对两个端口的依赖，简化部署流程，同时保持开发时的便利性。

## 架构

### 当前架构

```
┌─────────────────┐         ┌─────────────────┐
│   Next.js Dev   │         │   Flask API     │
│   Server        │────────▶│   Server        │
│   Port 3000     │  Proxy  │   Port 6001     │
└─────────────────┘         └─────────────────┘
        │                           │
        │                           │
        ▼                           ▼
   前端页面                    API + 静态文件
   (SSR/CSR)                  (/api/*, /output/*)
```

### 目标架构（生产模式）

```
┌──────────────────────────────────────┐
│      Flask Application               │
│         Port 28888                   │
│                                      │
│  ┌────────────┐  ┌────────────────┐ │
│  │  Static    │  │   API Routes   │ │
│  │  Frontend  │  │   /api/*       │ │
│  │  Files     │  │   /output/*    │ │
│  │  /, /detail│  │   /generated_* │ │
│  └────────────┘  └────────────────┘ │
└──────────────────────────────────────┘
```

### 开发模式架构（保留）

```
┌─────────────────┐         ┌─────────────────┐
│   Next.js Dev   │         │   Flask API     │
│   Server        │────────▶│   Server        │
│   Port 3000     │  Proxy  │   Port 6001     │
└─────────────────┘         └─────────────────┘
   (热重载)                    (API开发)
```

## 组件和接口

### 1. Flask应用核心模块

#### 1.1 静态文件服务模块

**职责：** 提供前端静态文件和生成的图片文件

**接口：**
```python
# 配置静态文件目录
app = Flask(__name__, 
            static_folder='frontend_dist',
            static_url_path='')

# 前端路由处理
@app.route('/')
@app.route('/detail')
@app.route('/joyai')
def serve_frontend():
    """返回前端index.html，支持客户端路由"""
    return send_from_directory(app.static_folder, 'index.html')

# 静态资源路由（已存在）
@app.route('/output/<path:filename>')
def serve_output_file(filename):
    """提供output文件夹中的静态文件"""
    return send_from_directory('output', filename)

@app.route('/generated_images/<path:filename>')
def serve_generated_image(filename):
    """提供generated_images文件夹中的静态文件"""
    return send_from_directory('generated_images', filename)
```

#### 1.2 脚本执行工具模块

**职责：** 安全地执行Python脚本并处理结果

**接口：**
```python
import subprocess
import os
from typing import Dict, List, Tuple

class ScriptExecutor:
    """Python脚本执行器"""
    
    def __init__(self, timeout: int = 120):
        self.timeout = timeout
    
    def run_script(self, script_path: str, args: List[str]) -> Tuple[int, str, str]:
        """
        执行Python脚本
        
        Args:
            script_path: 脚本绝对路径
            args: 脚本参数列表
            
        Returns:
            (返回码, stdout输出, stderr输出)
        """
        pass
    
    def get_new_files(self, directory: str, before_files: List[str]) -> List[str]:
        """
        获取目录中新增的文件
        
        Args:
            directory: 监控目录
            before_files: 执行前的文件列表
            
        Returns:
            新增文件的绝对路径列表
        """
        pass
```

#### 1.3 图片上传模块

**职责：** 处理图片上传到图床的逻辑

**接口：**
```python
class ImageUploader:
    """图片上传器"""
    
    def upload_file(self, file_path: str, custom_name: str = None) -> Dict:
        """
        上传文件到图床
        
        Args:
            file_path: 本地文件路径
            custom_name: 自定义文件名
            
        Returns:
            {'success': bool, 'url': str, 'error': str}
        """
        pass
    
    def upload_multiple(self, file_paths: List[str]) -> List[str]:
        """
        批量上传文件
        
        Returns:
            成功上传的URL列表
        """
        pass
```

#### 1.4 远程文件下载模块

**职责：** 下载远程图片到本地临时目录

**接口：**
```python
class RemoteFileDownloader:
    """远程文件下载器"""
    
    def __init__(self, temp_dir: str = 'generated_images'):
        self.temp_dir = temp_dir
    
    def download(self, url: str) -> str:
        """
        下载远程文件到本地
        
        Args:
            url: 远程文件URL
            
        Returns:
            本地文件绝对路径
            
        Raises:
            DownloadError: 下载失败时抛出
        """
        pass
    
    def is_remote_url(self, path: str) -> bool:
        """判断是否为远程URL"""
        pass
```

### 2. API路由模块

所有API路由将在Flask中实现，保持与原Next.js API相同的接口。

#### 2.1 /api/run-banana

**功能：** 执行banana-background.py脚本，添加背景

**请求：**
```json
{
  "tagImgUrl": "string (URL或相对路径)",
  "backgroundText": "string (背景描述)"
}
```

**响应：**
```json
{
  "success": boolean,
  "message": "string",
  "resultImages": ["string (图片URL)"],
  "uploadedImages": ["string"],
  "localImages": ["string"],
  "newFiles": ["string"],
  "stdout": "string",
  "stderr": "string"
}
```

**实现逻辑：**
1. 验证参数
2. 处理输入图片路径（远程URL需下载到本地）
3. 记录执行前的文件列表
4. 执行banana-background.py脚本
5. 检测新生成的文件
6. 尝试上传到图床，失败则返回本地路径
7. 返回结果

#### 2.2 /api/run-jimeng4

**功能：** 执行background-jimeng4.py脚本，使用即梦API添加背景

**请求/响应：** 与run-banana相同

**特殊处理：** 如果输入是本地路径，需先上传到图床获取URL，因为即梦API需要远程URL

#### 2.3 /api/run-3d-banana

**功能：** 处理3D渲染图片的生成

**请求：**
```json
{
  "imagePath": "string (渲染图片路径)",
  "promptText": "string (提示文本)"
}
```

**响应：**
```json
{
  "success": boolean,
  "url": "string (生成的图片URL)"
}
```

#### 2.4 /api/run-banana-pro-img-jd

**功能：** 执行banana-pro-img-jd.py脚本，高级图像处理

**请求：**
```json
{
  "imageUrl": "string",
  "prompt": "string"
}
```

**响应：**
```json
{
  "success": boolean,
  "url": "string"
}
```

#### 2.5 /api/run-turn

**功能：** 执行runninghub-turn.py或liblib-turn.py脚本，处理图像角度变换

**请求：**
```json
{
  "imageUrl": "string",
  "action": "string (角度描述)"
}
```

**响应：**
```json
{
  "success": boolean,
  "url": "string"
}
```

#### 2.6 /api/upload-image

**功能：** 上传图片到图床

**请求：**
```json
{
  "image": "string (图片路径或URL)",
  "customName": "string (可选)"
}
```

**响应：**
```json
{
  "success": boolean,
  "url": "string",
  "error": "string (可选)"
}
```

#### 2.7 /api/save-render

**功能：** 保存3D编辑器渲染的图片（base64）

**请求：**
```json
{
  "dataURL": "string (data:image/png;base64,...)"
}
```

**响应：**
```json
{
  "success": boolean,
  "filePath": "string",
  "url": "string",
  "mime": "string"
}
```

### 3. 前端API客户端模块

**职责：** 统一管理前端API调用

**文件：** `frontend/src/lib/api.ts`

**接口：**
```typescript
// API基础配置
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || ''

// 通用请求函数
async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
  return response.json()
}

// 具体API方法
export const api = {
  startGenerate: (requirement: string) => 
    apiRequest('/api/start-generate', {
      method: 'POST',
      body: JSON.stringify({ requirement }),
    }),
  
  getJobStatus: (jobId: string) =>
    apiRequest(`/api/job/${jobId}/status`),
  
  runBanana: (tagImgUrl: string, backgroundText: string) =>
    apiRequest('/api/run-banana', {
      method: 'POST',
      body: JSON.stringify({ tagImgUrl, backgroundText }),
    }),
  
  // ... 其他API方法
}
```

### 4. 配置管理模块

**文件：** `config.py`

**新增配置项：**
```python
class Config:
    # 前端构建目录
    FRONTEND_BUILD_DIR = os.environ.get('FRONTEND_BUILD_DIR') or 'frontend_dist'
    
    # 单端口模式标志
    SINGLE_PORT_MODE = os.environ.get('SINGLE_PORT_MODE', 'true').lower() == 'true'
    
    # 服务器端口
    PORT = int(os.environ.get('PORT', 28888))
    
    # CORS配置（单端口模式下可禁用）
    CORS_ENABLED = not SINGLE_PORT_MODE
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',') if CORS_ENABLED else []
    
    # 脚本路径配置
    SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # 超时配置
    SCRIPT_TIMEOUT = int(os.environ.get('SCRIPT_TIMEOUT', 120))
```

## 数据模型

### API响应模型

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ScriptExecutionResult:
    """脚本执行结果"""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    new_files: List[str]
    error: Optional[str] = None

@dataclass
class ImageProcessingResult:
    """图像处理结果"""
    success: bool
    result_images: List[str]
    uploaded_images: List[str]
    local_images: List[str]
    message: str
    error: Optional[str] = None
```

## 正确性属性

*属性是系统在所有有效执行中应保持为真的特征或行为——本质上是关于系统应该做什么的形式化陈述。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。*

### 属性 1：静态文件服务一致性

*对于任何*前端路由路径（/、/detail、/joyai），Flask应用应返回相同的index.html文件，以支持客户端路由

**验证：需求 1.2, 1.3**

### 属性 2：API接口向后兼容性

*对于任何*现有的API端点，迁移后的Flask实现应接受相同的请求格式并返回相同结构的响应

**验证：需求 10.1, 10.2, 10.3**

### 属性 3：脚本执行超时保护

*对于任何*Python脚本执行，如果执行时间超过配置的超时时间，系统应终止进程并返回超时错误

**验证：需求 2.9, 8.4**

### 属性 4：文件路径转换正确性

*对于任何*相对路径（/output/*, /generated_images/*），系统应正确转换为绝对路径用于文件系统操作

**验证：需求 2.10**

### 属性 5：远程文件下载幂等性

*对于任何*远程URL，多次下载应产生内容相同的本地文件（在文件未变更的情况下）

**验证：需求 2.10**

### 属性 6：图片上传降级策略

*对于任何*图片上传失败的情况，系统应返回本地可访问路径作为降级方案

**验证：需求 2.2, 2.3**

### 属性 7：新文件检测准确性

*对于任何*脚本执行，系统检测到的新文件应该是且仅是执行后新增的文件

**验证：需求 2.2**

### 属性 8：前端API调用路径一致性

*对于任何*前端API调用，在开发模式和生产模式下应使用相同的相对路径

**验证：需求 4.1, 4.5**

### 属性 9：配置环境变量优先级

*对于任何*配置项，环境变量的值应优先于代码中的默认值

**验证：需求 5.3, 5.4**

### 属性 10：静态资源Content-Type正确性

*对于任何*静态文件请求，Flask应根据文件扩展名返回正确的Content-Type响应头

**验证：需求 9.5**

## 错误处理

### 1. 前端构建目录不存在

**场景：** Flask应用启动时，配置的前端构建目录不存在

**处理：**
- 记录警告日志
- 返回友好的错误页面（HTML）
- 提示用户执行前端构建步骤

**实现：**
```python
@app.before_first_request
def check_frontend_build():
    if not os.path.exists(app.static_folder):
        app.logger.warning(f"前端构建目录不存在: {app.static_folder}")
        app.logger.warning("请先执行: cd frontend && npm run build && npm run export")
```

### 2. 脚本执行超时

**场景：** Python脚本执行时间超过配置的超时时间

**处理：**
- 终止子进程
- 返回超时错误响应
- 记录详细日志

**实现：**
```python
try:
    result = subprocess.run(
        ['python', script_path] + args,
        timeout=SCRIPT_TIMEOUT,
        capture_output=True,
        text=True
    )
except subprocess.TimeoutExpired:
    return jsonify({
        'success': False,
        'error': f'脚本执行超时（{SCRIPT_TIMEOUT}秒）'
    }), 200
```

### 3. 远程文件下载失败

**场景：** 下载远程图片时网络错误或文件不存在

**处理：**
- 捕获异常
- 返回详细错误信息
- 不阻塞整个请求流程

**实现：**
```python
try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
except requests.RequestException as e:
    return jsonify({
        'success': False,
        'error': f'下载远程文件失败: {str(e)}'
    }), 200
```

### 4. 图片上传失败降级

**场景：** 上传图片到图床失败

**处理：**
- 不返回错误，而是降级到本地路径
- 在响应中标识使用了降级方案
- 记录上传失败日志

**实现：**
```python
uploaded_urls = []
for file_path in new_files:
    try:
        url = upload_to_imgbed(file_path)
        if url:
            uploaded_urls.append(url)
    except Exception as e:
        app.logger.warning(f"上传失败，使用本地路径: {e}")

# 降级到本地路径
if not uploaded_urls:
    local_urls = [f"/generated_images/{os.path.basename(f)}" for f in new_files]
    return jsonify({
        'success': True,
        'message': '上传失败，已回退到本地路径',
        'resultImages': local_urls,
        'uploadedImages': [],
        'localImages': local_urls
    })
```

### 5. 静态文件不存在

**场景：** 请求的静态文件不存在

**处理：**
- 返回404状态码
- 记录访问日志
- 对于前端路由，返回index.html

**实现：**
```python
@app.errorhandler(404)
def not_found(e):
    # 如果是API请求，返回JSON
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    
    # 如果是前端路由，返回index.html
    if os.path.exists(os.path.join(app.static_folder, 'index.html')):
        return send_from_directory(app.static_folder, 'index.html')
    
    return "404 Not Found", 404
```

### 6. 脚本执行错误

**场景：** Python脚本执行返回非零退出码

**处理：**
- 返回包含stderr输出的错误响应
- 记录完整的stdout和stderr
- 不抛出500错误，而是返回200状态码和success=false

**实现：**
```python
if result.returncode != 0:
    app.logger.error(f"脚本执行失败: {result.stderr}")
    return jsonify({
        'success': False,
        'error': '脚本执行失败',
        'stderr': result.stderr,
        'stdout': result.stdout
    }), 200
```

## 测试策略

### 单元测试

#### 1. 脚本执行器测试
- 测试正常执行流程
- 测试超时处理
- 测试错误输出捕获
- 测试新文件检测

#### 2. 文件下载器测试
- 测试远程URL下载
- 测试下载失败处理
- 测试URL判断逻辑

#### 3. 图片上传器测试
- 测试单文件上传
- 测试批量上传
- 测试上传失败处理

#### 4. API路由测试
- 测试每个API端点的请求/响应
- 测试参数验证
- 测试错误处理

### 集成测试

#### 1. 端到端API测试
- 测试完整的图片生成流程
- 测试脚本执行和文件上传的集成
- 测试降级策略

#### 2. 静态文件服务测试
- 测试前端页面访问
- 测试静态资源加载
- 测试客户端路由

#### 3. 开发/生产模式切换测试
- 测试环境变量配置
- 测试CORS设置
- 测试API基础路径

### 手动测试

#### 1. 前端功能测试
- 测试聊天界面
- 测试图片生成
- 测试详情页面
- 测试3D编辑器

#### 2. 部署验证
- 测试构建流程
- 测试单端口访问
- 测试所有API功能
- 测试静态资源加载

### 性能测试

#### 1. 并发请求测试
- 测试多个用户同时生成图片
- 测试脚本执行的并发安全性
- 测试文件系统操作的并发性能

#### 2. 大文件处理测试
- 测试大图片上传
- 测试大图片下载
- 测试内存使用

## 部署流程

### 开发环境

1. 安装依赖
```bash
# 后端依赖
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
```

2. 启动开发服务器
```bash
# 终端1：启动后端
python app_new.py

# 终端2：启动前端
cd frontend
npm run dev
```

3. 访问应用
- 前端：http://localhost:3000
- 后端API：http://localhost:6001

### 生产环境（单端口部署）

1. 构建前端
```bash
cd frontend
npm run build
npm run export
```

2. 复制前端构建产物
```bash
# 将导出的文件复制到Flask应用目录
cp -r frontend/out ../frontend_dist
```

3. 配置环境变量
```bash
export PORT=28888
export SINGLE_PORT_MODE=true
export FRONTEND_BUILD_DIR=frontend_dist
```

4. 启动Flask应用
```bash
python app_new.py
```

5. 访问应用
- 完整应用：http://your-server:28888

### 使用Gunicorn部署（推荐）

```bash
# 安装Gunicorn
pip install gunicorn

# 启动应用
gunicorn -w 4 -b 0.0.0.0:28888 --timeout 120 app_new:app
```

### 使用Nginx反向代理（可选）

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:28888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 增加超时时间以支持长时间运行的脚本
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }
}
```

## 配置示例

### config.py（新增配置）

```python
class Config:
    # ... 现有配置 ...
    
    # 前端构建目录
    FRONTEND_BUILD_DIR = os.environ.get('FRONTEND_BUILD_DIR') or 'frontend_dist'
    
    # 单端口模式
    SINGLE_PORT_MODE = os.environ.get('SINGLE_PORT_MODE', 'true').lower() == 'true'
    
    # 服务器配置
    HOST = '0.0.0.0'
    PORT = int(os.environ.get('PORT', 28888))
    
    # CORS配置
    CORS_ENABLED = not SINGLE_PORT_MODE
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',') if CORS_ENABLED else []
    
    # 脚本超时
    SCRIPT_TIMEOUT = int(os.environ.get('SCRIPT_TIMEOUT', 120))
```

### frontend/next.config.js（更新）

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // 静态导出配置
  output: process.env.NODE_ENV === 'production' ? 'export' : undefined,
  trailingSlash: false,
  
  // 开发模式下的代理配置
  async rewrites() {
    // 仅在开发模式下启用代理
    if (process.env.NODE_ENV === 'development') {
      const backendOrigin = process.env.NEXT_PUBLIC_BACKEND_ORIGIN || 'http://127.0.0.1:6001'
      return [
        {
          source: '/api/:path*',
          destination: `${backendOrigin}/api/:path*`,
        },
        {
          source: '/output/:path*',
          destination: `${backendOrigin}/output/:path*`,
        },
        {
          source: '/generated_images/:path*',
          destination: `${backendOrigin}/generated_images/:path*`,
        },
      ]
    }
    return []
  },
}

module.exports = nextConfig
```

### frontend/package.json（新增脚本）

```json
{
  "scripts": {
    "dev": "next dev -p 3000 -H 0.0.0.0",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "export": "next build && next export -o ../frontend_dist"
  }
}
```

### .env.example（新增）

```bash
# 生产环境配置
PORT=28888
SINGLE_PORT_MODE=true
FRONTEND_BUILD_DIR=frontend_dist
SCRIPT_TIMEOUT=120

# 开发环境配置（前端）
NEXT_PUBLIC_API_BASE=
NEXT_PUBLIC_BACKEND_ORIGIN=http://127.0.0.1:6001
```

## 迁移检查清单

### 后端迁移
- [ ] 配置Flask静态文件服务
- [ ] 实现前端路由处理
- [ ] 创建ScriptExecutor工具类
- [ ] 创建ImageUploader工具类
- [ ] 创建RemoteFileDownloader工具类
- [ ] 实现/api/run-banana端点
- [ ] 实现/api/run-jimeng4端点
- [ ] 实现/api/run-3d-banana端点
- [ ] 实现/api/run-banana-pro-img-jd端点
- [ ] 实现/api/run-turn端点
- [ ] 实现/api/upload-image端点
- [ ] 实现/api/save-render端点
- [ ] 更新config.py配置
- [ ] 添加错误处理
- [ ] 添加日志记录

### 前端迁移
- [ ] 创建API工具模块（api.ts）
- [ ] 更新ChatInterface.tsx使用API工具
- [ ] 更新DetailView.tsx使用API工具
- [ ] 删除Next.js API路由文件
- [ ] 更新next.config.js配置
- [ ] 添加export脚本到package.json
- [ ] 测试开发模式
- [ ] 测试生产构建

### 文档更新
- [ ] 更新DEPLOYMENT.md
- [ ] 更新QUICKSTART.md
- [ ] 更新AGENTS.md
- [ ] 创建.env.example
- [ ] 添加构建脚本说明

### 测试验证
- [ ] 单元测试
- [ ] 集成测试
- [ ] 手动功能测试
- [ ] 性能测试
- [ ] 部署验证
