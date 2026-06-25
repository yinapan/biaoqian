@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.."
call "%SCRIPT_DIR%env.bat"

echo ================================
echo  biaoqian - local frontend build
echo ================================
echo [INFO] Project: %PROJECT_NAME%
echo [INFO] URL: %APP_URL%

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH.
    popd
    pause
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm is not installed or not in PATH.
    popd
    pause
    exit /b 1
)

pushd frontend
if not exist node_modules (
    echo [INFO] Installing frontend dependencies...
    call npm install
    if errorlevel 1 (
        popd
        popd
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
)

echo [INFO] Building frontend...
call npm run build
if errorlevel 1 (
    popd
    popd
    echo [ERROR] Frontend build failed.
    pause
    exit /b 1
)
popd

echo [OK] Frontend build finished.
popd
pause
