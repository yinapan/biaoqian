@echo off
setlocal
chcp 65001 >nul
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.."
call "%SCRIPT_DIR%env.bat"

echo ================================
echo  biaoqian - 正式环境停止
echo ================================
echo [INFO] 仅停止容器，不删除 PostgreSQL / Elasticsearch 数据卷。
%COMPOSE% stop
if errorlevel 1 (
    echo [ERROR] 服务停止失败。
    popd
    pause
    exit /b 1
)
echo [OK] 服务已停止，数据卷保留。
popd
pause
