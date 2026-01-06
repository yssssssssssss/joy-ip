@echo off
echo ============================================
echo Joy IP 3D Backend Server
echo ============================================
echo.

REM 检查是否存在 .env 文件
if not exist ".env" (
    echo [警告] .env 文件不存在，使用默认配置
    echo.
)

REM 检查前端构建目录
if not exist "frontend_dist\index.html" (
    echo [警告] frontend_dist 目录为空，正在从 frontend/out 复制...
    if exist "frontend\out\index.html" (
        xcopy /E /I /Y "frontend\out\*" "frontend_dist\"
        echo [完成] 前端文件已复制
    ) else (
        echo [错误] frontend/out 目录也不存在，请先构建前端
        echo 运行: cd frontend ^&^& npm run build
        pause
        exit /b 1
    )
)

echo.
echo 启动后端服务...
echo 访问地址: http://127.0.0.1:28888 (或查看 .env 中的 PORT 配置)
echo.
python app_new.py
pause
