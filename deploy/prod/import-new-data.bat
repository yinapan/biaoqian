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
if not defined EFFECTS_JSON_PATH if exist "特效\merged\effects_data.json" set "EFFECTS_JSON_PATH=特效\merged\effects_data.json"
if not defined EFFECTS_JSON_PATH if exist "特效\merged\effect_gif_results.json" set "EFFECTS_JSON_PATH=特效\merged\effect_gif_results.json"
if not defined EFFECTS_JSON_PATH if exist "特效\data\effect_gif_results.json" set "EFFECTS_JSON_PATH=特效\data\effect_gif_results.json"

echo ================================
echo  biaoqian - production incremental import
echo ================================
echo [INFO] Upsert import: duplicate module/path rows are updated, not duplicated.
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

%COMPOSE% ps --status running | findstr "backend" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Backend is not running. Run deploy.bat or start.bat first.
    popd
    pause
    exit /b 1
)

echo [1/6] Expose PostgreSQL port...
%COMPOSE_IMPORT% up -d postgres
if errorlevel 1 (
    echo [ERROR] PostgreSQL failed to start.
    popd
    pause
    exit /b 1
)
timeout /t 10 /nobreak >nul

echo [2/6] Import Excel data...
if exist "%EXCEL_PATH%" (
    python scripts/import_data.py --excel "%EXCEL_PATH%"
    if errorlevel 1 goto :import_failed
) else (
    echo [SKIP] Excel source not found: %EXCEL_PATH%
)

echo [3/6] Import effects data...
if not defined EFFECTS_JSON_PATH goto :skip_effects
if not exist "%EFFECTS_JSON_PATH%" goto :skip_effects
python scripts/import_data.py --effects-json "%EFFECTS_JSON_PATH%"
if errorlevel 1 goto :import_failed
goto :after_effects
:skip_effects
echo [SKIP] Effects source not found: %EFFECTS_JSON_PATH%
:after_effects

echo [4/6] Import icons data...
if exist "%ICONS_JSON_PATH%" (
    python scripts/import_data.py --icons-json "%ICONS_JSON_PATH%"
    if errorlevel 1 goto :import_failed
) else (
    echo [SKIP] Icons source not found: %ICONS_JSON_PATH%
)

echo [5/6] Rebuild ES index and refresh dictionary...
python scripts/import_data.py --reindex --backend-url "%APP_URL%"
if errorlevel 1 echo [WARN] ES reindex may have failed. Check output above.

echo [6/6] Restore regular PostgreSQL service config...
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
popd
pause
exit /b 1
