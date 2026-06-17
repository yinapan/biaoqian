# 内网部署 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将美术标签搜索平台从本地开发环境转为公司内网 50+ 人可通过 HTTP 访问的服务

**架构：** 保持现有 Docker Compose 四服务架构不变，关闭数据库端口暴露，增加 Nginx 生产优化（gzip/缓存），添加 bat 管理脚本和主机侧导入脚本

**技术栈：** Docker Compose, Nginx, FastAPI, PostgreSQL 16, Elasticsearch 8 + IK, Windows batch scripts

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `docker-compose.yml` | 修改 | 移除 PG/ES 端口暴露，admin key 改用环境变量，nginx 添加 GIF 挂载 |
| `.gitignore` | 新建 | 项目根目录的 gitignore，排除 .env 等 |
| `.env` | 新建 | 生产环境配置（admin key），不入版本控制 |
| `nginx.conf` | 修改 | 添加 gzip、缓存头、GIF 路由、keepalive |
| `backend/app/routers/health.py` | 新建 | 增强健康检查端点（检查 PG + ES） |
| `backend/app/main.py` | 修改 | 替换内联 health 为 health router |
| `scripts/import_data.py` | 新建 | 主机侧数据导入脚本，直连 PG |
| `start.bat` | 新建 | 一键启动 Docker Compose 并打印内网访问地址 |
| `stop.bat` | 新建 | 一键停止 |
| `import.bat` | 新建 | 数据导入：临时开端口 → 导入 → 关端口 |

---

### 任务 1：安全收紧 — docker-compose.yml + .env + .gitignore

**文件：**
- 修改：`docker-compose.yml`
- 新建：`.gitignore`
- 新建：`.env`

- [ ] **步骤 1：修改 docker-compose.yml — 移除 PG 端口暴露**

删除 postgres 服务中的 `ports: ["5432:5432"]`。

```yaml
# 删除这一行：
    ports: ["5432:5432"]
```

- [ ] **步骤 2：修改 docker-compose.yml — 移除 ES 端口暴露**

删除 elasticsearch 服务中的 `ports: ["9200:9200"]`。

```yaml
# 删除这一行：
    ports: ["9200:9200"]
```

- [ ] **步骤 3：修改 docker-compose.yml — admin key 改用环境变量**

将 backend 服务的 environment 中：
```yaml
      - ADMIN_API_KEY=dev-admin-key-change-in-prod
```
改为：
```yaml
      - ADMIN_API_KEY=${ADMIN_API_KEY:-dev-admin-key-change-in-prod}
```

- [ ] **步骤 4：修改 docker-compose.yml — nginx 添加 GIF 目录挂载**

在 nginx 服务的 volumes 中添加 GIF 挂载：
```yaml
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
      - ./previews:/data/previews:ro
      - ./特效/merged/gifs:/data/gifs:ro    # 新增
```

- [ ] **步骤 5：新建项目根目录 .gitignore**

```gitignore
.env
docker-compose.override.yml
__pycache__/
*.py[cod]
.pytest_cache/
```

- [ ] **步骤 6：生成 .env 文件**

使用 Python 生成随机 32 字符密钥：
```bash
python -c "import secrets; print(f'ADMIN_API_KEY={secrets.token_urlsafe(32)}')" > .env
```

- [ ] **步骤 7：验证 docker-compose 配置有效**

```bash
docker compose config --quiet
```

预期：无输出（表示配置正确）。

- [ ] **步骤 8：Commit**

```bash
git add docker-compose.yml .gitignore
git commit -m "chore: harden docker-compose for internal deployment"
```

注意：`.env` 不入版本控制。

---

### 任务 2：Nginx 生产优化

**文件：**
- 修改：`nginx.conf`

- [ ] **步骤 1：添加 gzip 配置**

在 `server` 块内、第一个 `location` 之前添加：

```nginx
    gzip on;
    gzip_min_length 1000;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript
               text/xml application/xml application/xml+rss text/javascript
               image/svg+xml;
    gzip_vary on;
```

- [ ] **步骤 2：添加 keepalive 配置**

在 gzip 配置之后添加：

```nginx
    keepalive_timeout 65;
    proxy_buffering on;
```

- [ ] **步骤 3：为 Vite 构建产物添加长缓存**

在 `location /` 块之前添加：

```nginx
    location /assets/ {
        root /usr/share/nginx/html;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
```

- [ ] **步骤 4：为预览图添加缓存头**

修改现有的 `/static/previews/` 块，改路径为 `/previews/` 并确认缓存配置：

```nginx
    location /previews/ {
        alias /data/previews/;
        expires 1d;
        add_header Cache-Control "public";
    }
```

注意：当前是 `/static/previews/`，需确认前端实际请求路径后决定是否改名。如果前端请求 `/static/previews/`，则保留原路径名但更新缓存策略：

```nginx
    location /static/previews/ {
        alias /data/previews/;
        expires 1d;
        add_header Cache-Control "public";
    }
```

- [ ] **步骤 5：添加 GIF 静态文件路由**

```nginx
    location /data/gifs/ {
        alias /data/gifs/;
        expires 1d;
        add_header Cache-Control "public";
    }
```

- [ ] **步骤 6：验证 nginx 配置语法**

```bash
docker compose run --rm nginx nginx -t
```

预期：`nginx: the configuration file /etc/nginx/nginx.conf syntax is ok`

- [ ] **步骤 7：Commit**

```bash
git add nginx.conf
git commit -m "perf: optimize nginx with gzip, caching, and GIF route"
```

---

### 任务 3：增强健康检查端点

**文件：**
- 新建：`backend/app/routers/health.py`
- 新建：`backend/tests/test_health.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：编写健康检查测试**

创建 `backend/tests/test_health.py`：

```python
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_health_all_ok():
    """PG and ES both reachable → 200 with status ok."""
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_conn.fetchval = AsyncMock(return_value=1)

    mock_es = AsyncMock()
    mock_es.ping = AsyncMock(return_value=True)

    with patch("app.routers.health.get_pool", return_value=mock_pool), \
         patch("app.routers.health.get_es", return_value=mock_es):
        from app.routers.health import health_check
        response = await health_check()
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_pg_down():
    """PG unreachable → 503."""
    mock_pool = AsyncMock()
    mock_pool.acquire.side_effect = Exception("connection refused")

    mock_es = AsyncMock()
    mock_es.ping = AsyncMock(return_value=True)

    with patch("app.routers.health.get_pool", return_value=mock_pool), \
         patch("app.routers.health.get_es", return_value=mock_es):
        from app.routers.health import health_check
        response = await health_check()
        assert response.status_code == 503


@pytest.mark.asyncio
async def test_health_es_down():
    """ES unreachable → 503."""
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_conn.fetchval = AsyncMock(return_value=1)

    mock_es = AsyncMock()
    mock_es.ping = AsyncMock(return_value=False)

    with patch("app.routers.health.get_pool", return_value=mock_pool), \
         patch("app.routers.health.get_es", return_value=mock_es):
        from app.routers.health import health_check
        response = await health_check()
        assert response.status_code == 503
```

- [ ] **步骤 2：运行测试验证失败**

```bash
cd backend && python -m pytest tests/test_health.py -v
```

预期：FAIL，`ModuleNotFoundError: No module named 'app.routers.health'`

- [ ] **步骤 3：实现 health router**

创建 `backend/app/routers/health.py`：

```python
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models.database import get_pool
from app.services.es_sync_service import get_es

router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
async def health_check():
    pg_ok = False
    es_ok = False

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        pg_ok = True
    except Exception:
        pass

    try:
        es = await get_es()
        es_ok = await es.ping()
    except Exception:
        pass

    status = "ok" if (pg_ok and es_ok) else "error"
    code = 200 if status == "ok" else 503
    return JSONResponse(
        status_code=code,
        content={"status": status, "pg": pg_ok, "es": es_ok},
    )
```

- [ ] **步骤 4：修改 main.py — 替换内联 health**

在 `backend/app/main.py` 中：

1. 在 import 行添加 health：
```python
from app.routers import admin, assets, filter, health, search
```

2. 添加 router 注册：
```python
app.include_router(health.router)
```

3. 删除文件末尾的内联 health 函数：
```python
# 删除以下内容：
@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
```

- [ ] **步骤 5：运行测试验证通过**

```bash
cd backend && python -m pytest tests/test_health.py -v
```

预期：3 tests PASS

- [ ] **步骤 6：Commit**

```bash
git add backend/app/routers/health.py backend/tests/test_health.py backend/app/main.py
git commit -m "feat: enhance health endpoint to check PG and ES connectivity"
```

---

### 任务 4：主机侧导入脚本

**文件：**
- 新建：`scripts/import_data.py`

- [ ] **步骤 1：创建 scripts 目录**

```bash
mkdir -p scripts
```

- [ ] **步骤 2：编写导入脚本**

创建 `scripts/import_data.py`。此脚本从主机直连 PG（localhost:5432），调用 backend 中的 importer 模块：

```python
"""
Host-side data import script.
Connects directly to PostgreSQL at localhost:5432 (requires PG port exposed).
Usage: python scripts/import_data.py [--excel PATH] [--effects-json PATH] [--reindex]
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import asyncpg


async def run_excel_import(excel_path: str, pool: asyncpg.Pool):
    from app.importers.excel_importer import import_excel
    result = await import_excel(excel_path, pool, "previews")
    print(f"Excel import done: {result}")
    return result


async def run_effects_import(json_path: str, pool: asyncpg.Pool):
    from app.importers.effects_importer import import_effects_json
    result = await import_effects_json(json_path, "特效/merged/gifs", pool, "previews")
    print(f"Effects import done: {result}")
    return result


async def call_reindex(admin_key: str, backend_url: str = "http://localhost"):
    import urllib.request
    import json
    req = urllib.request.Request(
        f"{backend_url}/api/v1/admin/reindex-es",
        method="POST",
        headers={"X-Admin-Key": admin_key},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = json.loads(resp.read())
    print(f"Reindex done: {result}")
    return result


async def call_refresh_dict(admin_key: str, backend_url: str = "http://localhost"):
    import urllib.request
    import json
    req = urllib.request.Request(
        f"{backend_url}/api/v1/admin/refresh-dictionary",
        method="POST",
        headers={"X-Admin-Key": admin_key},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())
    print(f"Dictionary refresh done: {result}")
    return result


async def main():
    parser = argparse.ArgumentParser(description="Import data into biaoqiao platform")
    parser.add_argument("--excel", help="Path to Excel file (资源标签对照表.xlsx)")
    parser.add_argument("--effects-json", help="Path to effects JSON file")
    parser.add_argument("--reindex", action="store_true", help="Trigger ES reindex after import")
    parser.add_argument("--pg-url", default="postgresql://biaoqiao:biaoqiao_dev@localhost:5432/biaoqiao")
    parser.add_argument("--admin-key", default=None, help="Admin API key (reads from .env if not provided)")
    parser.add_argument("--backend-url", default="http://localhost", help="Backend URL for API calls")
    args = parser.parse_args()

    if not args.excel and not args.effects_json and not args.reindex:
        parser.print_help()
        sys.exit(1)

    admin_key = args.admin_key
    if not admin_key:
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("ADMIN_API_KEY="):
                    admin_key = line.split("=", 1)[1].strip()
                    break
        if not admin_key:
            admin_key = "dev-admin-key-change-in-prod"

    pool = await asyncpg.create_pool(args.pg_url)
    try:
        if args.excel:
            await run_excel_import(args.excel, pool)
        if args.effects_json:
            await run_effects_import(args.effects_json, pool)
    finally:
        await pool.close()

    if args.reindex:
        await call_reindex(admin_key, args.backend_url)
        await call_refresh_dict(admin_key, args.backend_url)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **步骤 3：验证脚本语法正确**

```bash
python -c "import ast; ast.parse(open('scripts/import_data.py').read()); print('OK')"
```

预期：`OK`

- [ ] **步骤 4：Commit**

```bash
git add scripts/import_data.py
git commit -m "feat: add host-side import script for large file imports"
```

---

### 任务 5：管理脚本 (start.bat / stop.bat / import.bat)

**文件：**
- 新建：`start.bat`
- 新建：`stop.bat`
- 新建：`import.bat`

- [ ] **步骤 1：编写 start.bat**

```batch
@echo off
chcp 65001 >nul
echo ================================
echo  美术标签搜索平台 - 启动
echo ================================

REM Check Docker Desktop is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop 未运行，请先启动 Docker Desktop。
    pause
    exit /b 1
)

echo [1/3] 启动服务...
docker compose up -d --build
if errorlevel 1 (
    echo [ERROR] Docker Compose 启动失败。
    pause
    exit /b 1
)

echo [2/3] 等待服务就绪...
set RETRIES=0
:health_loop
if %RETRIES% GEQ 24 (
    echo [WARN] 服务未在 120 秒内就绪，请检查 docker compose logs。
    goto :show_ip
)
timeout /t 5 /nobreak >nul
curl -sf http://localhost/api/v1/health >nul 2>&1
if errorlevel 1 (
    set /a RETRIES+=1
    goto :health_loop
)
echo [OK] 服务已就绪。

:show_ip
echo [3/3] 检测内网 IP...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set "IP=%%a"
    goto :found_ip
)
:found_ip
set IP=%IP: =%
echo ================================
echo  访问地址: http://%IP%
echo ================================
pause
```

- [ ] **步骤 2：编写 stop.bat**

```batch
@echo off
chcp 65001 >nul
echo ================================
echo  美术标签搜索平台 - 停止
echo ================================
docker compose down
echo [OK] 服务已停止。
pause
```

- [ ] **步骤 3：编写 import.bat**

```batch
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

echo [5/5] 关闭 PG 端口...
del docker-compose.override.yml
docker compose up -d postgres
timeout /t 5 /nobreak >nul

echo ================================
echo  数据导入完成！
echo ================================
pause
```

- [ ] **步骤 4：Commit**

```bash
git add start.bat stop.bat import.bat
git commit -m "feat: add management scripts for start/stop/import"
```

---

### 任务 6：端到端验证

**文件：** 无新增文件，仅验证

- [ ] **步骤 1：构建前端**

```bash
cd frontend && npm run build
```

验证 `frontend/dist/` 目录存在且包含 `index.html`。

- [ ] **步骤 2：生成 .env（如尚未生成）**

```bash
python -c "import secrets; print(f'ADMIN_API_KEY={secrets.token_urlsafe(32)}')" > .env
```

- [ ] **步骤 3：启动服务**

```bash
docker compose up -d --build
```

- [ ] **步骤 4：验证端口安全**

从宿主机测试 PG 和 ES 端口不可达：

```bash
curl -f http://localhost:9200 2>&1 | grep "Connection refused"
```

```powershell
Test-NetConnection -ComputerName localhost -Port 5432
```

预期：两者都连接失败。

- [ ] **步骤 5：验证健康检查**

```bash
curl http://localhost/api/v1/health
```

预期：`{"status":"ok","pg":true,"es":true}`

- [ ] **步骤 6：验证 gzip**

```bash
curl -H "Accept-Encoding: gzip" -sI http://localhost/api/v1/search -o /dev/null -w "%{content_type}\n" | head -20
```

检查响应头包含 `Content-Encoding: gzip`。

- [ ] **步骤 7：浏览器验证**

在浏览器打开 `http://localhost`，确认：
- 页面正常加载
- 三个模块 tab 可切换
- 搜索功能正常
- 预览图正常显示

- [ ] **步骤 8：验证内网可访问**

获取本机内网 IP 后，从同一网络的其他设备访问 `http://<内网IP>`。
如果没有其他设备可测试，确认 Windows 防火墙允许 80 端口入站。

- [ ] **步骤 9：Commit 最终状态**

```bash
git add -A
git commit -m "chore: deployment configuration complete"
```
