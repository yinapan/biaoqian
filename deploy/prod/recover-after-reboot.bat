@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.."
call "%SCRIPT_DIR%env.bat"

echo ================================
echo  biaoqian - production reboot recovery
echo ================================
echo [INFO] Project: %PROJECT_NAME%
echo [INFO] URL: %APP_URL%
echo [INFO] This script starts existing containers without rebuild.
echo [INFO] It then restarts backend after PostgreSQL and Elasticsearch are healthy.

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running.
    popd
    pause
    exit /b 1
)

echo [1/5] Start existing containers without rebuild...
%COMPOSE% up -d
if errorlevel 1 (
    echo [ERROR] Docker Compose failed.
    popd
    pause
    exit /b 1
)

echo [2/5] Wait for PostgreSQL and Elasticsearch...
set RETRIES=0
:deps_loop
if %RETRIES% GEQ 36 (
    echo [ERROR] Dependency health check timed out.
    %COMPOSE% ps
    popd
    pause
    exit /b 1
)
docker inspect biaoqian-postgres-1 --format "{{.State.Health.Status}}" 2>nul | findstr /I "healthy" >nul
if errorlevel 1 (
    set /a RETRIES+=1
    timeout /t 5 /nobreak >nul
    goto deps_loop
)
docker inspect biaoqian-elasticsearch-1 --format "{{.State.Health.Status}}" 2>nul | findstr /I "healthy" >nul
if errorlevel 1 (
    set /a RETRIES+=1
    timeout /t 5 /nobreak >nul
    goto deps_loop
)
echo [OK] Dependencies are healthy.

echo [3/5] Restart backend after dependencies are ready...
%COMPOSE% restart backend
if errorlevel 1 (
    echo [ERROR] Backend restart failed.
    popd
    pause
    exit /b 1
)

echo [4/5] Wait for application health...
set RETRIES=0
:app_loop
if %RETRIES% GEQ 24 (
    echo [ERROR] Application health check timed out.
    echo [INFO] Backend logs:
    docker compose -p %PROJECT_NAME% logs --tail=200 backend
    popd
    pause
    exit /b 1
)
timeout /t 5 /nobreak >nul
curl -sf %APP_URL%/api/v1/health >nul 2>&1
if errorlevel 1 (
    set /a RETRIES+=1
    goto app_loop
)
echo [OK] Application is healthy.

echo [5/5] Current containers:
%COMPOSE% ps
echo [INFO] Open: %APP_URL%
popd
pause
