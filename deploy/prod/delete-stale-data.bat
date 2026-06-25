@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.."
call "%SCRIPT_DIR%env.bat"
set "MODELS_JSON_PATH=tag_data_upload\model\merged\model_png_results.json"
set "ANIMATOR_JSON_PATH=tag_data_upload\animation\actions_tags_format.json"
set "EFFECTS_JSON_PATH=tag_data_upload\effect\merged\effect_gif_results.json"
set "ICONS_JSON_PATH=tag_data_upload\ui\icon_png_results.json"
set "APPLY_DELETE_STALE=0"

if /I "%~1"=="/apply" set "APPLY_DELETE_STALE=1"
if /I "%~1"=="--apply" set "APPLY_DELETE_STALE=1"
if not "%~2"=="" (
    echo [ERROR] Unknown argument: %~2
    echo Usage: %~nx0 [/apply]
    popd
    pause
    exit /b 1
)

echo ================================
echo  biaoqian - prod delete stale data
echo ================================
echo [INFO] Project: %PROJECT_NAME%
echo [INFO] APP_URL=%APP_URL%
echo [INFO] APPLY_DELETE_STALE=%APPLY_DELETE_STALE%
echo [INFO] Without /apply this is a dry-run only.

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop is not running.
    popd
    pause
    exit /b 1
)

%COMPOSE% ps --status running | findstr "backend" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Backend is not running. Run deploy.bat or start.bat first.
    popd
    pause
    exit /b 1
)

echo [1/4] Expose PostgreSQL and Elasticsearch ports...
%COMPOSE_IMPORT% up -d postgres elasticsearch
if errorlevel 1 (
    echo [ERROR] PostgreSQL failed to start.
    popd
    pause
    exit /b 1
)
timeout /t 10 /nobreak >nul

set "APPLY_ARG="
if "%APPLY_DELETE_STALE%"=="1" set "APPLY_ARG=--apply-delete-stale"

echo [2/4] Compare manifest files with database assets...
python scripts/import_data.py --delete-stale %APPLY_ARG% ^
    --models-json "%MODELS_JSON_PATH%" ^
    --animator-json "%ANIMATOR_JSON_PATH%" ^
    --effects-json "%EFFECTS_JSON_PATH%" ^
    --icons-json "%ICONS_JSON_PATH%" ^
    --backend-url "%APP_URL%"
if errorlevel 1 goto failed

if "%APPLY_DELETE_STALE%"=="1" (
    echo [3/4] Rebuild ES index and refresh dictionary...
    python scripts/import_data.py --reindex --backend-url "%APP_URL%"
    if errorlevel 1 goto failed

    echo [4/4] Verify preview images...
    python scripts/import_data.py --verify-previews --backend-url "%APP_URL%"
    if errorlevel 1 goto failed
) else (
    echo [3/4] Dry-run finished. Re-run with /apply to delete stale rows.
    echo [4/4] No data changed.
)

%COMPOSE% up -d postgres >nul
echo [OK] Delete stale data script finished.
popd
pause
exit /b 0

:failed
echo [ERROR] Delete stale data script failed.
%COMPOSE% up -d postgres >nul
popd
pause
exit /b 1
