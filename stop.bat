@echo off
chcp 65001 >nul
echo ================================
echo  美术标签搜索平台 - 停止
echo ================================
docker compose down
echo [OK] 服务已停止。
pause
