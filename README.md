# 美术资产检索工作台

面向美术团队的游戏资产检索工作台，支持模型、特效、动作、图标四大模块的结构化标签筛选与自然语言搜索。

## 技术栈

| 层级     | 技术                                      |
| -------- | ----------------------------------------- |
| 前端     | Vue 3 + Element Plus + Pinia + TypeScript |
| 后端     | FastAPI + asyncpg + elasticsearch-py      |
| 数据库   | PostgreSQL 16 (JSONB)                     |
| 搜索引擎 | Elasticsearch 8.15 + IK 中文分词          |
| 部署     | Docker Compose (4 服务)                   |

## 模块说明

| 模块类型 | module_type | 数据源                     | 预览目录                       |
| -------- | ----------- | -------------------------- | ------------------------------ |
| 模型     | 1           | JSON + PNGs                | runtime_data/model/previews/   |
| 特效     | 2           | JSON + GIFs                | runtime_data/effect/gifs/      |
| 动作     | 3           | JSON + GIFs                | runtime_data/animator/previews/ |
| 图标     | 4           | JSON + PNGs                | runtime_data/ui/pngs/          |

## 快速部署

### 前置条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac)
- Git
- Node.js 18+（用于构建前端）

### 步骤

```bash
# 1. 克隆项目
git clone https://github.com/yinapan/biaoqian.git
cd biaoqian

# 2. 配置环境变量
copy .env.example .env
# 编辑 .env，修改 ADMIN_API_KEY 为随机字符串

# 3. 准备数据文件（tag_data_upload 与 biaoqian 项目目录同级）
# - ../tag_data_upload/model/merged/model_png_results.json + pngs/   （模型 JSON+PNG）
# - ../tag_data_upload/animation/actions_tags_format.json + gifs/     （动作 JSON+GIF）
# - ../tag_data_upload/effect/merged/effect_gif_results.json + gifs/      （特效 JSON+GIF）
# - ../tag_data_upload/ui/icon_png_results.json + pngs/ （图标 JSON+PNG）

# 4. 构建前端（首次部署或前端代码变更时）
build.bat
# 或按环境执行: deploy\local\build.bat / deploy\prod\build.bat

# 5. 启动服务
start.bat
# 或手动: docker compose up -d --build

# 代码修改后只重启前端/后端（不导入数据、不清库）
restart-app.bat

# 6. 导入数据（见下方"数据导入"）

# 7. 验证预览图可访问
verify-previews.bat
```

### 访问

- 本机: http://localhost
- 内网: http://<你的局域网IP> (start.bat 会自动显示)

## 数据导入

### 命令行脚本（推荐）

`scripts/import_data.py` 支持批量导入各模块数据，自动推断预览目录：

推荐优先使用环境脚本，它会自动切到项目根目录，并临时暴露 PostgreSQL/Elasticsearch 端口：

```bat
deploy\local\reimport-data.bat
deploy\prod\import-new-data.bat
```

如果手动执行 `python scripts/import_data.py`，必须先进入项目根目录。不能在 `deploy\local` 或 `deploy` 目录下直接执行，否则会找不到 `scripts\import_data.py`：

```bat
cd /d F:\biaoqian
```

本地测试环境还需要先打开 import compose，让宿主机能连到 `localhost:5432`：

```bat
docker compose -p biaoqian_local -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.import.yml up -d postgres elasticsearch
```

```bash
# 导入模型
python scripts/import_data.py --models-json ../tag_data_upload/model/merged/model_png_results.json --reindex

# 本地测试环境手动导入模型
python scripts/import_data.py --models-json ../tag_data_upload/model/merged/model_png_results.json --reindex --backend-url http://localhost:8081

# 导入动作
python scripts/import_data.py --animator-json ../tag_data_upload/animation/actions_tags_format.json --reindex

# 导入特效
python scripts/import_data.py --effects-json ../tag_data_upload/effect/merged/effect_gif_results.json --reindex

# 导入图标
python scripts/import_data.py --icons-json ../tag_data_upload/ui/icon_png_results.json --reindex

# 从 canonical 归档恢复（不读源 JSON，从 runtime_data 的 JSONL 还原）
python scripts/import_data.py --from-canonical --reindex

# 验证预览图可访问
verify-previews.bat
# 或按环境执行: deploy\local\verify-previews.bat / deploy\prod\verify-previews.bat

# Dry-run: list DB assets missing from the current JSON files, no deletion
python scripts/import_data.py --delete-stale --models-json ../tag_data_upload/model/merged/model_png_results.json --animator-json ../tag_data_upload/animation/actions_tags_format.json --effects-json ../tag_data_upload/effect/merged/effect_gif_results.json --icons-json ../tag_data_upload/ui/icon_png_results.json

# Apply stale deletion, then rebuild ES
python scripts/import_data.py --delete-stale --apply-delete-stale --models-json ../tag_data_upload/model/merged/model_png_results.json --animator-json ../tag_data_upload/animation/actions_tags_format.json --effects-json ../tag_data_upload/effect/merged/effect_gif_results.json --icons-json ../tag_data_upload/ui/icon_png_results.json --reindex

# Bat wrappers: dry-run first, then apply after checking output
delete-stale-data.bat
delete-stale-data.bat /apply
```

参数说明：
- `--pg-url` PostgreSQL 连接串（默认 `postgresql://biaoqiao:biaoqiao_dev@localhost:5432/biaoqiao`）
- `--admin-key` 管理密钥（不传则从 `.env` 读取）
- `--backend-url` 后端地址（默认 `http://localhost`）
- `--reindex` 导入后触发 ES 重建索引 + 字典刷新

### Admin API（在线导入）

服务启动后，可通过 HTTP 接口上传 JSON 触发导入：

| 接口                          | 说明           |
| ----------------------------- | -------------- |
| POST /api/v1/admin/import-models-json   | 导入模型 JSON  |
| POST /api/v1/admin/import-animator-json  | 导入动作 JSON  |
| POST /api/v1/admin/import-effects-json  | 导入特效 JSON  |
| POST /api/v1/admin/import-icons-json    | 导入图标 JSON  |
| POST /api/v1/admin/reindex-es            | 重建 ES 索引   |
| POST /api/v1/admin/refresh-dictionary    | 刷新字典缓存   |

所有接口需携带 `X-Admin-Key` 头。

## 日常管理

| 操作       | 命令           |
| ---------- | -------------- |
| 编译前端   | `build.bat`    |
| 启动       | `start.bat`    |
| 重启应用服务 | `restart-app.bat` |
| 停止       | `stop.bat`     |
| 导入数据   | `import.bat`   |
| 清库重导   | `reset-and-reimport-data.bat` |
| 备份数据库 | `backup.bat`   |

`restart-app.bat` 会重新构建前端、重建后端镜像，并重启 `backend/nginx`。它不会导入数据、不会清理 PostgreSQL/Elasticsearch，也不会删除 Docker volumes。适合修改前端或后端代码后刷新本地/正式部署。

也可以按环境显式执行：

```bat
deploy\local\restart-app.bat
deploy\prod\restart-app.bat
```

`reset-and-reimport-data.bat` 用于清空已导入的业务数据后重新完整导入。脚本会要求输入 `RESET CONFIRM` 二次确认；它只清理数据库中的 `assets`、`tag_values`、`import_errors`、`user_favorites`，保留表结构、标签定义、同义词、Docker volumes 和 `runtime_data` 预览文件。正式环境执行前建议先运行 `backup.bat`。

也可以按环境显式执行：

```bat
deploy\local\reset-and-reimport-data.bat
deploy\prod\reset-and-reimport-data.bat
```

### 环境脚本

`deploy\local\env.bat` 和 `deploy\prod\env.bat` 只决定当前机器上的 Compose 项目名、访问地址和 compose 文件组合：

| 脚本 | PROJECT_NAME | APP_URL | 用途 |
| ---- | ------------ | ------- | ---- |
| `deploy\local\env.bat` | `biaoqian_local` | `http://localhost:8081` | 本地测试环境 |
| `deploy\prod\env.bat` | `biaoqian` | `https://artsearch.testplus.cn` | 正式配置 |

注意：`deploy\prod` 不会自动连接线上服务器。它只会操作当前这台机器的 Docker。执行正式脚本前先运行：

```bat
hostname
ipconfig
docker compose -p biaoqian ps
```

如果是在本机执行，只影响本机 Docker；只有登录线上服务器后执行，才会影响线上正式环境。

### 备份与恢复

**备份** — 运行 `backup.bat`，SQL 文件保存在 `backups/` 目录，自动保留最近 7 份。

**恢复** — 将备份文件导入：

```bash
docker compose exec -T postgres psql -U biaoqian -d biaoqian < backups/biaoqian_YYYY-MM-DD_HHMM.sql
```

## 目录结构

```
biaoqian/
├── backend/                # FastAPI 后端
│   └── app/importers/      # 各模块导入器（model/animator/effects/icon）
├── frontend/               # Vue 3 前端
├── docker/                  # Dockerfile (ES + IK)
├── sql/                     # 数据库初始化 SQL
├── scripts/                 # 数据导入/提取脚本
│   └── import_data.py       # 统一导入入口
├── runtime_data/            # 运行时数据（生成，不进 git）
│   ├── model/previews/      # 模型 PNG 预览
│   ├── animator/previews/   # 动作 GIF 预览（前/左视角）
│   ├── effect/gifs/         # 特效 GIF 预览
│   ├── ui/pngs/             # 图标 PNG
│   └── canonical/           # 归档的 JSONL（用于灾难恢复）
├── model/                   # 模型源数据（不进 git）
├── animator/                # 动作源数据（不进 git）
├── 特效/                    # 特效源数据（不进 git）
├── icon_png_results/        # 图标源数据（不进 git）
├── nginx.conf               # Nginx 配置
├── docker-compose.yml
├── build.bat / start.bat / stop.bat / import.bat / backup.bat
└── .env.example             # 环境变量模板
```

## 常见问题

**Q: Docker 镜像拉不下来？**
修改 `.env` 中的镜像源地址，或参考 `docs/docker-offline-images.md` 使用离线镜像。

**Q: 启动后页面空白？**
确认已执行 `build.bat` 构建前端。

**Q: 搜索没结果？**
确认已运行 `import.bat` 导入数据。可通过 health 接口检查服务状态:

```bash
curl http://localhost/api/v1/health
```

**Q: 如何更新数据？**
重新运行 `import.bat` 或对应的 `python scripts/import_data.py --xxx-json ...` 命令，会自动 upsert 更新。

**Q: 筛选面板出现 `["乌鸦", "鸟"]` 这种带方括号的选项？**
这是 `tag_values` 表里残留了数组字符串。运行：

```bash
docker compose exec postgres psql -U biaoqiao -d biaoqiao -c "DELETE FROM tag_values WHERE value LIKE '[%'"
curl -X POST http://localhost/api/v1/admin/refresh-dictionary -H "X-Admin-Key: <你的key>"
```

然后重新 `--reindex`。

**Q: 模型/动作预览图不显示？**
检查 `runtime_data/model/previews/` 或 `runtime_data/animator/previews/` 是否有对应文件，且 `docker-compose.yml` 挂载了 `./runtime_data:/runtime_data`。

**Q: 内网其他人访问不了？**
检查 Windows 防火墙是否放行了 80 端口入站规则。
