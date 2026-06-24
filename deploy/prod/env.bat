@echo off
set "PROJECT_NAME=biaoqian"
set "APP_URL=https://artsearch.testplus.cn"
set "COMPOSE_FILES=-f docker-compose.yml"
set "COMPOSE=docker compose -p %PROJECT_NAME% %COMPOSE_FILES%"
set "COMPOSE_IMPORT=docker compose -p %PROJECT_NAME% %COMPOSE_FILES% -f docker-compose.import.yml"
