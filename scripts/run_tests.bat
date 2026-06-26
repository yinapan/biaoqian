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
docker compose -f docker-compose.test.yml down
exit /b 1
:integration_run
cd backend && set RUN_ID=local && python -m pytest tests/integration/ -v --cov=app --cov-report=term && cd ..
docker compose -f docker-compose.test.yml down
goto end

:e2e
echo === Building frontend ===
cd frontend && npm run build
if %ERRORLEVEL% neq 0 ( echo Frontend build failed & exit /b 1 )
cd ..
echo === Starting fixture environment ===
docker compose -f docker-compose.test.yml up -d --build
echo === Waiting for nginx health (port 18081) ===
for /L %%i in (1,1,30) do (
  curl -sf http://localhost:18081 > nul 2>&1 && goto :e2e_ready
  timeout /t 2 > nul
)
echo Nginx not ready after 60 seconds
docker compose -f docker-compose.test.yml down
exit /b 1
:e2e_ready
echo === Waiting for backend health ===
for /L %%i in (1,1,30) do (
  curl -sf http://localhost:18000/api/v1/health > nul 2>&1 && goto :e2e_run
  timeout /t 2 > nul
)
echo Backend not ready after 60 seconds
docker compose -f docker-compose.test.yml down
exit /b 1
:e2e_run
echo === Seeding fixture data ===
if "%ADMIN_API_KEY%"=="" set ADMIN_API_KEY=test-key-12345
for %%ep in (models animator effects icons) do (
  curl -sf -X POST "http://localhost:18000/api/v1/admin/import-%%ep-json" -H "X-Admin-Key: %ADMIN_API_KEY%" -F "file=@tests/e2e/fixtures/%%ep.fixture.json"
  if %ERRORLEVEL% neq 0 ( echo Seed %%ep failed & docker compose -f docker-compose.test.yml down & exit /b 1 )
)
curl -sf -X POST "http://localhost:18000/api/v1/admin/reindex-es" -H "X-Admin-Key: %ADMIN_API_KEY%"
if %ERRORLEVEL% neq 0 ( echo Reindex failed & docker compose -f docker-compose.test.yml down & exit /b 1 )
echo === Installing Playwright chromium ===
cd tests/e2e && npx playwright install --with-deps chromium
if %ERRORLEVEL% neq 0 ( cd ../.. & docker compose -f docker-compose.test.yml down & exit /b 1 )
echo === Running E2E tests ===
npx playwright test
set E2E_EXIT=%ERRORLEVEL%
cd ../..
docker compose -f docker-compose.test.yml down
exit /b %E2E_EXIT%

:perf
echo === Performance baseline ===
k6 run tests/performance/k6-baseline.js
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
echo === Performance load ===
k6 run tests/performance/k6-load.js
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
goto end

:all
call %0 unit && call %0 integration && call %0 e2e
goto end

:full
call %0 all && call %0 perf
goto end

:end
