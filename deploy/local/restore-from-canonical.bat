@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.."
call "%SCRIPT_DIR%env.bat"

echo ================================
echo  biaoqian - local restore from canonical
echo ================================
echo [INFO] Restore DB rows from runtime_data JSONL files.
echo [INFO] This script never removes Docker volumes.
echo [INFO] Using docker-compose.import.yml to expose PostgreSQL temporarily.
echo [INFO] APP_URL=%APP_URL%

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop is not running.
    popd
    pause
    exit /b 1
)

echo [1/6] Start services...
%COMPOSE% up -d --build
if errorlevel 1 (
    echo [ERROR] Docker Compose failed to start.
    popd
    pause
    exit /b 1
)

echo [2/6] Wait for backend...
set RETRIES=0
:health_loop
if %RETRIES% GEQ 36 (
    echo [WARN] Backend did not become ready within 180 seconds. Restore will still be attempted.
    goto open_ports
)
timeout /t 5 /nobreak >nul
curl -sf %APP_URL%/api/v1/health >nul 2>&1
if errorlevel 1 (
    set /a RETRIES+=1
    goto health_loop
)
echo [OK] Backend is ready.

:open_ports
echo [3/6] Expose PostgreSQL and Elasticsearch ports...
%COMPOSE_IMPORT% up -d postgres elasticsearch
if errorlevel 1 (
    echo [ERROR] PostgreSQL or Elasticsearch failed to start.
    popd
    pause
    exit /b 1
)
timeout /t 10 /nobreak >nul

echo [4/6] Restore PostgreSQL rows...
python scripts/import_data.py --from-canonical
if errorlevel 1 goto restore_failed

echo [5/6] Rebuild ES and verify preview images...
python scripts/import_data.py --reindex --verify-previews --backend-url "%APP_URL%"
if errorlevel 1 goto verify_failed

echo [6/6] Restore regular PostgreSQL service config...
%COMPOSE% up -d postgres
timeout /t 5 /nobreak >nul

echo ================================
echo  Restore from canonical finished
echo ================================
popd
pause
exit /b 0

:restore_failed
echo [ERROR] Restore failed. Check runtime_data\logs\imports.
%COMPOSE% up -d postgres
popd
pause
exit /b 1

:verify_failed
echo [ERROR] Reindex or preview verification failed. Check runtime_data\logs\imports.
%COMPOSE% up -d postgres
popd
pause
exit /b 1
