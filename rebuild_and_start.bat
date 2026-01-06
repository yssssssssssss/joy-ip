@echo off
chcp 65001 >nul
echo ============================================
echo Joy IP 3D - 全量构建与启动脚本
echo ============================================
echo.

REM 1. 环境配置
echo [1/5] 加载环境配置...
if exist ".env.local" (
    copy /Y ".env.local" ".env" >nul
    echo   - 已加载本地配置 (.env.local)
) else (
    echo   - 使用默认配置 (.env)
)

REM 2. 构建前端
echo.
echo [2/5] 正在构建前端项目 (这可能需要几分钟)...
echo --------------------------------------------
cd frontend
call npm run build
if %errorlevel% neq 0 (
    echo.
    echo [错误] 前端构建失败！请检查错误日志。
    cd ..
    pause
    exit /b %errorlevel%
)
cd ..
echo --------------------------------------------

REM 3. 检查构建产物
echo.
echo [3/5] 验证构建产物...
if not exist "frontend\out" (
    echo [警告] 未找到 frontend\out 目录。尝试运行 npm run export...
    cd frontend
    call npm run export
    if %errorlevel% neq 0 (
         REM 忽略 export 错误，有些 next 版本不需要显式 export
         echo [提示] npm run export 返回了错误，但这可能是正常的（取决于 next 版本），继续检查目录...
    )
    cd ..
)

if not exist "frontend\out" (
    echo [错误] 依然未找到构建产物 (frontend\out)。
    echo 请检查 next.config.js 是否包含 output: 'export'。
    pause
    exit /b 1
)

REM 4. 更新分发目录
echo.
echo [4/5] 更新 frontend_dist 目录...
if exist "frontend_dist" (
    rmdir /s /q "frontend_dist"
)
mkdir "frontend_dist"
xcopy /E /I /Q /Y "frontend\out\*" "frontend_dist\" >nul
echo   - 静态文件已更新。

REM 5. 启动后端
echo.
echo [5/5] 启动后端服务...
echo --------------------------------------------
echo 服务启动后，请访问: http://127.0.0.1:6001 (以控制台实际输出为准)
echo --------------------------------------------
python app_new.py

pause
