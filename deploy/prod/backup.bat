@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.."
call "%SCRIPT_DIR%env.bat"

echo ================================
echo  biaoqian - 正式环境数据库备份
echo ================================

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker 未运行。
    popd
    pause
    exit /b 1
)

%COMPOSE% ps --status running | findstr "postgres" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PostgreSQL 服务未运行，请先执行 start.bat。
    popd
    pause
    exit /b 1
)

if not exist backups mkdir backups
for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do set "DT=%%a"
set "STAMP=%DT:~0,4%-%DT:~4,2%-%DT:~6,2%_%DT:~8,2%%DT:~10,2%"
set "BACKUP_FILE=backups\biaoqian_%STAMP%.sql"

echo [1/2] 导出数据库...
%COMPOSE% exec -T postgres pg_dump -U biaoqiao --clean --if-exists biaoqiao > "%BACKUP_FILE%"
if errorlevel 1 (
    echo [ERROR] 备份失败。
    popd
    pause
    exit /b 1
)

echo [OK] 备份已保存到 %BACKUP_FILE%
echo [2/2] 清理旧备份，保留最近 7 份...
set COUNT=0
for /f "tokens=*" %%f in ('dir /b /o-d backups\biaoqian_*.sql 2^>nul') do (
    set /a COUNT+=1
    if !COUNT! GTR 7 (
        del "backups\%%f"
        echo   已删除 %%f
    )
)

echo ================================
echo  备份流程结束
echo ================================
popd
pause
