@echo off
setlocal
chcp 65001 >nul
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.."
call "%SCRIPT_DIR%env.bat"

echo ================================
echo  biaoqian - 本地测试启动
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

%COMPOSE% up -d --build
if errorlevel 1 (
    echo [ERROR] Docker Compose 启动失败。
    popd
    pause
    exit /b 1
)

set RETRIES=0
:health_loop
if %RETRIES% GEQ 24 (
    echo [WARN] 服务未在 120 秒内就绪，请检查: docker compose -p %PROJECT_NAME% logs
    goto :finish
)
timeout /t 5 /nobreak >nul
curl -sf %APP_URL%/api/v1/health >nul 2>&1
if errorlevel 1 (
    set /a RETRIES+=1
    goto :health_loop
)
echo [OK] 服务已就绪。

:finish
echo [INFO] 打开: %APP_URL%
popd
pause
