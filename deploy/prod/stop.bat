@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.."
call "%SCRIPT_DIR%env.bat"

echo ================================
echo  biaoqian - production stop
echo ================================
echo [INFO] Stop containers only. Docker volumes are kept.
%COMPOSE% stop
if errorlevel 1 (
    echo [ERROR] Failed to stop services.
    popd
    pause
    exit /b 1
)
echo [OK] Services stopped. Data volumes are kept.
popd
pause
