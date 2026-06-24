@echo off
setlocal
chcp 65001 >nul
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.."
call "%SCRIPT_DIR%env.bat"
set "EXCEL_PATH=资源标签对照表.xlsx"
set "EFFECTS_JSON_PATH="
set "ICONS_JSON_PATH=icon_png_results\icon_png_results.json"

:parse_args
if "%~1"=="" goto :args_done
if /I "%~1"=="/excel" goto :set_excel
if /I "%~1"=="--excel" goto :set_excel
if /I "%~1"=="/effects" goto :set_effects
if /I "%~1"=="--effects" goto :set_effects
if /I "%~1"=="/icons" goto :set_icons
if /I "%~1"=="--icons" goto :set_icons
echo [ERROR] Unknown argument: %~1
echo Usage: %~nx0 [/excel path.xlsx] [/effects effects.json] [/icons icons.json]
popd
pause
exit /b 1

:set_excel
if "%~2"=="" goto :missing_arg
set "EXCEL_PATH=%~2"
shift
shift
goto :parse_args

:set_effects
if "%~2"=="" goto :missing_arg
set "EFFECTS_JSON_PATH=%~2"
shift
shift
goto :parse_args

:set_icons
if "%~2"=="" goto :missing_arg
set "ICONS_JSON_PATH=%~2"
shift
shift
goto :parse_args

:missing_arg
echo [ERROR] Missing value for %~1
popd
pause
exit /b 1

:args_done
if not defined EFFECTS_JSON_PATH if exist "特效\data\effect_gif_results.json" set "EFFECTS_JSON_PATH=特效\data\effect_gif_results.json"

echo ================================
echo  biaoqian - production full reimport
echo ================================
echo [INFO] Use this when current data is empty and source files need importing again.
echo [INFO] This script never removes PostgreSQL or Elasticsearch volumes.
echo [INFO] Using docker-compose.import.yml to expose PostgreSQL temporarily.
echo [INFO] APP_URL=%APP_URL%
echo [INFO] EXCEL_PATH=%EXCEL_PATH%
echo [INFO] EFFECTS_JSON_PATH=%EFFECTS_JSON_PATH%
echo [INFO] ICONS_JSON_PATH=%ICONS_JSON_PATH%

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running.
    popd
    pause
    exit /b 1
)

echo [1/8] Start services...
%COMPOSE% up -d --build
if errorlevel 1 (
    echo [ERROR] Docker Compose failed to start.
    popd
    pause
    exit /b 1
)

echo [2/8] Wait for backend...
set RETRIES=0
:health_loop
if %RETRIES% GEQ 36 (
    echo [WARN] Backend did not become ready within 180 seconds. Import will still be attempted.
    goto :open_pg
)
timeout /t 5 /nobreak >nul
curl -sf %APP_URL%/api/v1/health >nul 2>&1
if errorlevel 1 (
    set /a RETRIES+=1
    goto :health_loop
)
echo [OK] Backend is ready.

:open_pg
echo [3/8] Expose PostgreSQL port...
%COMPOSE_IMPORT% up -d postgres
if errorlevel 1 (
    echo [ERROR] PostgreSQL failed to start.
    popd
    pause
    exit /b 1
)
timeout /t 10 /nobreak >nul

echo [4/8] Import Excel data...
if exist "%EXCEL_PATH%" (
    python scripts/import_data.py --excel "%EXCEL_PATH%"
    if errorlevel 1 goto :import_failed
) else (
    echo [SKIP] Excel source not found: %EXCEL_PATH%
)

echo [5/8] Import effects data...
if not defined EFFECTS_JSON_PATH goto :skip_effects
if not exist "%EFFECTS_JSON_PATH%" goto :skip_effects
python scripts/import_data.py --effects-json "%EFFECTS_JSON_PATH%"
if errorlevel 1 goto :import_failed
goto :after_effects
:skip_effects
echo [SKIP] Effects source not found: %EFFECTS_JSON_PATH%
:after_effects

echo [6/8] Import icons data...
if exist "%ICONS_JSON_PATH%" (
    python scripts/import_data.py --icons-json "%ICONS_JSON_PATH%"
    if errorlevel 1 goto :import_failed
) else (
    echo [SKIP] Icons source not found: %ICONS_JSON_PATH%
)

echo [7/8] Rebuild ES index and refresh dictionary...
python scripts/import_data.py --reindex --backend-url "%APP_URL%"
if errorlevel 1 echo [WARN] ES reindex may have failed. Check output above.

echo [8/8] Restore regular PostgreSQL service config...
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
popd
pause
exit /b 1
