@echo off
setlocal
chcp 65001 >nul
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.."
call "%SCRIPT_DIR%env.bat"

echo ================================
echo  biaoqian - 本地测试一键部署
echo ================================
echo [INFO] Docker Compose 项目名: %PROJECT_NAME%
echo [INFO] 访问地址: %APP_URL%

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop 未运行，请先启动 Docker Desktop。
    popd
    pause
    exit /b 1
)

if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [WARN] 已从 .env.example 创建 .env，请确认 ADMIN_API_KEY 已改成安全值。
    ) else (
        echo [ERROR] 缺少 .env 和 .env.example。
        popd
        pause
        exit /b 1
    )
)

echo [1/4] 构建前端...
pushd frontend
if not exist node_modules (
    call npm install
    if errorlevel 1 (
        popd
        popd
        echo [ERROR] npm install 失败。
        pause
        exit /b 1
    )
)
call npm run build
if errorlevel 1 (
    popd
    popd
    echo [ERROR] 前端构建失败。
    pause
    exit /b 1
)
popd

echo [2/4] 启动/更新 Docker 服务...
%COMPOSE% up -d --build
if errorlevel 1 (
    echo [ERROR] Docker Compose 启动失败。
    popd
    pause
    exit /b 1
)

echo [3/4] 等待服务健康...
set RETRIES=0
:health_loop
if %RETRIES% GEQ 36 (
    echo [WARN] 服务未在 180 秒内就绪，请检查: docker compose -p %PROJECT_NAME% logs
    goto :done
)
timeout /t 5 /nobreak >nul
curl -sf %APP_URL%/api/v1/health >nul 2>&1
if errorlevel 1 (
    set /a RETRIES+=1
    goto :health_loop
)
echo [OK] 服务已就绪。

:done
echo [4/4] 部署流程结束。
echo [INFO] 打开: %APP_URL%
popd
pause
