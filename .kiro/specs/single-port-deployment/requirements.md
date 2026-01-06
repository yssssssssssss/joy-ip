# 需求文档：单端口部署整合

## 简介

本项目当前采用前后端分离架构，前端运行在端口3000（Next.js），后端运行在端口6001（Flask）。由于云服务器仅提供单一可用端口28888，需要将整个应用整合到单一Flask服务中，通过静态文件服务提供前端页面，同时保留所有API功能。

## 术语表

- **Flask应用（Flask Application）**：基于Python Flask框架的后端服务，提供REST API和静态文件服务
- **Next.js应用（Next.js Application）**：基于React和Next.js框架的前端单页应用
- **静态导出（Static Export）**：将Next.js应用编译为纯静态HTML/CSS/JS文件的过程
- **API路由（API Route）**：Next.js中的服务端API处理函数，位于`app/api/`目录
- **Flask路由（Flask Route）**：Flask应用中的HTTP端点处理函数
- **代理重写（Proxy Rewrite）**：Next.js开发模式下将特定路径请求转发到后端服务器的配置
- **CORS（Cross-Origin Resource Sharing）**：跨域资源共享，用于控制不同源之间的HTTP请求
- **相对路径（Relative Path）**：不包含协议和域名的URL路径，如`/api/generate`
- **绝对URL（Absolute URL）**：包含完整协议、域名和路径的URL，如`http://127.0.0.1:6001/api/generate`

## 需求

### 需求 1：Flask应用整合前端静态文件

**用户故事：** 作为系统管理员，我希望Flask应用能够同时提供API服务和前端静态文件，以便在单一端口上运行完整应用。

#### 验收标准

1. WHEN Flask应用启动 THEN Flask应用 SHALL 配置静态文件目录指向编译后的前端资源
2. WHEN 用户访问根路径`/` THEN Flask应用 SHALL 返回前端的index.html文件
3. WHEN 用户访问前端路由（如`/detail`） THEN Flask应用 SHALL 返回前端的index.html以支持客户端路由
4. WHEN 用户请求静态资源（JS、CSS、图片） THEN Flask应用 SHALL 从前端构建目录提供这些文件
5. WHERE 前端构建目录不存在 THEN Flask应用 SHALL 记录错误并返回友好提示信息

### 需求 2：迁移Next.js API路由到Flask

**用户故事：** 作为开发者，我希望将所有Next.js API路由迁移到Flask中，以便消除对Next.js服务端功能的依赖。

#### 验收标准

1. WHEN 迁移API路由 THEN 系统 SHALL 在Flask中实现所有现有Next.js API路由的等效功能
2. WHEN 实现`/api/run-banana`端点 THEN Flask应用 SHALL 下载远程图片、执行Python脚本并返回结果
3. WHEN 实现`/api/run-jimeng4`端点 THEN Flask应用 SHALL 执行相应的图像处理脚本并返回生成的图片URL
4. WHEN 实现`/api/run-3d-banana`端点 THEN Flask应用 SHALL 处理3D渲染图片的生成请求
5. WHEN 实现`/api/run-banana-pro-img-jd`端点 THEN Flask应用 SHALL 处理高级图像生成请求
6. WHEN 实现`/api/run-turn`端点 THEN Flask应用 SHALL 处理图像角度变换请求
7. WHEN 实现`/api/upload-image`端点 THEN Flask应用 SHALL 处理图片上传到图床的请求
8. WHEN 实现`/api/save-render`端点 THEN Flask应用 SHALL 保存3D编辑器渲染的图片
9. WHEN API路由执行长时间操作 THEN Flask应用 SHALL 实现适当的超时控制和错误处理
10. WHEN API路由需要执行外部脚本 THEN Flask应用 SHALL 使用subprocess模块安全地调用Python脚本

### 需求 3：配置Next.js静态导出

**用户故事：** 作为开发者，我希望配置Next.js以支持静态导出，以便生成可由Flask提供的纯静态文件。

#### 验收标准

1. WHEN 配置Next.js THEN 系统 SHALL 在next.config.js中设置`output: 'export'`
2. WHEN 执行构建命令 THEN Next.js SHALL 生成静态HTML、CSS和JavaScript文件到指定目录
3. WHEN 静态导出完成 THEN 系统 SHALL 将输出目录设置为`../frontend_dist`或其他配置的位置
4. WHEN Next.js配置包含rewrites THEN 系统 SHALL 移除或条件化这些配置以支持静态导出
5. WHEN 前端代码使用服务端特性 THEN 系统 SHALL 识别并移除或替换这些不兼容的功能

### 需求 4：前端API调用路径更新

**用户故事：** 作为前端开发者，我希望所有API调用使用相对路径，以便在同源部署时无需配置额外的代理。

#### 验收标准

1. WHEN 前端发起API请求 THEN 前端代码 SHALL 使用相对路径（如`/api/generate`）而非绝对URL
2. WHEN 创建API工具函数 THEN 系统 SHALL 在`frontend/src/lib/api.ts`中集中管理API请求逻辑
3. WHEN API工具函数构建请求URL THEN 系统 SHALL 支持通过环境变量`NEXT_PUBLIC_API_BASE`配置API基础路径
4. WHERE 环境变量未设置 THEN API工具函数 SHALL 使用空字符串作为前缀（相对路径）
5. WHEN 更新现有组件 THEN 系统 SHALL 将所有`axios.post`、`axios.get`和`fetch`调用替换为使用API工具函数

### 需求 5：配置管理和环境变量

**用户故事：** 作为系统管理员，我希望通过配置文件和环境变量管理应用设置，以便在不同环境中灵活部署。

#### 验收标准

1. WHEN 配置Flask应用 THEN 系统 SHALL 在config.py中添加`FRONTEND_BUILD_DIR`配置项
2. WHEN 配置Flask应用 THEN 系统 SHALL 在config.py中添加`SINGLE_PORT_MODE`配置项
3. WHEN Flask应用启动 THEN 系统 SHALL 从环境变量读取端口号，默认为28888
4. WHEN 配置CORS THEN 系统 SHALL 通过环境变量`CORS_ORIGINS`配置允许的源
5. WHERE 应用运行在单端口模式 THEN Flask应用 SHALL 禁用或最小化CORS限制（同源访问）
6. WHEN 前端构建时 THEN 系统 SHALL 支持通过`NEXT_PUBLIC_API_BASE`环境变量配置API基础路径

### 需求 6：开发模式支持

**用户故事：** 作为开发者，我希望保留前后端分离的开发模式，以便在开发时享受热重载等便利功能。

#### 验收标准

1. WHEN 在开发模式下运行 THEN 系统 SHALL 支持前端运行在端口3000，后端运行在端口6001
2. WHEN Next.js开发服务器运行 THEN 系统 SHALL 使用rewrites配置代理API请求到后端
3. WHEN 前端代码检测到开发环境 THEN 系统 SHALL 使用`NEXT_PUBLIC_API_BASE`环境变量配置后端地址
4. WHEN 开发者修改前端代码 THEN Next.js开发服务器 SHALL 提供热模块替换功能
5. WHEN 开发者修改后端代码 THEN Flask应用 SHALL 支持自动重载（可选）

### 需求 7：构建和部署流程

**用户故事：** 作为DevOps工程师，我希望有清晰的构建和部署流程文档，以便顺利将应用部署到生产环境。

#### 验收标准

1. WHEN 准备部署 THEN 系统 SHALL 提供构建脚本执行前端静态导出
2. WHEN 执行构建脚本 THEN 系统 SHALL 将前端构建产物复制到Flask应用可访问的目录
3. WHEN 部署到生产环境 THEN 系统 SHALL 提供启动脚本配置环境变量并启动Flask应用
4. WHEN Flask应用启动 THEN 系统 SHALL 验证前端构建目录存在并包含必要文件
5. WHEN 应用运行在生产环境 THEN 系统 SHALL 在单一端口（28888）上提供完整服务
6. WHEN 部署文档更新 THEN 系统 SHALL 在`doc/DEPLOYMENT.md`中记录单端口部署步骤
7. WHEN 快速入门文档更新 THEN 系统 SHALL 在`doc/QUICKSTART.md`中说明开发和生产模式的区别

### 需求 8：错误处理和日志记录

**用户故事：** 作为系统管理员，我希望应用提供完善的错误处理和日志记录，以便快速诊断和解决问题。

#### 验收标准

1. WHEN Flask应用启动失败 THEN 系统 SHALL 记录详细的错误信息到日志
2. WHEN 前端构建目录不存在 THEN Flask应用 SHALL 记录警告并返回友好的错误页面
3. WHEN API请求失败 THEN Flask应用 SHALL 返回包含错误代码和描述的JSON响应
4. WHEN 执行外部脚本超时 THEN Flask应用 SHALL 终止进程并返回超时错误
5. WHEN 文件操作失败 THEN Flask应用 SHALL 捕获异常并记录详细的堆栈跟踪
6. WHEN 应用运行在生产模式 THEN 系统 SHALL 将日志输出到文件而非仅控制台

### 需求 9：静态资源服务

**用户故事：** 作为用户，我希望应用能够正确提供所有静态资源，包括生成的图片和前端资源，以便完整体验应用功能。

#### 验收标准

1. WHEN 用户请求`/output/*`路径 THEN Flask应用 SHALL 从output目录提供文件
2. WHEN 用户请求`/generated_images/*`路径 THEN Flask应用 SHALL 从generated_images目录提供文件
3. WHEN 用户请求前端静态资源 THEN Flask应用 SHALL 从前端构建目录提供文件
4. WHEN 静态文件不存在 THEN Flask应用 SHALL 返回404状态码
5. WHEN 提供静态文件 THEN Flask应用 SHALL 设置适当的Content-Type响应头

### 需求 10：向后兼容性

**用户故事：** 作为API用户，我希望现有的API接口保持兼容，以便无需修改客户端代码即可使用新的单端口部署。

#### 验收标准

1. WHEN 迁移API路由 THEN 系统 SHALL 保持所有现有API端点的路径不变
2. WHEN API接收请求 THEN 系统 SHALL 接受与原有格式相同的请求参数
3. WHEN API返回响应 THEN 系统 SHALL 返回与原有格式相同的响应结构
4. WHEN 客户端使用旧的API调用方式 THEN 系统 SHALL 正常处理请求并返回预期结果
5. WHEN 系统行为发生变化 THEN 系统 SHALL 在文档中明确说明不兼容的变更
