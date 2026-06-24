@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.."
call "%SCRIPT_DIR%env.bat"

echo ================================
echo  biaoqian - local start
echo ================================
echo [INFO] Project: %PROJECT_NAME%
echo [INFO] URL: %APP_URL%

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop is not running.
    popd
    pause
    exit /b 1
)

%COMPOSE% up -d --build
if errorlevel 1 (
    echo [ERROR] Docker Compose failed.
    popd
    pause
    exit /b 1
)

set RETRIES=0
:health_loop
if %RETRIES% GEQ 24 (
    echo [WARN] Health check timed out. Check: docker compose -p %PROJECT_NAME% logs
    goto finish
)
timeout /t 5 /nobreak >nul
curl -sf %APP_URL%/api/v1/health >nul 2>&1
if errorlevel 1 (
    set /a RETRIES+=1
    goto health_loop
)
echo [OK] Service is ready.

:finish
echo [INFO] Open: %APP_URL%
popd
pause
