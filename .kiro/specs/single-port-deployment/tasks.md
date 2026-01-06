# 实施计划：单端口部署整合

- [x] 1. 创建工具模块和辅助类
  - 创建脚本执行器、图片上传器、文件下载器等工具类
  - 这些工具类将被多个API路由复用
  - _需求: 2.10_

- [x] 1.1 实现ScriptExecutor工具类
  - 在项目根目录创建`utils/script_executor.py`
  - 实现`run_script()`方法，使用subprocess执行Python脚本
  - 实现超时控制和错误捕获
  - 实现`get_new_files()`方法，检测目录中新增的文件
  - _需求: 2.9, 2.10_

- [x] 1.2 实现ImageUploader工具类
  - 在`utils/image_uploader.py`中创建ImageUploader类
  - 实现`upload_file()`方法，调用upload2imgbed.py脚本
  - 实现`upload_multiple()`方法，批量上传文件
  - 添加错误处理和日志记录
  - _需求: 2.2, 2.3_

- [x] 1.3 实现RemoteFileDownloader工具类
  - 在`utils/remote_downloader.py`中创建RemoteFileDownloader类
  - 实现`download()`方法，使用requests下载远程文件
  - 实现`is_remote_url()`方法，判断是否为远程URL
  - 添加超时和重试机制
  - _需求: 2.2, 2.10_

- [x] 2. 更新配置文件
  - 在config.py中添加单端口部署相关配置
  - _需求: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 2.1 更新config.py添加新配置项
  - 添加`FRONTEND_BUILD_DIR`配置项
  - 添加`SINGLE_PORT_MODE`配置项
  - 更新`PORT`默认值为28888
  - 添加`CORS_ENABLED`配置项
  - 添加`SCRIPT_TIMEOUT`配置项
  - 确保所有配置项支持环境变量覆盖
  - _需求: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 2.2 创建.env.example文件
  - 在项目根目录创建`.env.example`
  - 添加生产环境配置示例
  - 添加开发环境配置示例
  - 添加配置说明注释
  - _需求: 5.3, 5.4, 5.5, 5.6_

- [x] 3. 实现Flask静态文件服务
  - 配置Flask应用提供前端静态文件和支持客户端路由
  - _需求: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 3.1 配置Flask静态文件目录
  - 修改`app_new.py`中的Flask初始化
  - 设置`static_folder`为配置的前端构建目录
  - 设置`static_url_path`为空字符串
  - 添加前端构建目录存在性检查
  - _需求: 1.1, 1.5_

- [x] 3.2 实现前端路由处理
  - 添加`/`、`/detail`、`/joyai`路由
  - 所有前端路由返回index.html
  - 添加404错误处理，区分API请求和前端路由
  - _需求: 1.2, 1.3_

- [x] 3.3 验证静态资源服务
  - 确保`/output/*`和`/generated_images/*`路由正常工作
  - 测试静态文件的Content-Type设置
  - _需求: 1.4, 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 4. 迁移API路由到Flask
  - 将所有Next.js API路由迁移到Flask中
  - _需求: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10_

- [x] 4.1 实现/api/run-banana端点
  - 在`app_new.py`中添加`/api/run-banana`路由
  - 验证请求参数（tagImgUrl, backgroundText）
  - 处理远程URL下载（使用RemoteFileDownloader）
  - 处理相对路径转换为绝对路径
  - 记录执行前的文件列表
  - 使用ScriptExecutor执行banana-background.py
  - 检测新生成的文件
  - 使用ImageUploader上传到图床，失败则返回本地路径
  - 返回符合接口规范的JSON响应
  - _需求: 2.2, 2.9, 2.10, 10.1, 10.2, 10.3_

- [x] 4.2 实现/api/run-jimeng4端点
  - 在`app_new.py`中添加`/api/run-jimeng4`路由
  - 验证请求参数
  - 特殊处理：本地路径需先上传到图床获取URL
  - 使用ScriptExecutor执行background-jimeng4.py
  - 处理结果文件上传和降级
  - 返回JSON响应
  - _需求: 2.3, 2.9, 2.10, 10.1, 10.2, 10.3_

- [x] 4.3 实现/api/run-3d-banana端点
  - 在`app_new.py`中添加`/api/run-3d-banana`路由
  - 验证请求参数（imagePath, promptText）
  - 执行3D-banana-all.py脚本
  - 处理生成的图片
  - 返回JSON响应
  - _需求: 2.4, 10.1, 10.2, 10.3_

- [x] 4.4 实现/api/run-banana-pro-img-jd端点
  - 在`app_new.py`中添加`/api/run-banana-pro-img-jd`路由
  - 验证请求参数（imageUrl, prompt）
  - 下载远程图片（如需要）
  - 执行banana-pro-img-jd.py脚本
  - 处理生成的图片
  - 返回JSON响应
  - _需求: 2.5, 10.1, 10.2, 10.3_

- [x] 4.5 实现/api/run-turn端点
  - 在`app_new.py`中添加`/api/run-turn`路由
  - 验证请求参数（imageUrl, action）
  - 下载远程图片（如需要）
  - 执行runninghub-turn.py或liblib-turn.py脚本
  - 处理生成的图片
  - 返回JSON响应
  - _需求: 2.6, 10.1, 10.2, 10.3_

- [x] 4.6 实现/api/upload-image端点
  - 在`app_new.py`中添加`/api/upload-image`路由
  - 验证请求参数（image, customName）
  - 使用ImageUploader上传图片
  - 返回JSON响应
  - _需求: 2.7, 10.1, 10.2, 10.3_

- [x] 4.7 实现/api/save-render端点
  - 在`app_new.py`中添加`/api/save-render`路由
  - 验证请求参数（dataURL）
  - 解析base64数据
  - 保存到output目录
  - 返回文件路径和URL
  - _需求: 2.8, 10.1, 10.2, 10.3_

- [x] 5. 更新前端配置和代码
  - 配置Next.js支持静态导出，更新API调用方式
  - _需求: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 5.1 更新next.config.js配置
  - 添加`output: 'export'`配置（仅生产环境）
  - 条件化rewrites配置（仅开发环境）
  - 移除不兼容的服务端特性配置
  - 添加环境变量支持
  - _需求: 3.1, 3.2, 3.4, 6.2, 6.3_

- [x] 5.2 创建前端API工具模块
  - 在`frontend/src/lib/api.ts`中创建API客户端
  - 实现`apiRequest()`通用请求函数
  - 支持`NEXT_PUBLIC_API_BASE`环境变量
  - 实现所有API方法（startGenerate, getJobStatus, runBanana等）
  - _需求: 4.2, 4.3, 4.4_

- [x] 5.3 更新ChatInterface.tsx使用API工具
  - 导入api工具模块
  - 替换所有axios调用为api方法调用
  - 移除硬编码的URL
  - 测试功能正常
  - _需求: 4.1, 4.5_

- [x] 5.4 更新DetailView.tsx使用API工具
  - 导入api工具模块
  - 替换所有fetch调用为api方法调用
  - 移除硬编码的URL
  - 测试功能正常
  - _需求: 4.1, 4.5_

- [x] 5.5 删除Next.js API路由文件
  - 删除`frontend/src/app/api/`目录下的所有route.ts文件
  - 确认没有其他代码引用这些文件
  - _需求: 2.1, 3.5_

- [x] 5.6 更新package.json添加export脚本
  - 在scripts中添加`"export": "next build && next export -o ../frontend_dist"`
  - 测试export命令执行成功
  - _需求: 3.2, 7.1, 7.2_

- [x] 6. 添加错误处理和日志
  - 完善错误处理机制和日志记录
  - _需求: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [x] 6.1 添加前端构建目录检查
  - 在Flask应用启动时检查前端构建目录
  - 目录不存在时记录警告并返回友好提示
  - _需求: 1.5, 8.1, 8.2_

- [x] 6.2 完善API错误处理
  - 为所有API路由添加try-except块
  - 返回统一格式的错误响应
  - 记录详细的错误日志和堆栈跟踪
  - _需求: 8.3, 8.5_

- [x] 6.3 添加脚本执行超时处理
  - 在ScriptExecutor中实现超时控制
  - 超时时终止进程并返回错误
  - 记录超时日志
  - _需求: 8.4_

- [x] 6.4 配置生产环境日志
  - 配置日志输出到文件
  - 设置日志级别和格式
  - 添加日志轮转配置
  - _需求: 8.6_

- [x] 7. 更新文档
  - 更新项目文档以反映单端口部署方式
  - _需求: 7.6, 7.7_

- [x] 7.1 更新DEPLOYMENT.md
  - 添加单端口部署章节
  - 说明前端构建和导出步骤
  - 添加Gunicorn部署示例
  - 添加Nginx配置示例
  - _需求: 7.6_

- [x] 7.2 更新QUICKSTART.md
  - 区分开发模式和生产模式
  - 说明环境变量配置
  - 添加单端口部署快速开始指南
  - _需求: 7.7_

- [x] 7.3 更新AGENTS.md
  - 更新构建和测试命令
  - 说明单端口部署的配置要求
  - 更新端口信息
  - _需求: 7.7_

- [ ] 8. 测试和验证
  - 全面测试单端口部署功能
  - _需求: 所有需求_

- [ ] 8.1 测试开发模式
  - 启动后端服务（端口6001）
  - 启动前端开发服务器（端口3000）
  - 测试API代理功能
  - 测试热重载功能
  - _需求: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 8.2 测试前端构建和导出
  - 执行`npm run build`
  - 执行`npm run export`
  - 验证frontend_dist目录生成
  - 检查生成的文件结构
  - _需求: 3.2, 3.3, 7.1, 7.2_

- [ ] 8.3 测试单端口部署
  - 配置环境变量（PORT=28888, SINGLE_PORT_MODE=true）
  - 启动Flask应用
  - 访问根路径验证前端加载
  - 测试所有前端路由（/detail, /joyai）
  - 测试静态资源加载
  - _需求: 1.1, 1.2, 1.3, 1.4, 7.5_

- [ ] 8.4 测试所有API端点
  - 测试/api/start-generate和/api/job/*/status
  - 测试/api/run-banana
  - 测试/api/run-jimeng4
  - 测试/api/run-3d-banana
  - 测试/api/run-banana-pro-img-jd
  - 测试/api/run-turn
  - 测试/api/upload-image
  - 测试/api/save-render
  - 验证响应格式和向后兼容性
  - _需求: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 10.1, 10.2, 10.3, 10.4_

- [ ] 8.5 测试错误处理
  - 测试前端构建目录不存在的情况
  - 测试脚本执行超时
  - 测试远程文件下载失败
  - 测试图片上传失败降级
  - 测试静态文件不存在
  - 测试脚本执行错误
  - _需求: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 8.6 测试完整用户流程
  - 测试聊天界面生成图片
  - 测试详情页面功能
  - 测试3D编辑器功能
  - 测试图片下载功能
  - 测试背景添加功能
  - 测试角度变换功能
  - _需求: 所有需求_

- [ ] 9. 最终检查和优化
  - 确保所有功能正常，准备部署
  - _需求: 所有需求_

- [ ] 9.1 代码审查和清理
  - 移除调试代码和注释
  - 检查代码风格一致性
  - 优化导入语句
  - 添加必要的类型注解

- [ ] 9.2 性能优化
  - 检查并发请求处理
  - 优化文件系统操作
  - 添加必要的缓存
  - 测试内存使用

- [ ] 9.3 安全检查
  - 检查文件路径安全性
  - 验证输入参数
  - 检查CORS配置
  - 确保敏感信息不暴露

- [ ] 9.4 创建部署脚本
  - 创建`deploy.sh`脚本自动化部署流程
  - 包含前端构建、文件复制、服务启动等步骤
  - 添加错误检查和回滚机制
  - _需求: 7.1, 7.2, 7.3, 7.4_

- [ ] 9.5 最终部署验证
  - 在云服务器上执行完整部署流程
  - 验证端口28888可访问
  - 测试所有功能
  - 监控日志和性能
  - _需求: 7.5_
