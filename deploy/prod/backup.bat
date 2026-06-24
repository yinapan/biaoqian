@echo off
setlocal enabledelayedexpansion
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.."
call "%SCRIPT_DIR%env.bat"

echo ================================
echo  biaoqian - production database backup
echo ================================

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running.
    popd
    pause
    exit /b 1
)

%COMPOSE% ps --status running | findstr "postgres" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PostgreSQL is not running. Run start.bat first.
    popd
    pause
    exit /b 1
)

if not exist backups mkdir backups
for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do set "DT=%%a"
set "STAMP=%DT:~0,4%-%DT:~4,2%-%DT:~6,2%_%DT:~8,2%%DT:~10,2%"
set "BACKUP_FILE=backups\biaoqian_%STAMP%.sql"

echo [1/2] Export database...
%COMPOSE% exec -T postgres pg_dump -U biaoqiao --clean --if-exists biaoqiao > "%BACKUP_FILE%"
if errorlevel 1 (
    echo [ERROR] Backup failed.
    popd
    pause
    exit /b 1
)

echo [OK] Backup saved: %BACKUP_FILE%
echo [2/2] Keep latest 7 backups...
set COUNT=0
for /f "tokens=*" %%f in ('dir /b /o-d backups\biaoqian_*.sql 2^>nul') do (
    set /a COUNT+=1
    if !COUNT! GTR 7 (
        del "backups\%%f"
        echo Deleted old backup: %%f
    )
)

echo ================================
echo  Backup finished
echo ================================
popd
pause
