@echo off
echo ============================================
echo Joy IP 3D - 云服务器生产模式
echo ============================================
echo.

REM 备份当前 .env
if exist ".env" (
    copy /Y ".env" ".env.backup" >nul
)

REM 使用云服务器配置
if exist ".env.cloud" (
    copy /Y ".env.cloud" ".env" >nul
    echo [配置] 已切换到云服务器配置
)

REM 检查前端构建目录
if not exist "frontend_dist\index.html" (
    echo [错误] frontend_dist 目录为空
    echo 请先构建前端: cd frontend ^&^& npm run build
    echo 然后复制: xcopy /E /I /Y frontend\out\* frontend_dist\
    pause
    exit /b 1
)

echo.
echo 启动生产服务...
echo 访问地址: http://0.0.0.0:28888
echo.
python app_new.py
