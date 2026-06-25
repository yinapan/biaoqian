@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.."
call "%SCRIPT_DIR%env.bat"
set "MODELS_JSON_PATH=tag_data_upload\model\merged\model_png_results.json"
set "ANIMATOR_JSON_PATH=tag_data_upload\animation\actions_tags_format.json"
set "EFFECTS_JSON_PATH=tag_data_upload\effect\merged\effect_gif_results.json"
set "ICONS_JSON_PATH=tag_data_upload\ui\icon_png_results.json"
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
echo  biaoqian - production full reimport
echo ================================
echo [INFO] Use this when current data is empty and source files need importing again.
echo [INFO] This script never removes PostgreSQL or Elasticsearch volumes.
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

echo [1/10] Start services...
%COMPOSE% up -d --build
if errorlevel 1 (
    echo [ERROR] Docker Compose failed to start.
    popd
    pause
    exit /b 1
)

echo [2/10] Wait for backend...
set RETRIES=0
:health_loop
if %RETRIES% GEQ 36 (
    echo [WARN] Backend did not become ready within 180 seconds. Import will still be attempted.
    goto open_pg
)
timeout /t 5 /nobreak >nul
curl -sf %APP_URL%/api/v1/health >nul 2>&1
if errorlevel 1 (
    set /a RETRIES+=1
    goto health_loop
)
echo [OK] Backend is ready.

:open_pg
echo [3/10] Expose PostgreSQL and Elasticsearch ports...
%COMPOSE_IMPORT% up -d postgres elasticsearch
if errorlevel 1 (
    echo [ERROR] PostgreSQL failed to start.
    popd
    pause
    exit /b 1
)
timeout /t 10 /nobreak >nul

echo [4/10] Import models data...
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

echo [5/10] Import animator data...
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

echo [6/10] Import effects data...
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

echo [7/10] Import icons data...
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

echo [8/10] Rebuild ES index and refresh dictionary...
python scripts/import_data.py --reindex --backend-url "%APP_URL%"
if errorlevel 1 echo [WARN] ES reindex may have failed. Check output above.

echo [9/10] Verify preview images...
python scripts/import_data.py --verify-previews --backend-url "%APP_URL%"
if errorlevel 1 goto verify_failed

echo [10/10] Restore regular PostgreSQL service config...
%COMPOSE% up -d postgres
timeout /t 5 /nobreak >nul

echo ================================
echo  Full reimport finished
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
