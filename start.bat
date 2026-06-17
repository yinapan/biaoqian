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
del docker-compose.override.yml 2>nul
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
echo ================================
echo  可用的 IPv4 地址:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set "ADDR=%%a"
    call set "ADDR=%%ADDR: =%%"
    call echo   http://%%ADDR%%
)
echo ================================
echo  请使用上方局域网 IP 地址访问
echo  (忽略 172.x 开头的虚拟网卡地址)
echo ================================
pause
