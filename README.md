# 美术标签搜索平台

面向美术团队的游戏资产标签搜索平台，支持模型、特效、动作三大模块的结构化标签筛选与自然语言搜索。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Element Plus + Pinia + TypeScript |
| 后端 | FastAPI + asyncpg + elasticsearch-py |
| 数据库 | PostgreSQL 16 (JSONB) |
| 搜索引擎 | Elasticsearch 8.15 + IK 中文分词 |
| 部署 | Docker Compose (4 服务) |

## 快速部署

### 前置条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac)
- Git

### 步骤

```bash
# 1. 克隆项目
git clone <repo-url>
cd biaoqiao

# 2. 配置环境变量
copy .env.example .env
# 编辑 .env，修改 ADMIN_API_KEY 为随机字符串

# 3. 准备数据文件（放到项目根目录）
# - 资源标签对照表.xlsx
# - 特效/merged/effects_data.json (可选)
# - 特效/merged/gifs/ (可选，特效 GIF 预览)

# 4. 构建前端（首次部署或前端代码变更时）
cd frontend && npm install && npx vite build && cd ..

# 5. 启动服务
start.bat
# 或手动: docker compose up -d --build

# 6. 导入数据
import.bat

# 7. 提取缩略图（首次导入后执行一次）
python scripts/extract_thumbnails.py
```

### 访问

- 本机: http://localhost
- 内网: http://\<你的局域网IP\> (start.bat 会自动显示)

## 日常管理

| 操作 | 命令 |
|------|------|
| 启动 | `start.bat` |
| 停止 | `stop.bat` |
| 导入数据 | `import.bat` |
| 备份数据库 | `backup.bat` |

### 备份与恢复

**备份** — 运行 `backup.bat`，SQL 文件保存在 `backups/` 目录，自动保留最近 7 份。

**恢复** — 将备份文件导入：
```bash
docker compose exec -T postgres psql -U biaoqiao -d biaoqiao < backups/biaoqiao_YYYY-MM-DD_HHMM.sql
```

## 目录结构

```
biaoqiao/
├── backend/          # FastAPI 后端
├── frontend/         # Vue 3 前端
├── docker/           # Dockerfile (ES + IK)
├── sql/              # 数据库初始化 SQL
├── scripts/          # 数据导入/提取脚本
├── previews/         # 模型缩略图 (生成，不进 git)
├── nginx.conf        # Nginx 配置
├── docker-compose.yml
├── start.bat / stop.bat / import.bat / backup.bat
└── .env.example      # 环境变量模板
```

## 常见问题

**Q: Docker 镜像拉不下来？**
修改 `.env` 中的镜像源地址，或参考 `docs/docker-offline-images.md` 使用离线镜像。

**Q: 启动后页面空白？**
确认已执行 `cd frontend && npx vite build` 构建前端。

**Q: 搜索没结果？**
确认已运行 `import.bat` 导入数据。可通过 health 接口检查服务状态:
```bash
curl http://localhost/api/v1/health
```

**Q: 如何更新数据？**
重新运行 `import.bat`，会自动 upsert 更新。

**Q: 内网其他人访问不了？**
检查 Windows 防火墙是否放行了 80 端口入站规则。
