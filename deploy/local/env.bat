@echo off
set "PROJECT_NAME=biaoqian_local"
set "APP_URL=http://localhost:8081"
set "COMPOSE_FILES=-f docker-compose.yml -f docker-compose.dev.yml"
set "COMPOSE=docker compose -p %PROJECT_NAME% %COMPOSE_FILES%"
set "COMPOSE_IMPORT=docker compose -p %PROJECT_NAME% %COMPOSE_FILES% -f docker-compose.import.yml"
