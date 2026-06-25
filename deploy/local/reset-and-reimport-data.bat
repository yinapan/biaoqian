@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.."
call "%SCRIPT_DIR%env.bat"

echo ================================
echo  biaoqian - local reset and reimport
echo ================================
echo [WARN] This clears imported DB rows: assets, tag_values, import_errors, user_favorites.
echo [WARN] It does not remove Docker volumes or runtime_data preview files.
echo [WARN] It keeps tag definitions and synonyms.
echo.
set /p CONFIRM=Type RESET CONFIRM to continue: 
if not "%CONFIRM%"=="RESET CONFIRM" (
    echo [CANCELLED] Confirmation did not match.
    popd
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop is not running.
    popd
    pause
    exit /b 1
)

echo [1/3] Start services...
%COMPOSE% up -d --build
if errorlevel 1 (
    echo [ERROR] Docker Compose failed to start.
    popd
    pause
    exit /b 1
)

echo [2/3] Expose PostgreSQL and Elasticsearch ports...
%COMPOSE_IMPORT% up -d postgres elasticsearch
if errorlevel 1 (
    echo [ERROR] PostgreSQL failed to start.
    popd
    pause
    exit /b 1
)
timeout /t 10 /nobreak >nul

echo [3/3] Clear imported DB rows...
python scripts/import_data.py --reset-db --backend-url "%APP_URL%"
if errorlevel 1 (
    echo [ERROR] Reset failed. Reimport was not started.
    %COMPOSE% up -d postgres >nul
    popd
    pause
    exit /b 1
)

call "%SCRIPT_DIR%reimport-data.bat"
exit /b %ERRORLEVEL%
