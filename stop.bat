@echo off
chcp 65001 >nul
echo ================================
echo  美术资产检索工作台 - 停止
echo ================================
docker compose down
echo [OK] 服务已停止。
pause
