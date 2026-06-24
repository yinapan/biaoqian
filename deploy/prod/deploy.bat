@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.."
call "%SCRIPT_DIR%env.bat"

echo ================================
echo  biaoqian - production deploy
echo ================================
echo [INFO] Project: %PROJECT_NAME%
echo [INFO] URL: %APP_URL%

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running.
    popd
    pause
    exit /b 1
)

if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [WARN] Created .env from .env.example. Check ADMIN_API_KEY.
    ) else (
        echo [ERROR] Missing .env and .env.example.
        popd
        pause
        exit /b 1
    )
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

echo [2/4] Start Docker services...
%COMPOSE% up -d --build
if errorlevel 1 (
    echo [ERROR] Docker Compose failed.
    popd
    pause
    exit /b 1
)

echo [3/4] Wait for health check...
set RETRIES=0
:health_loop
if %RETRIES% GEQ 36 (
    echo [WARN] Health check timed out. Check: docker compose -p %PROJECT_NAME% logs
    goto done
)
timeout /t 5 /nobreak >nul
curl -sf %APP_URL%/api/v1/health >nul 2>&1
if errorlevel 1 (
    set /a RETRIES+=1
    goto health_loop
)
echo [OK] Service is ready.

:done
echo [4/4] Deploy finished.
echo [INFO] Open: %APP_URL%
popd
pause
