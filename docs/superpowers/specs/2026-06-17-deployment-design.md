# 美术标签搜索平台 — 内网部署设计

## 概述

将运行在 Docker Compose 上的美术标签搜索平台从本地开发环境转为公司内网可访问的服务。部署在当前 Windows 机器上，50+ 人通过内网 IP 的 HTTP 80 端口访问。

## 约束与决策

| 项目 | 决策 |
|------|------|
| 部署环境 | 当前 Windows 机器，Docker Desktop |
| 网络 | 公司内网，HTTP（不使用 HTTPS） |
| 用户规模 | 50+ 人 |
| 安全级别 | 最简化——关闭不必要端口、换掉硬编码密钥 |
| 运维方式 | 手动管理（start/stop bat 脚本） |
| 前端构建 | 开发者手动 `npm run build`，不在启动流程中 |

---

## 1. 安全收紧

### 1.1 关闭数据库端口暴露

当前 `docker-compose.yml` 暴露了 PG 5432 和 ES 9200 端口到宿主机，内网任何人可直接连接。部署时移除这两个端口映射，数据库仅在 Docker 内部网络可达。

**docker-compose.yml 改动：**
- 删除 postgres 服务的 `ports: ["5432:5432"]`
- 删除 elasticsearch 服务的 `ports: ["9200:9200"]`

### 1.2 数据导入时临时开放端口

需要导入数据时，通过 `docker-compose.override.yml` 临时暴露 PG 端口：

```yaml
# docker-compose.override.yml（临时文件，导入完删除）
services:
  postgres:
    ports: ["5432:5432"]
```

### 1.3 Admin API Key

创建 `.env` 文件，覆盖硬编码的 admin key：

```
ADMIN_API_KEY=<随机生成的32字符密钥>
```

docker-compose.yml 中 backend 的 environment 改为：
```yaml
- ADMIN_API_KEY=${ADMIN_API_KEY:-dev-admin-key-change-in-prod}
```

### 1.4 保留项

- PG 密码 `biaoqiao_dev` 保持不变（端口已不暴露，内网风险可接受）
- ES `xpack.security.enabled=false` 保持不变（仅内部网络可达）

---

## 2. Nginx 生产优化

### 2.1 Gzip 压缩

开启 gzip 压缩，减少传输大小，提升 50+ 并发用户的响应速度：

```nginx
gzip on;
gzip_min_length 1000;
gzip_comp_level 6;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript image/svg+xml;
gzip_vary on;
```

### 2.2 静态资源缓存

Vite 构建产物（JS/CSS）文件名包含 content hash，可以安全长缓存：

```nginx
location /assets/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

预览图和 GIF 缓存 1 天：

```nginx
location /previews/ {
    alias /data/previews/;
    expires 1d;
    add_header Cache-Control "public";
}

location /data/gifs/ {
    alias /data/gifs/;
    expires 1d;
    add_header Cache-Control "public";
}
```

### 2.3 连接优化

```nginx
keepalive_timeout 65;
proxy_buffering on;
```

### 2.4 保留项

- `client_max_body_size 2G` — 数据导入需要
- `proxy_read_timeout 600s` — 数据导入需要

---

## 3. 管理脚本

项目根目录放置 3 个 `.bat` 脚本，方便日常操作。

### 3.1 `start.bat` — 一键启动

流程：
1. 检查 Docker Desktop 是否运行（`docker info`），未运行则提示用户启动
2. 执行 `docker compose up -d --build`
3. 轮询 `/api/v1/health` 端点等待服务就绪（最多等 120 秒）
4. 检测本机内网 IP，打印访问地址：`http://<内网IP>`

### 3.2 `stop.bat` — 一键停止

执行 `docker compose down`。

### 3.3 `import.bat` — 数据导入

背景：1.1GB Excel 文件通过 API 上传会 504 超时，必须从主机直连 PG 导入。

流程：
1. 创建 `docker-compose.override.yml` 暴露 PG 5432 端口
2. `docker compose up -d postgres`（重启 PG 使端口生效）
3. 等待 PG 就绪
4. 运行主机侧导入脚本 `scripts/import_data.py`——直连 `localhost:5432` 执行 Excel 导入（models + actions）和 effects JSON 导入
5. 调用后端 API `POST /api/v1/admin/reindex-es` 触发 ES 全量重建索引
6. 调用后端 API `POST /api/v1/admin/refresh-dictionary` 刷新 NLP 词典缓存
7. 删除 `docker-compose.override.yml`
8. `docker compose up -d postgres`（关闭端口）

需要新建 `scripts/import_data.py`——封装 `excel_importer` 和 `effects_importer` 的主机侧调用逻辑。

### 3.4 健康检查端点

新增 `/api/v1/health` 路由：

- 检查 PG 连接（执行 `SELECT 1`）
- 检查 ES 连接（请求 `/_cluster/health`）
- 返回格式：`{"status": "ok", "pg": true, "es": true}`
- 任一检查失败返回 HTTP 503 和 `{"status": "error", "pg": false, "es": true}`

---

## 4. 前端构建与部署

### 4.1 构建方式

前端构建不纳入 `start.bat`，避免要求部署机器安装 Node.js。构建作为开发时操作：

```bash
cd frontend && npm run build
```

构建产物在 `frontend/dist/`。

### 4.2 Nginx 路由

| 路径 | 目标 |
|------|------|
| `/` | `frontend/dist/`（静态文件） |
| `/api/` | 反向代理到 `backend:8000` |
| `/previews/` | 预览图静态文件 |
| `/data/gifs/` | 特效 GIF 文件 |

### 4.3 访问方式

用户通过 `http://<机器内网IP>` 直接访问。`start.bat` 启动后自动检测内网 IP 并打印。

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `docker-compose.yml` | 修改 | 移除 PG/ES 端口，admin key 引用环境变量 |
| `nginx.conf` | 修改 | 添加 gzip、缓存头、keepalive |
| `.env` | 新建 | admin key |
| `.gitignore` | 修改 | 添加 `.env` |
| `backend/app/routers/health.py` | 新建 | 健康检查端点 |
| `backend/app/main.py` | 修改 | 注册 health router |
| `scripts/import_data.py` | 新建 | 主机侧数据导入脚本（直连 PG） |
| `start.bat` | 新建 | 一键启动脚本 |
| `stop.bat` | 新建 | 一键停止脚本 |
| `import.bat` | 新建 | 数据导入脚本 |
