@echo off
chcp 65001 >nul
echo ================================
echo  美术标签搜索平台 - 启动
echo ================================

REM Check Docker Desktop is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop 未运行，请先启动 Docker Desktop。
    pause
    exit /b 1
)

echo [1/3] 启动服务...
docker compose up -d --build
if errorlevel 1 (
    echo [ERROR] Docker Compose 启动失败。
    pause
    exit /b 1
)

echo [2/3] 等待服务就绪...
set RETRIES=0
:health_loop
if %RETRIES% GEQ 24 (
    echo [WARN] 服务未在 120 秒内就绪，请检查 docker compose logs。
    goto :show_ip
)
timeout /t 5 /nobreak >nul
curl -sf http://localhost/api/v1/health >nul 2>&1
if errorlevel 1 (
    set /a RETRIES+=1
    goto :health_loop
)
echo [OK] 服务已就绪。

:show_ip
echo [3/3] 检测内网 IP...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set "IP=%%a"
    goto :found_ip
)
:found_ip
set IP=%IP: =%
echo ================================
echo  访问地址: http://%IP%
echo ================================
pause
