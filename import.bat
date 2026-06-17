@echo off
chcp 65001 >nul
echo ================================
echo  美术标签搜索平台 - 数据导入
echo ================================

REM Check Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop 未运行。
    pause
    exit /b 1
)

REM Check services are running
docker compose ps --status running | findstr "backend" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 后端服务未运行，请先执行 start.bat。
    pause
    exit /b 1
)

echo [1/5] 临时开放 PG 端口...
(
    echo services:
    echo   postgres:
    echo     ports: ["5432:5432"]
) > docker-compose.override.yml
docker compose up -d postgres
timeout /t 10 /nobreak >nul

echo [2/5] 导入 Excel 数据...
python scripts/import_data.py --excel "资源标签对照表.xlsx"
if errorlevel 1 (
    echo [WARN] Excel 导入可能失败，请检查输出。
)

echo [3/5] 导入特效数据...
if exist "特效\merged\effects_data.json" (
    python scripts/import_data.py --effects-json "特效\merged\effects_data.json"
) else (
    echo [SKIP] 特效 JSON 文件不存在，跳过。
)

echo [4/5] 重建 ES 索引并刷新词典...
python scripts/import_data.py --reindex
if errorlevel 1 (
    echo [WARN] ES 重建索引可能失败，请检查输出。
)

echo [5/5] 关闭 PG 端口...
del docker-compose.override.yml
docker compose up -d postgres
timeout /t 5 /nobreak >nul

echo ================================
echo  数据导入完成！
echo ================================
pause
