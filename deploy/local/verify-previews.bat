@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.."
call "%SCRIPT_DIR%env.bat"

echo ================================
echo  biaoqian - local verify previews
echo ================================
echo [INFO] Project: %PROJECT_NAME%
echo [INFO] APP_URL=%APP_URL%

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop is not running.
    popd
    pause
    exit /b 1
)

echo [1/2] Expose PostgreSQL for preview verification...
%COMPOSE_IMPORT% up -d postgres
if errorlevel 1 (
    echo [ERROR] Failed to expose PostgreSQL.
    popd
    pause
    exit /b 1
)
timeout /t 5 /nobreak >nul

echo [2/2] Verify preview images...
python scripts/import_data.py --verify-previews --verify-sample-size 20 --backend-url "%APP_URL%"
if errorlevel 1 (
    echo [ERROR] Preview verification failed. Check runtime_data\logs\imports.
    %COMPOSE% up -d postgres >nul
    popd
    pause
    exit /b 1
)

%COMPOSE% up -d postgres >nul
echo [OK] Preview verification passed.
popd
pause
