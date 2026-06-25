@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.."
call "%SCRIPT_DIR%env.bat"
set "DATA_ROOT=..\tag_data_upload"
set "MODELS_JSON_PATH=%DATA_ROOT%\model\merged\model_png_results.json"
set "ANIMATOR_JSON_PATH=%DATA_ROOT%\animation\actions_tags_format.json"
set "EFFECTS_JSON_PATH=%DATA_ROOT%\effect\merged\effect_gif_results.json"
set "ICONS_JSON_PATH=%DATA_ROOT%\ui\icon_png_results.json"
set "HAS_EXPLICIT_SOURCE=0"
set "IMPORT_MODELS=0"
set "IMPORT_ANIMATOR=0"
set "IMPORT_EFFECTS=0"
set "IMPORT_ICONS=0"

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="/models" goto set_models
if /I "%~1"=="--models" goto set_models
if /I "%~1"=="/animator" goto set_animator
if /I "%~1"=="--animator" goto set_animator
if /I "%~1"=="/effects" goto set_effects
if /I "%~1"=="--effects" goto set_effects
if /I "%~1"=="/icons" goto set_icons
if /I "%~1"=="--icons" goto set_icons
echo [ERROR] Unknown argument: %~1
echo Usage: %~nx0 [/models models.json] [/animator animator.json] [/effects effects.json] [/icons icons.json]
popd
pause
exit /b 1

:set_models
if "%~2"=="" goto missing_arg
set "MODELS_JSON_PATH=%~2"
set "HAS_EXPLICIT_SOURCE=1"
set "IMPORT_MODELS=1"
shift
shift
goto parse_args

:set_animator
if "%~2"=="" goto missing_arg
set "ANIMATOR_JSON_PATH=%~2"
set "HAS_EXPLICIT_SOURCE=1"
set "IMPORT_ANIMATOR=1"
shift
shift
goto parse_args

:set_effects
if "%~2"=="" goto missing_arg
set "EFFECTS_JSON_PATH=%~2"
set "HAS_EXPLICIT_SOURCE=1"
set "IMPORT_EFFECTS=1"
shift
shift
goto parse_args

:set_icons
if "%~2"=="" goto missing_arg
set "ICONS_JSON_PATH=%~2"
set "HAS_EXPLICIT_SOURCE=1"
set "IMPORT_ICONS=1"
shift
shift
goto parse_args

:missing_arg
echo [ERROR] Missing value for %~1
popd
pause
exit /b 1

:args_done
if "%HAS_EXPLICIT_SOURCE%"=="0" (
    set "IMPORT_MODELS=1"
    set "IMPORT_ANIMATOR=1"
    set "IMPORT_EFFECTS=1"
    set "IMPORT_ICONS=1"
)

echo ================================
echo  biaoqian - production incremental import
echo ================================
echo [INFO] Upsert import. Duplicate module/path rows are updated.
echo [INFO] Using docker-compose.import.yml to expose PostgreSQL temporarily.
echo [INFO] APP_URL=%APP_URL%
echo [INFO] MODELS_JSON_PATH=%MODELS_JSON_PATH%
echo [INFO] ANIMATOR_JSON_PATH=%ANIMATOR_JSON_PATH%
echo [INFO] EFFECTS_JSON_PATH=%EFFECTS_JSON_PATH%
echo [INFO] ICONS_JSON_PATH=%ICONS_JSON_PATH%
echo [INFO] IMPORT_MODELS=%IMPORT_MODELS%
echo [INFO] IMPORT_ANIMATOR=%IMPORT_ANIMATOR%
echo [INFO] IMPORT_EFFECTS=%IMPORT_EFFECTS%
echo [INFO] IMPORT_ICONS=%IMPORT_ICONS%

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running.
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

echo [1/8] Expose PostgreSQL and Elasticsearch ports...
%COMPOSE_IMPORT% up -d postgres elasticsearch
if errorlevel 1 (
    echo [ERROR] PostgreSQL failed to start.
    popd
    pause
    exit /b 1
)
timeout /t 10 /nobreak >nul

echo [2/8] Import models data...
if "%IMPORT_MODELS%"=="1" (
    if defined MODELS_JSON_PATH (
        python scripts/import_data.py --models-json "%MODELS_JSON_PATH%"
        if errorlevel 1 goto import_failed
    ) else (
        echo [SKIP] Models source not provided. Use /models path.json
    )
) else (
    echo [SKIP] Models source not requested.
)

echo [3/8] Import animator data...
if "%IMPORT_ANIMATOR%"=="1" (
    if exist "%ANIMATOR_JSON_PATH%" (
        python scripts/import_data.py --animator-json "%ANIMATOR_JSON_PATH%"
        if errorlevel 1 goto import_failed
    ) else (
        echo [SKIP] Animator source not found: %ANIMATOR_JSON_PATH%
    )
) else (
    echo [SKIP] Animator source not requested.
)

echo [4/8] Import effects data...
if "%IMPORT_EFFECTS%"=="1" (
    if defined EFFECTS_JSON_PATH (
        python scripts/import_data.py --effects-json "%EFFECTS_JSON_PATH%"
        if errorlevel 1 goto import_failed
    ) else (
        powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Get-ChildItem -LiteralPath . -Recurse -Filter effect_gif_results.json -File | Where-Object { $_.Directory.Name -eq 'data' } | Select-Object -First 1 -ExpandProperty FullName; if($p){ python scripts/import_data.py --effects-json $p; exit $LASTEXITCODE } else { Write-Host '[SKIP] Effects source not found.'; exit 0 }"
        if errorlevel 1 goto import_failed
    )
) else (
    echo [SKIP] Effects source not requested.
)

echo [5/8] Import icons data...
if "%IMPORT_ICONS%"=="1" (
    if exist "%ICONS_JSON_PATH%" (
        python scripts/import_data.py --icons-json "%ICONS_JSON_PATH%"
        if errorlevel 1 goto import_failed
    ) else (
        echo [SKIP] Icons source not found: %ICONS_JSON_PATH%
    )
) else (
    echo [SKIP] Icons source not requested.
)

echo [6/8] Rebuild ES index and refresh dictionary...
python scripts/import_data.py --reindex --backend-url "%APP_URL%"
if errorlevel 1 echo [WARN] ES reindex may have failed. Check output above.

echo [7/8] Verify preview images...
python scripts/import_data.py --verify-previews --backend-url "%APP_URL%"
if errorlevel 1 goto verify_failed

echo [8/8] Restore regular PostgreSQL service config...
%COMPOSE% up -d postgres
timeout /t 5 /nobreak >nul

echo ================================
echo  Incremental import finished
echo ================================
popd
pause
exit /b 0

:import_failed
echo [ERROR] Import failed. Stop here to avoid rebuilding ES with partial data.
%COMPOSE% up -d postgres
popd
pause
exit /b 1

:verify_failed
echo [ERROR] Preview verification failed. Check runtime_data\logs\imports.
%COMPOSE% up -d postgres
popd
pause
exit /b 1
