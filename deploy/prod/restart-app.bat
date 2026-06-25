@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.."
call "%SCRIPT_DIR%env.bat"

echo ================================
echo  biaoqian - production restart app
echo ================================
echo [INFO] Project: %PROJECT_NAME%
echo [INFO] URL: %APP_URL%
echo [INFO] This script rebuilds frontend/backend and restarts app services only.
echo [INFO] It does not import data, clear DB, or remove Docker volumes.

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running.
    popd
    pause
    exit /b 1
)

echo [1/4] Build frontend...
pushd frontend
if not exist node_modules (
    call npm install
    if errorlevel 1 (
        popd
        popd
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
)
call npm run build
if errorlevel 1 (
    popd
    popd
    echo [ERROR] Frontend build failed.
    pause
    exit /b 1
)
popd

echo [2/4] Rebuild and restart backend/nginx...
%COMPOSE% up -d --build backend nginx
if errorlevel 1 (
    echo [ERROR] Docker Compose failed.
    popd
    pause
    exit /b 1
)

echo [3/4] Wait for health check...
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
echo [4/4] Restart finished.
echo [INFO] Open: %APP_URL%
popd
pause
