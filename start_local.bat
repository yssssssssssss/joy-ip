@echo off
echo ============================================
echo Joy IP 3D - 本地开发模式
echo ============================================
echo.

REM 备份当前 .env
if exist ".env" (
    copy /Y ".env" ".env.backup" >nul
)

REM 使用本地配置
if exist ".env.local" (
    copy /Y ".env.local" ".env" >nul
    echo [配置] 已切换到本地开发配置
) else (
    echo [警告] .env.local 不存在，使用当前 .env
)

REM 检查前端构建目录
if not exist "frontend_dist\index.html" (
    echo [警告] frontend_dist 目录为空，正在从 frontend/out 复制...
    if exist "frontend\out\index.html" (
        xcopy /E /I /Y "frontend\out\*" "frontend_dist\"
        echo [完成] 前端文件已复制
    ) else (
        echo [错误] 请先构建前端: cd frontend ^&^& npm run build
    )
)

echo.
echo 启动本地开发服务...
echo 访问地址: http://127.0.0.1:6001
echo.
python app_new.py
pause
