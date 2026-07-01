@echo off
setlocal

set "OLD_ROOT=F:\biaoqian"
set "NEW_ROOT=E:\biaoqian"
if not "%~1"=="" set "OLD_ROOT=%~1"
if not "%~2"=="" set "NEW_ROOT=%~2"

echo ================================
echo  biaoqian - migrate to SSD start
echo ================================
echo [INFO] Old root: %OLD_ROOT%
echo [INFO] New root: %NEW_ROOT%
echo [INFO] Docker volumes are kept.

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running.
    pause
    exit /b 1
)

if not exist "%OLD_ROOT%\docker-compose.yml" (
    echo [WARN] Old root compose file not found, skip old service shutdown.
    goto start_new_root
)

echo [1/6] Stop old root containers...
pushd "%OLD_ROOT%"
docker compose -p biaoqian -f docker-compose.yml down
if errorlevel 1 (
    echo [ERROR] Failed to stop old root services.
    popd
    pause
    exit /b 1
)
popd

:start_new_root
if not exist "%NEW_ROOT%\docker-compose.yml" (
    echo [ERROR] New root compose file not found: %NEW_ROOT%\docker-compose.yml
    pause
    exit /b 1
)
if not exist "%NEW_ROOT%\deploy\prod\env.bat" (
    echo [ERROR] New root prod env file not found: %NEW_ROOT%\deploy\prod\env.bat
    pause
    exit /b 1
)

echo [2/6] Start services from new root...
pushd "%NEW_ROOT%"
call "%NEW_ROOT%\deploy\prod\env.bat"
echo [INFO] Project: %PROJECT_NAME%
echo [INFO] URL: %APP_URL%
%COMPOSE% up -d
if errorlevel 1 (
    echo [ERROR] Docker Compose failed.
    popd
    pause
    exit /b 1
)

echo [3/6] Wait for PostgreSQL and Elasticsearch...
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

echo [4/6] Restart backend after dependencies are ready...
%COMPOSE% restart backend
if errorlevel 1 (
    echo [ERROR] Backend restart failed.
    popd
    pause
    exit /b 1
)

echo [5/6] Wait for application health...
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

echo [6/6] Current containers:
%COMPOSE% ps
echo [INFO] Open: %APP_URL%
popd
pause

