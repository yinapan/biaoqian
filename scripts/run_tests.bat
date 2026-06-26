@echo off
setlocal
set TARGET=%1
if "%TARGET%"=="" set TARGET=all

if "%TARGET%"=="unit" goto unit
if "%TARGET%"=="integration" goto integration
if "%TARGET%"=="e2e" goto e2e
if "%TARGET%"=="perf" goto perf
if "%TARGET%"=="all" goto all
if "%TARGET%"=="full" goto full
echo Usage: run_tests.bat [unit^|integration^|e2e^|perf^|all^|full]
exit /b 1

:unit
echo === Frontend unit tests ===&& cd frontend && npm run test:unit && cd ..
echo === Backend unit tests ===&& cd backend && python -m pytest tests/ -k "not integration" && cd ..
goto end

:integration
echo === Starting fixture environment ===
docker compose -f docker-compose.test.yml up -d --build
echo === Waiting for backend health ===
for /L %%i in (1,1,30) do (
  curl -sf http://localhost:18000/api/v1/health > nul 2>&1 && goto :integration_run
  timeout /t 2 > nul
)
echo Backend not ready after 60 seconds
exit /b 1
:integration_run
cd backend && set RUN_ID=local && python -m pytest tests/integration/ -v && cd ..
docker compose -f docker-compose.test.yml down
goto end

:e2e
echo TODO: implement in phase 3
goto end

:perf
echo TODO: implement in phase 4
goto end

:all
call %0 unit && call %0 integration && call %0 e2e
goto end

:full
call %0 all && call %0 perf
goto end

:end
